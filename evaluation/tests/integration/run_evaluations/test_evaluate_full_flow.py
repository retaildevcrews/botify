import unittest

import pandas as pd
from run_evaluations.evaluate_full_flow import call_full_flow


class TestEvaluateFullFlow(unittest.TestCase):

    def test(self):
        datafilepath = "/workspaces/botify/evaluation/data_files/chatbot_test.jsonl"
        data = pd.read_json(datafilepath, lines=True)
        # read first line of data
        record = data.iloc[0]
        user_id = record["user_id"]
        session_id = record["session_id"]
        chat_history = record["chat_history"]
        question = record["question"]
        results = call_full_flow(
            user_id=user_id, session_id=session_id, chat_history=chat_history, question=question
        )
        print("RESULTS====================")
        print(results)
        print("SEARCH RESULTS====================")
        print(results["search_results"])
        print("CONTEXT====================")
        print(results["context"])
        self.assertIsNotNone(results)


if __name__ == "__main__":
    unittest.main()
