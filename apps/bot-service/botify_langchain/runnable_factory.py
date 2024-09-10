import json
import logging

import app.messages as messages
from app.settings import AppSettings
from botify_langchain.custom_cosmos_db_chat_message_history import \
    CustomCosmosDBChatMessageHistory
from common.schemas import ResponseSchema
from langchain.agents import AgentExecutor, create_tool_calling_agent
from botify_langchain.tools.topic_detection_tool import TopicDetectionTool
from langchain_community.chat_message_histories import \
    CosmosDBChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import ConfigurableFieldSpec, Runnable
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, START, StateGraph
from opentelemetry.trace import get_current_span
from prompts.prompt_gen import PromptGen


class RunnableFactory:
    def __init__(self, byo_session_history_callable=False):
        self.app_settings = AppSettings(
            byo_session_history_callable=byo_session_history_callable)
        log_level = self.app_settings.environment_config.log_level
        logging.getLogger().setLevel(log_level)
        self.logger = logging.getLogger(__name__)
        self.promptgen = PromptGen()

        self.byo_session_history_callable = byo_session_history_callable

        from botify_langchain.tools.azure_ai_search_tool import AzureAISearch_Tool
        from botify_langchain.tools.azure_content_safety_tool import \
            AzureContentSafety_Tool

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

    def make_prompt(self, file_name):
        json_schema = ResponseSchema().get_response_schema_as_string()
        prompt_text = self.promptgen.generate_prompt(
            file_name, json_schema=json_schema)
        """Generate a prompt using the specified template file."""
        cpt = ChatPromptTemplate.from_messages(
            [
                ("system", prompt_text),
                MessagesPlaceholder(variable_name="history", optional=True),
                ("human", "{question}"),
                MessagesPlaceholder(
                    variable_name="agent_scratchpad", optional=True)
            ],
        )
        return cpt

    def get_runnable(self, return_intermediate_steps=False, verbose=False, azure_chat_open_ai_streaming=True) -> Runnable:
        # Gets the main runnable with the session history callable
        # included - this is the main entry point for the chatbot
        return self.get_runnable_byo_session_history_callable(
            self._get_cosmos_db_chat_history,
            return_intermediate_steps=return_intermediate_steps,
            verbose=verbose,
            azure_chat_open_ai_streaming=azure_chat_open_ai_streaming
        )

    def get_runnable_byo_session_history_callable(self, get_session_history_callable, return_intermediate_steps=False, verbose=False, azure_chat_open_ai_streaming=True) -> Runnable:
        # Gets the main runnable with the session history callable as a
        # parameter - this is to be used mainly for validations where we want
        # to inject an alternative session history callable
        CHAT_BOT_PROMPT = self.make_prompt(
            self.app_settings.prompt_template_path
        )

        aoi_top_p = self.app_settings.model_config.top_p
        aoi_logit_bias = self.app_settings.model_config.logit_bias

        # Configure the language model
        use_structured_output = self.app_settings.model_config.use_structured_output
        response_format = {"type": "json_object",
                           "name": "response",
                           "schema": ResponseSchema().get_response_schema()
                           } if use_structured_output else {"type": "json_object"} if self.app_settings.model_config.use_json_format else {"type": "text"}
        llm = AzureChatOpenAI(
            deployment_name=self.app_settings.environment_config.openai_deployment_name,
            temperature=self.app_settings.model_config.temperature,
            max_tokens=self.app_settings.model_config.max_tokens,
            top_p=aoi_top_p,
            logit_bias=aoi_logit_bias,
            streaming=azure_chat_open_ai_streaming,
            model_kwargs={"response_format": response_format},
        )

        # Doc Search Tool for searching the menu
        search_tool = self.azure_ai_search_tool

        # Instantiate the tools to be used by the agent
        tools = [search_tool]
        runnable = self._create_decision_making_graph_runnable(
            llm,
            tools,
            CHAT_BOT_PROMPT,
            get_session_history_callable,
            return_intermediate_steps=return_intermediate_steps,
            verbose=verbose,
        )
        return runnable

    def _create_decision_making_graph_runnable(
        self, llm, tools, prompt, get_session_history_callable, return_intermediate_steps=False, verbose=False
    ):
        """Create a decision-making graph runnable."""
        tools_agent_with_history = self._create_tools_agent_runnable(
            llm,
            tools,
            prompt,
            get_session_history_callable,
            return_intermediate_steps=return_intermediate_steps,
            verbose=verbose,
        )
        graph = StateGraph(dict)
        graph.add_node("content_safety", self.content_safety)
        graph.add_node("identify_disclaimers", self.identify_disclaimers)
        graph.add_node("validate_response", self.validate_response)
        graph.add_node("call_model", tools_agent_with_history)
        graph.add_node("safety_stop", self.return_safety_error_message)
        graph.add_edge(START, "content_safety")
        graph.add_conditional_edges(
            "content_safety",
            self.should_stop_for_safety,
            {
                "continue": "identify_disclaimers",
                "safety_stop": "safety_stop"
            }
        )
        graph.add_edge("identify_disclaimers", "call_model")
        graph.add_edge("call_model", "validate_response")
        graph.add_edge("safety_stop", END)
        graph.add_edge("validate_response", END)
        graph_runnable = graph.compile()
        return graph_runnable

    def _get_cosmos_db_chat_history(
        self, session_id: str, user_id: str
    ) -> CosmosDBChatMessageHistory:
        """Get the session history from CosmosDB."""
        current_span = get_current_span()
        current_span.set_attribute("session_id", session_id)
        current_span.set_attribute("user_id", user_id)

        if self.app_settings.environment_config.cosmos_connection_string:
            if self.app_settings.optimize_history:
                session_history_class = CustomCosmosDBChatMessageHistory
            else:
                session_history_class = CosmosDBChatMessageHistory

            session_history = session_history_class(
                cosmos_endpoint=self.app_settings.environment_config.cosmos_endpoint,
                cosmos_database=self.app_settings.environment_config.cosmos_database,
                cosmos_container=self.app_settings.environment_config.cosmos_container,
                connection_string=self.app_settings.environment_config.cosmos_connection_string.get_secret_value(),
                session_id=session_id,
                user_id=user_id,
            )

        # Create database and container if they don't exist
        session_history.prepare_cosmos()

        return session_history

    def _create_tools_agent_runnable(
        self, llm, tools, prompt, get_session_history_callable, return_intermediate_steps=False, verbose=False
    ):
        """Create a runnable agent with tools."""
        agent = create_tool_calling_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            stream_runnable=False,
            return_intermediate_steps=return_intermediate_steps,
            verbose=verbose,
        )
        runnable = RunnableWithMessageHistory(
            agent_executor,
            get_session_history_callable,
            input_messages_key="question",
            history_messages_key="history",
            history_factory_config=[
                ConfigurableFieldSpec(
                    id="user_id",
                    annotation=str,
                    name="User ID",
                    description="Unique identifier for the user.",
                    default="",
                    is_shared=True,
                ),
                ConfigurableFieldSpec(
                    id="session_id",
                    annotation=str,
                    name="Session ID",
                    description="Unique identifier for the conversation.",
                    default="",
                    is_shared=True,
                ),
            ],
        )
        return runnable

    def content_safety(self, state: dict):
        """Evaluate content safety."""
        self.logger.debug(f"Prompt Input: {state}")
        harmful_prompt_results = None
        prompt_shield_results = None
        attack_detected = False
        banned_topic_detected = False
        harmful_prompt_detected = False
        banned_topic_results = []
        unable_to_complete_safety_check = False
        try:
            current_span = get_current_span()
            if self.app_settings.content_safety_enabled:
                results = self.content_safety_tool.run(state["question"])
                self.logger.debug(
                    f"GetContentSafetyValidation_Tool results: {results}")
                harmful_prompt_results = results["analyzed_harmful_text_response"]
                prompt_shield_results = results["prompt_shield_validation_response"]
                captured_harmful_categories = [
                    category
                    for category in harmful_prompt_results["categoriesAnalysis"]
                    if category["severity"] > 0
                ]
                attack_detected = prompt_shield_results["userPromptAnalysis"]["attackDetected"]
                current_span.set_attribute(
                    "attackDetected", str(attack_detected))
                harmful_prompt_detected = len(captured_harmful_categories) > 0
                current_span.set_attribute(
                    "harmful_prompt_detected", str(harmful_prompt_detected))
                if harmful_prompt_detected:
                    current_span.set_attribute(
                        "harmful_categories_detected", str(
                            captured_harmful_categories)
                    )
            if len(self.app_settings.banned_topics) > 0 and harmful_prompt_detected == False:
                tool_input = {"text_entry": state["question"],
                              "topics": AppSettings().banned_topics}
                banned_topic_results = TopicDetectionTool().run(tool_input)
                banned_topic_detected = len(banned_topic_results) > 0
                current_span.set_attribute(
                    "banned_topic_detected", str(banned_topic_detected))
                if banned_topic_detected:
                    current_span.set_attribute(
                        "banned_topics_detected", str(banned_topic_results)
                    )
                self.logger.debug(
                    f"Topic Detection Tool - banned topic detected: {banned_topic_detected} results: {banned_topic_results}")
        except Exception as e:
            logging.error(
                f"Error in content safety tool unable to determine result so exiting without responding: {e}")
            unable_to_complete_safety_check = (
                self.app_settings.banned_topics > 0 or self.app_settings.content_safety_enabled)
            current_span.set_attribute(
                "unable_to_complete_safety_check", str(unable_to_complete_safety_check))

        state.update(
            {
                "attackDetected": attack_detected,
                "harmful_prompt_detected": harmful_prompt_detected,
                "harmful_categories": captured_harmful_categories,
                "banned_topic_detected": banned_topic_detected,
                "banned_topics": banned_topic_results,
                "unable_to_complete_safety_check": unable_to_complete_safety_check
            }
        )
        return state

    def should_stop_for_safety(self, state: dict):
        """Make a decision based on detected prompts."""
        if state["attackDetected"] or state["harmful_prompt_detected"] or state["banned_topic_detected"] or state["unable_to_complete_safety_check"]:
            self.logger.warning(
                f"Detected malicious step and stopping graph execution: {state}")
            return "stop_for_safety"
        else:
            return "continue"

    def return_safety_error_message(self, state: dict):
        """Return a safety error message."""
        state["output"] = messages.SAFETY_ERROR_MESSAGE_JSON
        return state

    def identify_disclaimers(self, state: dict):
        self.logger.debug(
            f"Topic Detection Tool Executing")
        current_span = get_current_span()
        tool_input = {"text_entry": state["question"],
                      "topics": AppSettings().disclaimer_topics}
        results = TopicDetectionTool().run(tool_input)
        self.logger.debug(
            f"Topic Detection Tool results: {results}")
        current_span.set_attribute(
            "disclaimers_added", str(results))
        state["disclaimers"] = results
        return state

    def validate_response(self, state: dict):
        try:
            self.logger.debug(f"Validating JSON: {state['output']}")
            ResponseSchema().validate_response(state["output"])
            output = json.loads(state["output"])  # Ensure the response
            output["disclaimers"] = state["disclaimers"]
            self.logger.debug(f"Output: {output}")
        except Exception as e:
            self.logger.error(f"JSON Validation Error: {e}")
            # Return the original response
            state["output"] = messages.GENERIC_ERROR_MESSAGE_JSON
        return state
