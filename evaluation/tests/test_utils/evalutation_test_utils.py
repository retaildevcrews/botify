import unittest

def validate_evaluator(self:unittest.TestCase, evaluators, evaluator_name, evaluator_type):

    evaluator = evaluators[evaluator_name]

    self.assertTrue(type(evaluator) is evaluator_type)



def validate_evaluator_config(self:unittest.TestCase, evaluator_config, evaluator_name, key_name, expected_content):
   self.assertEqual(evaluator_config[evaluator_name][key_name], expected_content)
