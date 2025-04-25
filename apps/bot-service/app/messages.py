GENERIC_ERROR_MESSAGE = """That’s embarrassing.
For some reason, I wasn’t able to come up with a good response.
Could you try asking me the question again?"""

SAFETY_ERROR_MESSAGE = """I'm afraid you have violated the terms of service.
I am unable to engage with that type of question."""

CHARACTER_LIMIT_ERROR_MESSAGE = """I'm sorry, the question you asked
is too long. Please try asking a shorter question."""

MAX_TURNS_EXCEEDED_ERROR_MESSAGE = """I'm sorry, unfortunately I am unable
to continue this conversation. You have exceeded the maximum number of
questions I am allowed to answer."""


def get_json_error_message(error_message: str) -> dict:
    return {"displayResponse": error_message, "voiceSummary": error_message}


GENERIC_ERROR_MESSAGE_JSON = get_json_error_message(GENERIC_ERROR_MESSAGE)

SAFETY_ERROR_MESSAGE_JSON = get_json_error_message(SAFETY_ERROR_MESSAGE)

CHARACTER_LIMIT_ERROR_MESSAGE_JSON = get_json_error_message(CHARACTER_LIMIT_ERROR_MESSAGE)

MAX_TURNS_EXCEEDED_ERROR_MESSAGE_JSON = get_json_error_message(MAX_TURNS_EXCEEDED_ERROR_MESSAGE)
