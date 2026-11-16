from fastapi import FastAPI
from pydantic import BaseModel

from agent import ask

app = FastAPI(title="Stock Research Assistant")

class ChatRequest(BaseModel):
    question: str

@app.post("/chat")
def chat(request: ChatRequest):
    return ask(request.question)