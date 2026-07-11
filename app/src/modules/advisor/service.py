from __future__ import annotations

import uuid

from src.modules.advisor.adapters.gemini_chat import ChatProvider
from src.modules.advisor.schemas import ChatMessage
from src.modules.identity.models import User
from src.modules.menu.schemas import MenuDetailResponse, MenuItemResponse
from src.modules.menu.service import MenuService

# How the assistant must behave. The three-tier rule keeps taste/subjective
# answers honest instead of generic: state facts only from the menu data, mark
# guesses as guesses, and admit when it doesn't know.
_SYSTEM_RULES = """\
You are MenuScan's dining assistant. Help the diner choose dishes from THIS menu.
Answer in the same language as the user's question. Be concise, warm and
conversational — like a knowledgeable friend, not a textbook.

Formatting rules for your reply:
- Start with a short friendly intro sentence about the dish.
- Use **bold** for dish names, key ingredients, allergens, and important warnings.
- Use bullet points (- ) to list details when there are multiple pieces of info
  (e.g. ingredients, flavor notes, allergens). Keep each bullet short.
- Use a blank line between logical sections (intro → details → warnings).
- For allergen/dietary warnings, put them at the end with a ⚠️ prefix.
- Keep the total reply under 150 words. No headers (#), no numbered lists.

Confidence rules (internal — NEVER show these labels):
1. If a dish's tags or description state a fact, answer confidently.
2. If the data doesn't say, give a short guess from the dish name and common
   food knowledge, but naturally flag it ("thường thì…", "có thể…") and
   suggest confirming with the restaurant.
3. If you can't tell at all, say the menu doesn't specify and suggest asking
   the staff.

Hard rules:
- NEVER invent specific ingredients or allergens as fact.
- For allergies always say a dish "may contain" X — never call it "safe".
- Do not answer questions unrelated to this menu.
"""




def _item_line(item: MenuItemResponse) -> str:
    name = item.translated_name or item.original_name
    if item.translated_name and item.translated_name != item.original_name:
        name = f"{item.translated_name} ({item.original_name})"
    desc = item.translated_description or item.original_description or "-"
    tags = ", ".join(item.dietary_tags) or "-"
    allergens = ", ".join(item.allergens) or "-"
    parts = [f"- {name}"]
    if item.category:
        parts.append(f"[{item.category}]")
    parts.append(f"| desc: {desc} | tags: {tags} | allergens: {allergens}")
    return " ".join(parts)


def _build_context(menu: MenuDetailResponse, user: User) -> str:
    dishes = "\n".join(_item_line(item) for item in menu.items) or "(no dishes)"
    allergies = ", ".join(user.allergies or []) or "none declared"
    diet = ", ".join(user.dietary_preferences or []) or "none declared"
    return (
        f"MENU: {menu.title}\n"
        f"DISHES:\n{dishes}\n\n"
        f"DINER PROFILE — allergies: {allergies}; diet: {diet}"
    )


def _to_provider_role(role: str) -> str:
    # Gemini uses "model" for assistant turns.
    return "model" if role == "assistant" else "user"


class AdvisorService:
    def __init__(self, *, menu_service: MenuService, chat_provider: ChatProvider) -> None:
        self._menu_service = menu_service
        self._chat = chat_provider

    def chat(
        self,
        *,
        user: User,
        menu_id: uuid.UUID,
        question: str,
        history: list[ChatMessage],
        focus_dishes: list[str] | None = None,
    ) -> str:
        # Ownership + existence enforced here (raises 404 when not the owner).
        menu = self._menu_service.get_menu(menu_id=menu_id, user_id=user.id)
        system = f"{_SYSTEM_RULES}\n\n{_build_context(menu, user)}"
        if focus_dishes:
            names = ", ".join(dish.strip() for dish in focus_dishes if dish.strip())
            if names:
                system += (
                    f"\n\nThe diner is asking about these selected dishes: {names}. "
                    "Focus your answer on them."
                )
        # Keep only the last few turns to bound the prompt.
        recent = history[-6:]
        messages = [(_to_provider_role(m.role), m.content) for m in recent]
        messages.append(("user", question))
        return self._chat.complete(system=system, messages=messages)
