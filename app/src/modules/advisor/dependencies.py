from __future__ import annotations

from fastapi import Depends

from src.core.config import settings
from src.modules.advisor.adapters.gemini_chat import (
    ChatProvider,
    GeminiChat,
    RuleBasedChat,
)
from src.modules.advisor.service import AdvisorService
from src.modules.menu.dependencies import get_menu_service
from src.modules.menu.service import MenuService


def get_chat_provider() -> ChatProvider:
    """Gemini when configured, else the rule-based fallback (dev/test)."""
    config = settings.llm
    if config.provider == "gemini" and config.api_key:
        return GeminiChat(
            api_key=config.api_key,
            api_base_url=config.api_base_url,
            model=config.model,
            timeout_seconds=config.timeout_seconds,
        )
    return RuleBasedChat()


def get_advisor_service(
    menu_service: MenuService = Depends(get_menu_service),
    chat_provider: ChatProvider = Depends(get_chat_provider),
) -> AdvisorService:
    return AdvisorService(menu_service=menu_service, chat_provider=chat_provider)
