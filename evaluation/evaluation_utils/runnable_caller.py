import json
from time import perf_counter
from typing import List

from app.settings import AppSettings
from botify_langchain.runnable_factory import RunnableFactory
from evaluation_utils.formatting_utils import string_to_dict
from langchain_community.callbacks import get_openai_callback
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


def format_search_result(documents):
    scores = []
    reranker_scores = []
    contexts = []
    for document in documents:
        page_content = document.page_content
        page_content = string_to_dict(page_content)
        scores.append(page_content["@search.score"])
        reranker_scores.append(page_content["@search.rerankerScore"])
        contexts.append(page_content)
    response = {"scores": scores,
                "reranker_scores": reranker_scores, "contexts": contexts}
    return response


def parse_full_flow_response(response, factory: RunnableFactory):
    try:
        question = ""
        output = ""
        voice_summary = ""
        display_response = ""
        recommended_products = []
        product_list = []
        toolagentaction_list = []
        history = []
        if "question" in response:
            question = response["question"]
        if "history" in response:
            messages = response["history"]
            for message in messages:
                history.append(f"{message.type}:{message.content}")
        if "output" in response:
            output = response["output"]
            parsed_response = response["output"]
        if "voiceSummary" in parsed_response:
            voice_summary = parsed_response["voiceSummary"]
        if "displayResponse" in parsed_response:
            display_response = parsed_response["displayResponse"]
        if "intermediate_steps" in response:
            intermediate_steps = response["intermediate_steps"]
            for step in intermediate_steps:
                toolagentaction = step[0].tool
                tool_query = step[0].tool_input
                documents = step[1]
                toolagentaction_list.append(
                    {
                        "tool": toolagentaction,
                        "query": tool_query,
                        "documents": documents,
                    }
                )

        consolidated_tool_actions = []
        consolidated_tool_actions = [{"tool": toolaction["tool"],
                                      "query": toolaction["query"],
                                      "documents": toolaction["documents"]} for toolaction in toolagentaction_list]

        return {
            "bot_response": output,
            "question": question,
            "voice_summary": voice_summary,
            "display_response": display_response,
            "toolagentactions": toolagentaction_list,
            "consolidated_tool_actions": consolidated_tool_actions,
            "app_config": factory.app_settings.get_config(),
            "app_config_hash": factory.app_settings.get_config_hash(),
            "history": history,
        }
    except Exception as e:
        return {"error": "Failed to parse response:" + response}


def get_history_messages_from_data(history: str):
    messages = []
    for message_pair in history:
        messages.append(HumanMessage(message_pair["human"]))
        messages.append(AIMessage(message_pair["ai"]))
    return messages


class MessageHistoryFromData:
    def __init__(self, session_id: str, user_id: str, messages_from_data: List[BaseMessage]):
        self.session_id = session_id
        self.user_id = user_id
        self.message_history = ChatMessageHistory()
        self.message_history.add_messages(messages_from_data)

    def get_session_history(self, user_id, session_id) -> List[BaseMessage]:
        return self.message_history

    def __call__(self, user_id, session_id) -> "MessageHistoryFromData":
        return self.get_session_history(user_id, session_id)


class RunnableCaller:
    def __init__(self, app_settings: AppSettings = None):
        self.appsettings = app_settings if app_settings else AppSettings()
        self.factory = RunnableFactory(app_settings)

    def call_search_tool(self, question: str) -> dict:
        documents = self.factory.azure_ai_search_tool.invoke(question)
        return format_search_result(documents)

    def call_full_flow(self, question: str, session_id: str, user_id: str, chat_history: str):
        # Inject artificial chat history for multi turn testing
        messages_from_data = get_history_messages_from_data(chat_history)
        messages_history_callable = MessageHistoryFromData(
            session_id, user_id, messages_from_data)
        # Create question payload
        question_payload = {"question": question}
        configurable_payload = {
            "configurable": {"session_id": session_id, "user_id": user_id}
        }
        # call runnable - note that we get the version where we can inject the chat history
        runnable = self.factory.get_runnable_byo_session_history_callable(messages_history_callable,
                                                                          return_intermediate_steps=True, azure_chat_open_ai_streaming=False)
        output = {"question": question}
        with get_openai_callback() as cb:
            start_time = perf_counter()
            result = runnable.invoke(
                question_payload, configurable_payload)
            end_time = perf_counter()
            ellapsed_time = end_time - start_time
        try:
            output = parse_full_flow_response(result, self.factory)
        except TypeError as e:
            output["answer"] = f"Failed to parse response - unparsed result: {
                result}"
        output["start_time"] = start_time
        output["end_time"] = end_time
        output["ellapsed_time"] = ellapsed_time
        output["completion_tokens"] = cb.completion_tokens
        output["prompt_tokens"] = cb.prompt_tokens
        output["total_tokens"] = cb.total_tokens
        return output
