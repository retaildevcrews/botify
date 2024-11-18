import json
import logging

import app.messages as messages
import yaml
from app.settings import AppSettings
from app.exceptions import InputTooLongError
from azure.identity import DefaultAzureCredential
from botify_langchain.custom_cosmos_db_chat_message_history import CustomCosmosDBChatMessageHistory
from botify_langchain.tools.topic_detection_tool import TopicDetectionTool
from common.schemas import ResponseSchema
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.chat_message_histories import CosmosDBChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import ConfigurableFieldSpec, Runnable
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import AzureChatOpenAI
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

    def get_runnable(
        self,
        include_history=True,
        return_intermediate_steps=False,
        verbose=False,
        azure_chat_open_ai_streaming=False,
    ) -> Runnable:
        # Gets the main runnable with the session history callable
        # included - this is the main entry point for the chatbot
        if include_history:
            history_callable = self._get_cosmos_db_chat_history
        else:
            history_callable = None
        return self.get_runnable_byo_session_history_callable(
            history_callable,
            return_intermediate_steps=return_intermediate_steps,
            verbose=verbose,
            azure_chat_open_ai_streaming=azure_chat_open_ai_streaming,
        )

    def get_runnable_byo_session_history_callable(
        self,
        get_session_history_callable,
        return_intermediate_steps=False,
        verbose=False,
        azure_chat_open_ai_streaming=True,
    ) -> Runnable:
        """
        Gets the main runnable with the session history callable as a
        parameter - this is to be used mainly for validations where we want
        to inject an alternative session history callable this also allows us to
        create an agent without history
        """

        CHAT_BOT_PROMPT = self.make_prompt(self.app_settings.prompt_template_paths)

        aoi_top_p = self.app_settings.model_config.top_p
        aoi_logit_bias = self.app_settings.model_config.logit_bias

        # Configure the language model
        use_structured_output = self.app_settings.model_config.use_structured_output
        response_format = (
            {"type": "json_object", "name": "response", "schema": ResponseSchema().get_response_schema()}
            if use_structured_output
            else (
                {"type": "json_object"}
                if self.app_settings.model_config.use_json_format
                else {"type": "text"}
            )
        )
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
        graph.add_node("pre_processor", self.pre_processor)
        graph.add_node("content_safety", self.content_safety)
        graph.add_node("stop_for_safety", self.return_safety_error_message)
        graph.add_node("identify_disclaimers", self.identify_disclaimers)
        graph.add_node("call_model", tools_agent_with_history)
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

    def _get_cosmos_db_chat_history(self, session_id: str, user_id: str) -> CosmosDBChatMessageHistory:
        """Get the session history from CosmosDB."""
        current_span = get_current_span()
        current_span.set_attribute("session_id", session_id)
        current_span.set_attribute("user_id", user_id)

        # Common parameters
        params = {
            'cosmos_endpoint': self.app_settings.environment_config.cosmos_endpoint,
            'cosmos_database': self.app_settings.environment_config.cosmos_database,
            'cosmos_container': self.app_settings.environment_config.cosmos_container,
            'session_id': session_id,
            'user_id': user_id,
        }

        # Extract the connection string if available
        cosmos_conn_str = self.app_settings.environment_config.cosmos_connection_string
        if (
            cosmos_conn_str is not None
            and cosmos_conn_str.get_secret_value() is not None
        ):
            params['connection_string'] = cosmos_conn_str.get_secret_value()
            self.logger.debug("Using connection string for CosmosDB")
        else:
            params['credential'] = DefaultAzureCredential()
            self.logger.debug("Using DefaultAzureCredential for CosmosDB")

        # Create the session history instance
        session_history = CustomCosmosDBChatMessageHistory(**params)

        # Create database and container if they don't exist
        session_history.prepare_cosmos()

        return session_history

    def _create_tools_agent_runnable(
        self,
        llm,
        tools,
        prompt,
        get_session_history_callable=None,
        return_intermediate_steps=False,
        verbose=False,
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
        if get_session_history_callable is None:
            return agent_executor
        else:
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
            if len(self.app_settings.banned_topics) > 0 and harmful_prompt_detected == False:
                tool_input = {"text_entry": state["question"], "topics": AppSettings().banned_topics}
                banned_topic_results = TopicDetectionTool().run(tool_input)
                banned_topic_detected = len(banned_topic_results) > 0
                current_span.set_attribute("banned_topic_detected", str(banned_topic_detected))
                if banned_topic_detected:
                    current_span.set_attribute("banned_topics_detected", str(banned_topic_results))
                self.logger.debug(
                    f"Topic Detection Tool - banned topic detected: {banned_topic_detected} results: {banned_topic_results}"
                )
        except Exception as e:
            logging.error(
                f"Error in content safety tool unable to determine result so exiting without responding: {e}"
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
        if len(state["question"]) > self.app_settings.invoke_question_character_limit:
            raise InputTooLongError(
                f"Question exceeds character limit: {len(state['question'])} > {self.app_settings.invoke_question_character_limit}")
        if state["question"].strip() == "":
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

    def identify_disclaimers(self, state: dict):
        self.logger.debug(f"Topic Detection Tool Executing")
        current_span = get_current_span()
        tool_input = {"text_entry": state["question"], "topics": AppSettings().disclaimer_topics}
        results = TopicDetectionTool().run(tool_input)
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
            llm_output = state["output"]

            output_format = self.app_settings.selected_format_config

            llm_output = self.extract_content(llm_output, f"```{output_format}")

            if output_format == "json":
                # Parse the cleaned JSON input
                data = json.loads(llm_output)

            if output_format == "yaml":
                # Parse the cleaned YAML input
                data = yaml.safe_load(llm_output)
            if llm_output.startswith('"') and llm_output.endswith('"'):
                llm_output = llm_output[1:-1]
            if llm_output == data:
                self.logger.warning(
                    f"LLM returned incorrect format so will wrap in json object llm response was: {llm_output}"
                )
                data = {"displayResponse": llm_output, "voiceSummary": llm_output}
        except Exception as e:
            self.logger.error(f"Error parsing {output_format} output from the LLM: {e}")
            self.logger.error(f"LLM Output: {llm_output}")

        # Convert the parsed data to JSON and return it
        state["output"] = json.dumps(data)
        return state

    def post_processor(self, state: dict):
        """Post-process the response based on the output format."""
        try:
            if self.app_settings.selected_format_config != "json_schema":
                state = self.process_llm_output(state)
            output = json.loads(state["output"])
            if self.app_settings.validate_json_output:
                self.logger.debug(f"Validating JSON Response Output: {output}")
                ResponseSchema().validate_json_response(output)
            output["disclaimers"] = state["disclaimers"]
        except Exception as e:
            self.logger.error(f"JSON Validation Error: {e}")
            output = messages.GENERIC_ERROR_MESSAGE_JSON
        state["output"] = output
        return state
