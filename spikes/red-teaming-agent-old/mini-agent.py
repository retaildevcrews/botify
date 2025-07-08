import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from agents import Agent, Runner, OpenAIChatCompletionsModel
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
import os
import uuid
from datetime import datetime
import uvicorn

# Load environment variables from .env file
load_dotenv("credentials.env")

app = FastAPI(title="OpenAI Agent API", version="1.0.0")
agent = None

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[dict]
    usage: dict

async def initialize_agent():
    global agent
    try:
        # Create the Async Azure OpenAI client
        client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )

        agent = Agent(
            name="Assistant",
            instructions="You are a helpful assistant",
            model=OpenAIChatCompletionsModel(
                    model=os.getenv("AZURE_OPENAI_MODEL_NAME"),
                    openai_client=client,
                )
        )
    except Exception as e:
        print(f"Error initializing Azure OpenAI client or agent: {e}")
        print("Please check your environment variables in credentials.env")
        raise e

@app.on_event("startup")
async def startup_event():
    await initialize_agent()

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    try:
        if not request.messages:
            raise HTTPException(status_code=400, detail="Messages array cannot be empty")

        # Get the last user message
        user_message = None
        for msg in reversed(request.messages):
            if msg.role == 'user':
                user_message = msg.content
                break

        if not user_message:
            raise HTTPException(status_code=400, detail="No user message found")

        # Run the agent asynchronously
        result = await Runner.run(agent, user_message)

        # Format response in OpenAI chat completions format
        response = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:29]}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": os.getenv("AZURE_OPENAI_MODEL_NAME", "gpt-4"),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result.final_output
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(result.final_output.split()),
                "total_tokens": len(user_message.split()) + len(result.final_output.split())
            }
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "agent_initialized": agent is not None}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
