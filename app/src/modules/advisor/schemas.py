from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    menu_id: uuid.UUID
    question: str = Field(min_length=1, max_length=1000)
    # Recent turns kept by the client (ephemeral — nothing is stored server-side).
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    # Dishes the diner selected and wants the answer focused on (names). Empty =
    # ask about the whole menu.
    focus_dishes: list[str] = Field(default_factory=list, max_length=20)


class ChatResponse(BaseModel):
    answer: str
