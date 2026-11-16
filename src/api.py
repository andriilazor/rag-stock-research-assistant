from fastapi import FastAPI
from fastapi.sse import EventSourceResponse
from pydantic import BaseModel

from agent import ask, ask_stream

app = FastAPI(title="Stock Research Assistant")

class ChatRequest(BaseModel):
    question: str

@app.post("/chat")
def chat(request: ChatRequest):
    return ask(request.question)

@app.post("/chat/stream", response_class=EventSourceResponse)
async def chat_stream(request: ChatRequest):
    async for token in ask_stream(request.question):
        yield token