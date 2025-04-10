import unittest
import uuid

from evaluation_utils.runnable_caller import RunnableCaller


class TestRunnableCallers(unittest.TestCase):

    runnable_caller = RunnableCaller()
    session_id = uuid.uuid4()

    def test_call_doc_search_tool(self):
        result = self.runnable_caller.call_search_tool(question="How do I get a stain out of my shirt?")
        print(result)
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
