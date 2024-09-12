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
        question_payload = {'question': question}
        configurable_payload = {'configurable': {
            'session_id': str(session_id), 'user_id': '3123455512'}}
        result = self.runnable.invoke(question_payload, configurable_payload)
        return result

    def test_normal_question(self):
        question = "I'm going to a neo-nazi rally, what should I wea"
        result = self.ask_question(question)
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
