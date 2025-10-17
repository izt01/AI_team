import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

FRONT = os.getenv("FRONT_ORIGIN", "*")
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONT] if FRONT != "*" else ["*"],
    allow_methods=["*"], allow_headers=["*"]
)

@app.get("/health")
def health(): return {"ok": True}

# /api プレフィックスの例
from .routers import chat
app.include_router(chat.router, prefix="/api", tags=["ai"])
