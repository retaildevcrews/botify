import logging
from os.path import dirname
from os.path import join as path_join

from jinja2 import FileSystemLoader
from jinja2.sandbox import SandboxedEnvironment

DEFAULT_TEMPLATE_DIRECTORY = f"{path_join(dirname(__file__), 'templates')}"

log = logging.getLogger(__name__)


class PromptGenEnvironment(SandboxedEnvironment):

    def is_safe_attribute(self, obj, attr, value):
        if attr in ["os", "subprocess", "eval", "exec"]:
            return False
        return super().is_safe_attribute(obj, attr)


def escape_curly_braces(input_string, open_brace="{{", close_brace="}}"):
    """
    Replaces all single curly braces in the input string with double curly braces.
    This is used to escape curly braces in the input string for templating systems like Jinja.

    :param input_string: The string in which to replace curly braces.
    :param open_brace: The string to replace single open curly braces.
    :param close_brace: The string to replace single close curly braces.
    :return: A new string with all curly braces replaced by the provided strings.
    """
    try:
        open_brace_placeholder = "_open_brace_"
        close_brace_placeholder = "_close_brace_"
        # Replace the intended curly braces with the placeholders
        input_string = input_string.replace(open_brace, open_brace_placeholder).replace(
            close_brace, close_brace_placeholder
        )
        # Replace the placeholders with the provided strings
        escaped_string = input_string.replace(open_brace_placeholder, open_brace).replace(
            close_brace_placeholder, close_brace
        )
    except Exception as e:
        log.error(f"An error occurred: {e}")
        return input_string
    return escaped_string


class PromptGen:
    def __init__(self, root_template_dir=DEFAULT_TEMPLATE_DIRECTORY):
        """Constructor

        Args:
            prompt_template_paths (dict, optional): _Path to prompt files._ Defaults to ".".
            kw_bot_attributes    (merged dict, optional): _Bot input arguments dict._
        """
        self.root_template_dir = root_template_dir
        self._env = PromptGenEnvironment(
            loader=FileSystemLoader(self.root_template_dir + "/jinja"),
            # Always autoescape to do bare minimum template santization, even if the template has
            # nothing to do with user input. It prevents injection/xss attacks
            # https://www.codiga.io/blog/python-jinja2-autoescape/
            # For SSTI vulnerability, it should to be handled in the FastAPI/RestApi routes
            # https://medium.com/dsf-developers/how-to-handle-an-ssti-vulnerability-in-jinja2-58242e561d4f
            autoescape=True,
            keep_trailing_newline=True,
            auto_reload=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def escape_curly_braces(self, input_string, open_brace="{{", close_brace="}}"):
        """
        Replaces all single curly braces in the input string with double curly braces.
        This is used to escape curly braces in the input string for templating systems like Jinja.

        :param input_string: The string in which to replace curly braces.
        :param open_brace: The string to replace single open curly braces.
        :param close_brace: The string to replace single close curly braces.
        :return: A new string with all curly braces replaced by the provided strings.
        """
        try:
            open_brace_placeholder = "_open_brace_"
            close_brace_placeholder = "_close_brace_"
            # Replace the intended curly braces with the placeholders
            input_string = input_string.replace("{", open_brace_placeholder).replace(
                "}", close_brace_placeholder
            )
            # Replace the placeholders with the provided strings
            escaped_string = input_string.replace(open_brace_placeholder, open_brace).replace(
                close_brace_placeholder, close_brace
            )
        except Exception as e:
            log.error(f"An error occurred: {e}")
            return input_string
        return escaped_string

    def generate_prompt(self, template_names, **kwargs) -> str:
        """Generates Prompt string from Jinja2 template if template name is Jinja file or from text
        file if tepmplate name is a text file
        Returns:
            str: the prompt as a string
        """

        prompt = ""

        for template_name in template_names:
            if template_name.endswith((".j2", ".jinja2", ".jinja")):
                prompt = prompt + self._generate_prompt_from_jinja(template_name, **kwargs)
            elif template_name.endswith((".txt", ".md")):
                prompt = prompt + self._generate_prompt_from_text_file(template_name, **kwargs)
            else:
                raise ValueError(f"Invalid template file extension: {template_name}")

        return prompt

    def _generate_prompt_from_jinja(self, template_name, **kwargs) -> str:
        """Generates Prompt string from Jinja2 template

        Returns:
            str: _Rendered template in order
        """
        for arg in kwargs:
            arg_value = kwargs[arg]
            if arg_value is None:
                arg_value = ""
            kwargs[arg] = self.escape_curly_braces(
                arg_value, open_brace="""{{'{{'}}""", close_brace="""{{'}}'}}"""
            )
        consolidated_template = self._env.get_template(template_name)
        rendered_template = consolidated_template.render(kwargs)
        return rendered_template

    def _generate_prompt_from_text_file(self, template_name, **kwargs) -> str:
        """
        Reads the content of a text file,
        removes leading and trailing whitespace,
        and returns the content as a string.

        :param template_name: Path to the text file.
        :return: A string with the content of the file, trimmed of leading and trailing whitespace.
        """
        try:
            text_root_dir = self.root_template_dir + "/text"
            text_file_path = path_join(text_root_dir, template_name)
            with open(text_file_path, "r", encoding="utf-8") as file:
                content = file.read()
                trimmed_content = content.strip()
                for arg in kwargs:
                    arg_value = kwargs[arg]
                    if arg_value is None:
                        arg_value = ""
                    escaped_arg = self.escape_curly_braces(arg_value)
                    trimmed_content = trimmed_content.replace(f"{{{arg}}}", escaped_arg)
                return trimmed_content
        except FileNotFoundError:
            log.error(f"Error: The file at {text_file_path} was not found.")
            return None
        except IOError as e:
            log.error(f"Error: An I/O error occurred. {e}")
            return None
