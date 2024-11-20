import unittest
import uuid

from botify_langchain.runnable_factory import RunnableFactory

session_id = uuid.uuid4()


class TestStringMethods(unittest.TestCase):

    # Create Agent instance
    factory = RunnableFactory()
    runnable = factory.get_runnable()

    def ask_question(self, question):
        question = question
        question_payload = {"question": question}
        configurable_payload = {"configurable": {"session_id": str(session_id), "user_id": "3123455512"}}
        result = self.runnable.invoke(question_payload, configurable_payload)
        return result

    def test_normal_question(self):
        app_settings = self.factory.app_settings
        anonymizer = Anonymizer(app_settings=app_settings, mode=app_settings.environment_config.anonymizer_mode,
                                crypto_key=app_settings.environment_config.anonymizer_crypto_key)
        question = "How do I get a stain out of my shirt?"
        anonymized_text = anonymizer.anonymize_text(question).to_json()
        result = self.ask_question(anonymized_text)
        print(result)
        self.assertIsNotNone(result)

    # def test_search_question(self):
    #     question = "How do I clean a hairbrush?"
    #     result = self.factory.azure_ai_search_tool.invoke(question)
    #     print(result)
    #     self.assertIsNotNone(result)

    # def test_search_question(self):
    #     question = "How do I clean a hairbrush?"
    #     result = self.factory.get_runnable.invoke(question)
    #     print(result)
    #     self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
