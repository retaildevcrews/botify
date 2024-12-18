import unittest
import uuid

from botify_langchain.runnable_factory import RunnableFactory

session_id = uuid.uuid4()


class TestStringMethods(unittest.TestCase):

    # Create Agent instance
    factory = RunnableFactory()
    runnable = factory.create_qna_agent()

    def ask_question(self, question):
        question = question
        question_payload = inputs = {"messages": [("user", question)]}
        configurable_payload = {"configurable": {"session_id": str(session_id), "user_id": "3123455512"}}
        result = self.runnable.invoke(question_payload, configurable_payload)
        return result

    def test_normal_question(self):
        app_settings = self.factory.app_settings
        question = "How do I get a stain out of my shirt?"
        result = self.ask_question(question)
        print(result)
        self.assertIsNotNone(result)




if __name__ == "__main__":
    unittest.main()
