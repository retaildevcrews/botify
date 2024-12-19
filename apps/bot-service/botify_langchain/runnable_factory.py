import json
import logging

import app.messages as messages
import yaml
from app.exceptions import InputTooLongError, MaxTurnsExceededError
from app.settings import AppSettings
from azure.identity import DefaultAzureCredential
from botify_langchain.create_react_agent import create_react_agent
from botify_langchain.custom_cosmos_db_chat_message_history import CustomCosmosDBChatMessageHistory
from botify_langchain.tools.topic_detection_tool import TopicDetectionTool
from common.schemas import ResponseSchema
from common.schemas.json.schema import Response
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.chat_message_histories import CosmosDBChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import ConfigurableFieldSpec, Runnable
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import AzureChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from opentelemetry.trace import get_current_span
from prompts.prompt_gen import PromptGen


class RunnableFactory:
    def __init__(self, byo_session_history_callable=False):
        self.app_settings = AppSettings(byo_session_history_callable=byo_session_history_callable)
        log_level = self.app_settings.environment_config.log_level
        logging.getLogger().setLevel(log_level)
        self.logger = logging.getLogger(__name__)
        self.promptgen = PromptGen()

        self.byo_session_history_callable = byo_session_history_callable

        self.current_turn_count = 0

        from botify_langchain.tools.azure_ai_search_tool import AzureAISearch_Tool
        from botify_langchain.tools.azure_content_safety_tool import AzureContentSafety_Tool

        # Document indexes for the custom retriever
        indexes = [
            self.app_settings.environment_config.doc_index
        ]  # Custom retriever is able to search multiple indexes

        # Doc Search Tool for searching the menu
        self.azure_ai_search_tool = AzureAISearch_Tool(
            indexes=indexes,
            fields_to_select="id, title, chunk, location",
            vector_query_fields="chunkVector",
            k=self.app_settings.search_tool_topk,
            semantic_config="my-semantic-config",
            name="Search-Tool",
            description="Use this tool to search the knowldge base",
            add_answer_scores=True,
        )

        self.content_safety_tool = AzureContentSafety_Tool()

    def create_qna_agent(self, azure_chat_open_ai_streaming=False):
        # Configure the language model
        use_structured_output = self.app_settings.model_config.use_structured_output
        use_json_format = self.app_settings.model_config.use_json_format
        llm = AzureChatOpenAI(
            deployment_name=self.app_settings.environment_config.openai_deployment_name,
            temperature=self.app_settings.model_config.temperature,
            max_tokens=self.app_settings.model_config.max_tokens,
            top_p=self.app_settings.model_config.top_p,
            logit_bias=self.app_settings.model_config.logit_bias,
            streaming=azure_chat_open_ai_streaming,
            timeout=self.app_settings.model_config.timeout,
            max_retries=self.app_settings.model_config.max_retries,
        )
        if use_json_format:
            llm.model_kwargs = {"response_format": {"type": "json_object"}}
        if use_structured_output:
            llm.model_kwargs = {
                "response_format": {"type": "json_schema", "json_schema": {"name":"response", "schema": json.loads(ResponseSchema().get_response_schema())}}
            }
        tools = [self.azure_ai_search_tool]
        prompt_text = self.promptgen.generate_prompt(
            self.app_settings.prompt_template_paths, schema=ResponseSchema().get_response_schema()
        )

        # Instantiate the tools to be used by the agent
        agent_graph = create_react_agent(llm, tools, state_modifier=prompt_text)
        return agent_graph

    def make_prompt(self, file_names):
        schema = ResponseSchema().get_response_schema()
        prompt_text = self.promptgen.generate_prompt(file_names, schema=schema)
        """Generate a prompt using the specified template file."""
        cpt = ChatPromptTemplate.from_messages(
            [
                ("system", prompt_text),
                MessagesPlaceholder(variable_name="history", optional=True),
                ("human", "{question}"),
                MessagesPlaceholder(variable_name="agent_scratchpad", optional=True),
            ],
        )
        return cpt

    def get_runnable(self):
        graph = StateGraph(dict)
        graph.add_node("pre_processor", self.pre_processor)
        graph.add_node("content_safety", self.content_safety)
        graph.add_node("stop_for_safety", self.return_safety_error_message)
        graph.add_node("identify_disclaimers", self.identify_disclaimers)
        graph.add_node("call_model", self.create_qna_agent())
        graph.add_node("post_processor", self.post_processor)
        graph.add_edge(START, "pre_processor")
        graph.add_edge("pre_processor", "content_safety")
        graph.add_conditional_edges(
            "content_safety",
            self.should_stop_for_safety,
            {"continue": "identify_disclaimers", "stop_for_safety": "stop_for_safety"},
        )
        graph.add_edge("identify_disclaimers", "call_model")
        graph.add_edge("call_model", "post_processor")
        graph.add_edge("stop_for_safety", END)
        graph.add_edge("post_processor", END)
        graph_runnable = graph.compile()
        return graph_runnable

    async def content_safety(self, state: dict):
        """Evaluate content safety."""
        self.logger.debug(f"Prompt Input: {state}")
        harmful_prompt_results = None
        prompt_shield_results = None
        attack_detected = False
        banned_topic_detected = False
        harmful_prompt_detected = False
        banned_topic_results = []
        unable_to_complete_safety_check = False
        current_span = get_current_span()
        try:
            if self.app_settings.content_safety_enabled:
                question = state["messages"][-1][1]
                results = await self.content_safety_tool._arun(question)
                self.logger.debug(f"GetContentSafetyValidation_Tool results: {results}")
                harmful_prompt_results = results["analyzed_harmful_text_response"]
                prompt_shield_results = results["prompt_shield_validation_response"]
                captured_harmful_categories = [
                    category
                    for category in harmful_prompt_results["categoriesAnalysis"]
                    if category["severity"] > self.app_settings.content_safety_threshold
                ]
                attack_detected = prompt_shield_results["userPromptAnalysis"]["attackDetected"]
                current_span.set_attribute("attackDetected", str(attack_detected))
                harmful_prompt_detected = len(captured_harmful_categories) > 0
                current_span.set_attribute("harmful_prompt_detected", str(harmful_prompt_detected))
                if harmful_prompt_detected:
                    current_span.set_attribute(
                        "harmful_categories_detected", str(captured_harmful_categories)
                    )
        except Exception as e:
            logging.error(
                f"Error in content safety tool unable to determine result so exiting without responding: {e}"
            )
            unable_to_complete_safety_check = True
            current_span.set_attribute(
                "unable_to_complete_safety_check", str(unable_to_complete_safety_check)
            )
        try:
            self.logger.debug(f"Starting Topic Detection: {state}")
            if len(self.app_settings.banned_topics) > 0 and harmful_prompt_detected is False:
                banned_topic_results = await TopicDetectionTool()._arun(question, AppSettings().banned_topics)
                banned_topic_detected = len(banned_topic_results) > 0
                current_span.set_attribute("banned_topic_detected", str(banned_topic_detected))
                if banned_topic_detected:
                    current_span.set_attribute("banned_topics_detected", str(banned_topic_results))
                self.logger.debug(
                    f"""Topic Detection Tool -
                    banned topic detected: {banned_topic_detected}
                    results: {banned_topic_results}"""
                )
        except Exception as e:
            logging.error(
                f"Error in topic detection tool unable to determine result so exiting without responding: {e}"
            )
            unable_to_complete_safety_check = True
            current_span.set_attribute(
                "unable_to_complete_safety_check", str(unable_to_complete_safety_check)
            )

        state.update(
            {
                "attackDetected": attack_detected,
                "harmful_prompt_detected": harmful_prompt_detected,
                "harmful_categories": captured_harmful_categories,
                "banned_topic_detected": banned_topic_detected,
                "banned_topics": banned_topic_results,
                "unable_to_complete_safety_check": unable_to_complete_safety_check,
            }
        )
        return state

    def pre_processor(self, state: dict):
        """Invoke prechecks before running the graph."""
        current_turn_count = self.current_turn_count
        max_turn_count = self.app_settings.max_turn_count
        self.logger.info("Current Turn Count: " + str(current_turn_count))
        self.logger.info("Max Turn Count: " + str(max_turn_count))
        if current_turn_count >= max_turn_count:
            raise MaxTurnsExceededError(f"Max turn count exceeded: {current_turn_count} >= {max_turn_count}")
        question = state["messages"][-1][1]
        if len(question) > self.app_settings.invoke_question_character_limit:
            raise InputTooLongError(
                f"""Question exceeds character limit:
                {len(question)} > {self.app_settings.invoke_question_character_limit}"""
            )
        if question.strip() == "":
            raise ValueError("Question is empty")

    def should_stop_for_safety(self, state: dict):
        """Make a decision based on detected prompts."""
        if (
            state["attackDetected"]
            or state["harmful_prompt_detected"]
            or state["banned_topic_detected"]
            or state["unable_to_complete_safety_check"]
        ):
            self.logger.warning(f"Detected malicious step and stopping graph execution: {state}")
            return "stop_for_safety"
        else:
            return "continue"

    def return_safety_error_message(self, state: dict):
        """Return a safety error message."""
        state["output"] = messages.SAFETY_ERROR_MESSAGE_JSON
        return state

    async def identify_disclaimers(self, state: dict):
        self.logger.debug("Topic Detection Tool Executing")
        current_span = get_current_span()
        question = state["messages"][-1][1]
        results = await TopicDetectionTool()._arun(question, AppSettings().disclaimer_topics)
        self.logger.debug(f"Topic Detection Tool results: {results}")
        current_span.set_attribute("disclaimers_added", str(results))
        state["disclaimers"] = results
        return state

    def extract_content(self, input_str: str, start_delimiter: str, end_delimiter: str = "```") -> str:
        """
        Helper function to extract content between two delimiters.

        :param input_str: The input string to process.
        :param start_delimiter: The starting delimiter to look for.
        :param end_delimiter: The ending delimiter to look for.
        :return: The content between the start and end delimiters.
        """
        if start_delimiter in input_str and end_delimiter in input_str:
            # Remove everything before and including the first occurrence of start_delimiter
            input_str = input_str.split(start_delimiter, 1)[1]
            # Remove everything after and including the last occurrence of end_delimiter
            input_str = input_str.rsplit(end_delimiter, 1)[0]
        return input_str.strip()

    def process_llm_output(self, state: dict):
        try:
            llm_output = state["messages"][-1].content
            output_format = self.app_settings.selected_format_config
            llm_output = self.extract_content(llm_output, f"```{output_format}")
            logging.debug(f"Ouput format: {output_format}")
            logging.debug(f"LLM Output: {llm_output}")
            if output_format == "json" or output_format == "yaml":
                if llm_output.startswith('"') and llm_output.endswith('"'):
                    llm_output = llm_output[1:-1]
                if output_format == "json":
                    # Parse the cleaned JSON input
                    data = json.loads(llm_output)
                    if llm_output == data:
                        self.logger.warning(
                            f"""LLM returned incorrect format.
                                Will wrap in json object.
                                llm response was: {llm_output}"""
                        )
                        data = {"displayResponse": llm_output, "voiceSummary": llm_output}
                    state["output"] = json.dumps(data)
            else:
                state["output"] = llm_output
        except Exception as e:
            self.logger.error(f"Error parsing {output_format} output from the LLM: {e}")
            self.logger.error(f"LLM Output: {llm_output}")
        return state

    def post_processor(self, state: dict):
        """Post-process the response based on the output format."""
        try:
            output_format = self.app_settings.selected_format_config
            state = self.process_llm_output(state)
            output = state["output"]
            if self.app_settings.validate_json_output:
                self.logger.debug(f"Validating JSON Response Output: {output}")
                ResponseSchema().validate_json_response(output)
            if "disclaimers" in state:
                if output_format == "json" or output_format == "json_schema":
                    output["disclaimers"] = state["disclaimers"]
                else:
                    output = output + "\n\ndisclaimers:" + state["disclaimers"]
        except Exception as e:
            self.logger.error(f"JSON Validation Error: {e}")
            output = messages.GENERIC_ERROR_MESSAGE_JSON
        state["output"] = output
        return state
