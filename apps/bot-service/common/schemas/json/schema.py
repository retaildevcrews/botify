from pydantic import BaseModel


class Response(BaseModel):
    voiceSummary: str
    displayResponse: str
