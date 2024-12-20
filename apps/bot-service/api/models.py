from typing import List

from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class Input(BaseModel):
    messages: List[Message]


class Configurable(BaseModel):
    session_id: str
    user_id: str


class Config(BaseModel):
    configurable: Configurable


class Payload(BaseModel):
    input: Input
    config: Config


class Output(BaseModel):
    question: str
    called_tools: list = []
    search_documents: list = []
    answer: str
