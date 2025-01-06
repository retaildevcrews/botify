import json
from time import perf_counter
from typing import List

from app.settings import AppSettings
from botify_langchain.runnable_factory import RunnableFactory
from evaluation_utils.formatting_utils import string_to_dict
from evaluation_utils.response_parser import parse_response
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
        # reranker_scores.append(page_content["@search.rerankerScore"])
        contexts.append(page_content)
    response = {"scores": scores, "reranker_scores": reranker_scores, "contexts": contexts}
    return response


def parse_full_flow_response(response):
    try:
        parsed_response = parse_response(response)
        return {
            "answer": parsed_response["answer"],
            "question": parsed_response["question"],
            "search_documents": json.dumps(parsed_response["search_documents"]),
            "called_tools": parsed_response["called_tools"],
        }
    except Exception as e:
        print(f"Failed to parse response Error: {e}")
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

    def call_content_safety_tool(self, question: str) -> dict:
        result = self.factory.content_safety_tool.invoke(question)
        return result

    def call_full_flow(
        self, question: str, session_id: str, user_id: str, global_id: str, chat_history: str = []
    ):
        # Inject artificial chat history for multi turn testing
        messages_from_data = get_history_messages_from_data(chat_history)
        messages_history_callable = MessageHistoryFromData(session_id, user_id, messages_from_data)
        # Create question payload
        question_payload = {"messages": [{"role": "user", "content": question}]}
        configurable_payload = {"configurable": {"session_id": session_id, "user_id": user_id}}
        # call runnable - note that we get the version where we can inject the chat history
        runnable = self.factory.get_runnable(azure_chat_open_ai_streaming=False, stream_usage=False)
        output = {}
        with get_openai_callback() as cb:
            start_time = perf_counter()
            result = runnable.invoke(question_payload, configurable_payload)
            end_time = perf_counter()
            ellapsed_time = end_time - start_time
        try:
            output = parse_full_flow_response(result)
        except TypeError as e:
            output["answer"] = (
                f"Failed to parse response - unparsed result: {
                result}"
            )
        output["start_time"] = start_time
        output["end_time"] = end_time
        output["ellapsed_time"] = ellapsed_time
        output["completion_tokens"] = cb.completion_tokens
        output["prompt_tokens"] = cb.prompt_tokens
        output["total_tokens"] = cb.total_tokens
        output["app_config"] = (self.factory.app_settings.get_config(),)
        output["app_config_hash"] = (self.factory.app_settings.get_config_hash(),)
        return output
