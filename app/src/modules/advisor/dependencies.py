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
    # Chat uses its OWN LLM config (separate from the scan pipeline).
    config = settings.chat_llm
    if config.provider == "gemini" and (config.api_key or config.api_keys):
        return GeminiChat(
            api_key=config.api_key or "",
            api_keys=config.api_keys,
            api_base_url=config.api_base_url,
            model=config.model,
            models=config.models,
            timeout_seconds=config.timeout_seconds,
        )
    return RuleBasedChat()


def get_advisor_service(
    menu_service: MenuService = Depends(get_menu_service),
    chat_provider: ChatProvider = Depends(get_chat_provider),
) -> AdvisorService:
    return AdvisorService(menu_service=menu_service, chat_provider=chat_provider)
