GENERIC_ERROR_MESSAGE = "That’s embarrassing. For some reason, I wasn’t able to come up with a good response. Could you try asking me the question again?"

GENERIC_ERROR_MESSAGE_JSON = {"displayResponse": GENERIC_ERROR_MESSAGE, "voiceSummary": GENERIC_ERROR_MESSAGE}

SAFETY_ERROR_MESSAGE = "I'm sorry, I can't answer that question. Please ask something else."
SAFETY_ERROR_MESSAGE_JSON = {"displayResponse": SAFETY_ERROR_MESSAGE, "voiceSummary": SAFETY_ERROR_MESSAGE}

CHARACTER_LIMIT_ERROR_MESSAGE = "I'm sorry, the question you asked is too long. Please try asking a shorter question."
CHARACTER_LIMIT_ERROR_MESSAGE_JSON = {"displayResponse": CHARACTER_LIMIT_ERROR_MESSAGE, "voiceSummary": CHARACTER_LIMIT_ERROR_MESSAGE}

MAX_TURNS_EXCEEDED_ERROR_MESSAGE = "I'm sorry, unfortunately I am unable to continue this conversation. You have exceeded the maximum number of questions I am allowed to answer."
MAX_TURNS_EXCEEDED_ERROR_MESSAGE_JSON = {"displayResponse": MAX_TURNS_EXCEEDED_ERROR_MESSAGE, "voiceSummary": MAX_TURNS_EXCEEDED_ERROR_MESSAGE}
