import json
import urllib.error
import urllib.request

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import get_settings
from app.deps import CurrentUser
from app.errors import AppError

router = APIRouter(tags=["chat"])

SYSTEM_PROMPT = (
    "You are the Samavesh assistant. Samavesh is a platform for students with disabilities "
    "to manage accommodation plans, compliance reminders, and grievances. Answer briefly and "
    "accurately. If you do not know something about the platform, say so."
)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


@router.post("/chat")
def chat(body: ChatIn, user: CurrentUser):
    s = get_settings()
    payload = {
        "model": s.ollama_model,
        "stream": False,
        "think": False,  # qwen3: skip the reasoning trace for fast answers
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": body.message},
        ],
    }
    req = urllib.request.Request(
        s.ollama_url.rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            reply = json.load(res)["message"]["content"]
    except (urllib.error.URLError, KeyError, ValueError):
        raise AppError(503, "assistant_unavailable", "The assistant is unavailable right now.")
    return {"reply": reply}
