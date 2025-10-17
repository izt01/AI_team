import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ChatReq(BaseModel):
    input: str

@router.post("/chat")
def chat(body: ChatReq):
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
              {"role":"system","content":"You are a helpful assistant."},
              {"role":"user","content": body.input}
            ],
        )
        return {"reply": r.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
