from typing import Optional, Tuple

from app.settings import AppSettings
from langchain.tools import BaseTool
from langchain_core.callbacks import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI


class TopicDetectionTool(BaseTool):
    """Tool for detecting banned topics in a query using Azure OpenAI."""

    name = "Topic Detection Tool"
    description = "Detects topics in the query using Azure OpenAI."

    def make_prompt(self, text_entry: str, topics: list[str]) -> list[dict]:
        return [
            SystemMessage(
                content=f"""
                          Identify if it contains any of these topics topics: {', '.join(topics)}.
                          If the prompt contains any of the following topics, please respond with the list of all topics that are present in the prompt.
                          If the prompt does not contain any of the banned topics, please respond with 'None'
                          Example Responses: 'medical, legal', 'None'
                          """
            ),
            HumanMessage(content=f"Does this prompt pertain to the listed topics? {text_entry}"),
        ]

    def get_llm(self):
        app_settings = AppSettings()
        llm = AzureChatOpenAI(
            deployment_name=app_settings.environment_config.openai_classifier_deployment_name,
            max_tokens=app_settings.topic_model_max_completion_tokens,
        )
        return llm

    def format_response(self, response: AIMessage) -> list[str]:
        result = response.content
        if result == "None":
            return []
        else:
            return result.split(", ")

    def _run(
        self, text_entry, topics, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> Tuple[str, bool, float]:
        # Call Azure OpenAI to classify the prompt
        response = self.get_llm().ainvoke(self.make_prompt(text_entry, topics))
        return self.format_response(response)

    async def _arun(
        self, text_entry, topics, run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> Tuple[str, bool, float]:
        # Call Azure OpenAI to classify the prompt asynchronously
        response = await self.get_llm().ainvoke(self.make_prompt(text_entry, topics))

        return self.format_response(response)
