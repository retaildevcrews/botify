from pydantic import BaseModel
from typing import List


class Input(BaseModel):
    question: str


class Configurable(BaseModel):
    session_id: str
    user_id: str


class Config(BaseModel):
    configurable: Configurable


class Payload(BaseModel):
    input: Input
    config: Config
