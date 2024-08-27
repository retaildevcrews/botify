import unittest

from prompts.prompt_gen import PromptGen

schema = """{"title":"Example Schema","type":"object","properties":{"firstName":{"type":"string"},"lastName":{"type":"string"},"age":{"description":"Age in years","type":"integer","minimum":0}},"required":["firstName","lastName"]}"""


class TestStringMethods(unittest.TestCase):

    def test_escape_curly_braces(self):
        input_string = schema
        escaped_string = PromptGen.escape_curly_braces(
            self, input_string=input_string)
        expected_string = """{{"title":"Example Schema","type":"object","properties":{{"firstName":{{"type":"string"}},"lastName":{{"type":"string"}},"age":{{"description":"Age in years","type":"integer","minimum":0}}}},"required":["firstName","lastName"]}}"""
        self.assertEqual(escaped_string, expected_string)

    def test_escape_curly_braces_jinja(self):
        input_string = schema
        escaped_string = PromptGen.escape_curly_braces(self,
                                                       input_string=input_string, open_brace="{{'{{'}}", close_brace="{{'}}'}}")
        expected_string = """{{'{{'}}"title":"Example Schema","type":"object","properties":{{'{{'}}"firstName":{{'{{'}}"type":"string"{{'}}'}},"lastName":{{'{{'}}"type":"string"{{'}}'}},"age":{{'{{'}}"description":"Age in years","type":"integer","minimum":0{{'}}'}}{{'}}'}},"required":["firstName","lastName"]{{'}}'}}"""
        self.assertEqual(escaped_string, expected_string)

    def test_generate_jinja_prompt(self):
        prompt_gen = PromptGen()
        jinja_template_name = "000_consolidated_json_with_options.jinja"
        prompt = prompt_gen.generate_prompt(
            jinja_template_name, json_schema=schema)
        self.assertIsNotNone(prompt)

    def test_generate_text_prompt(self):
        prompt_gen = PromptGen()
        template_name = "minified_json.txt"
        prompt = prompt_gen.generate_prompt(
            template_name=template_name, json_schema=schema)
        self.assertIsNotNone(prompt)


if __name__ == "__main__":
    unittest.main()
