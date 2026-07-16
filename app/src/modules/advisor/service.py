from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.modules.advisor.adapters.gemini_chat import ChatProvider
from src.modules.advisor.schemas import ChatMessage
from src.modules.identity.models import FoodProfile, FoodProfilePreference, User
from src.modules.menu.models import FoodItem, Menu
from src.modules.menu.service import MenuService

# How the assistant must behave. The three-tier rule keeps taste/subjective
# answers honest instead of generic: state facts only from the menu data, mark
# guesses as guesses, and admit when it doesn't know.
_SYSTEM_RULES = """\
You are MenuScan's dining assistant. A traveller is standing in front of a menu
they cannot read, deciding what to order. Help them.

LANGUAGE — this one is absolute:
Reply in the SAME language the diner wrote their question in. Not the menu's
language, not the app's. If they write in English, answer in English. If they
write in Vietnamese, answer in Vietnamese. If they switch languages mid-chat,
switch with them. Dish names may stay in their original language, with a short
gloss when it helps.

HOW TO TALK:
Like a friend who knows the food, not a form. Answer the question they asked, at
the length it deserves — one line for "is it spicy?", a proper answer for "what
should I get?". Don't lead every reply with a greeting. Don't force bullets onto a
one-sentence answer; use them only when you are genuinely listing several things.
Bold a dish name when you name one. If the question is vague, just ask what they
mean instead of guessing broadly.

WHAT YOU CAN TELL THEM ABOUT A DISH:
Everything they'd want before ordering — what's in it, how it's cooked, what it
tastes like (spicy, sweet, rich…), roughly what it costs, whether it clashes with
their allergies or diet, and how it compares to other dishes on the menu. The dish
lines below carry whatever the scan and analysis found; where a field is missing,
fall back to what the dish name and description tell you.

HOW SURE YOU ARE (never say these labels out loud, just behave this way):
1. If the dish data states something, say it plainly.
2. If it doesn't, infer from the dish name and ordinary food knowledge — but make
   the uncertainty audible in the way you phrase it ("usually…", "it's likely…",
   "thường thì…") and suggest checking with the restaurant.
3. If you genuinely cannot tell, say so and point them at the staff. That is a
   better answer than a confident invention.

HARD RULES:
- Never state a specific ingredient or allergen as fact when you are inferring it.
- For allergies, say a dish "may contain" X. Never call a dish "safe" — you are
  reading a photo of a menu, not the kitchen.
- Stay on this menu and this meal.
"""


def _item_line(item: FoodItem, currency: str | None) -> str:
    name = item.translated_name or item.original_name
    if item.translated_name and item.translated_name != item.original_name:
        name = f"{item.translated_name} ({item.original_name})"

    parts = [f"- {name}"]
    if item.category:
        parts.append(f"[{item.category}]")

    fields: list[str] = []
    # Price was missing entirely, so "what's the cheapest?" — the single most
    # obvious question a diner asks a menu assistant — was unanswerable.
    if item.price is not None:
        fields.append(f"price: {item.price} {item.currency or currency or ''}".strip())
    summary = item.assistant_summary or item.translated_description
    fields.append(f"desc: {summary or item.original_description or '-'}")
    if item.main_ingredients:
        fields.append(f"ingredients: {', '.join(item.main_ingredients)}")
    taste = [
        f"{label} {value}/5"
        for label, value in (
            ("spicy", item.spice_level),
            ("sweet", item.sweetness_level),
            ("salty", item.saltiness_level),
            ("sour", item.sourness_level),
            ("rich", item.richness_level),
            ("oily", item.oiliness_level),
        )
        if value
    ]
    if taste:
        fields.append(f"taste: {', '.join(taste)}")
    if item.cooking_methods:
        fields.append(f"cooked: {', '.join(item.cooking_methods)}")
    fields.append(f"diet: {', '.join(item.dietary_tags) or '-'}")
    fields.append(f"allergens: {', '.join(item.allergens) or '-'}")
    if item.risk_notes:
        fields.append(f"caution: {item.risk_notes}")

    parts.append("| " + " | ".join(fields))
    return " ".join(parts)


def _build_context(menu: Menu, preferences: list[FoodProfilePreference]) -> str:
    dishes = (
        "\n".join(
            _item_line(item, menu.default_currency)
            for item in sorted(menu.food_items, key=lambda item: item.sort_order)
        )
        or "(no dishes)"
    )

    # Read the SAME food profile the dish cards score their verdicts from. The chat
    # used to read user.allergies / user.dietary_preferences instead, so it could
    # cheerfully recommend a dish while the card beside it showed a red AVOID.
    if preferences:
        declared = "; ".join(
            f"{preference.preference_type.value.lower()}: {preference.code}"
            for preference in preferences
        )
    else:
        declared = "none declared"

    return f"MENU: {menu.title}\nDISHES:\n{dishes}\n\nDINER PROFILE — {declared}"


def _to_provider_role(role: str) -> str:
    # Gemini uses "model" for assistant turns.
    return "model" if role == "assistant" else "user"


class AdvisorService:
    def __init__(
        self,
        *,
        session: Session,
        menu_service: MenuService,
        chat_provider: ChatProvider,
    ) -> None:
        self._session = session
        self._menu_service = menu_service
        self._chat = chat_provider

    def _diner_preferences(self, user: User) -> list[FoodProfilePreference]:
        profile = self._session.scalars(
            select(FoodProfile)
            .where(
                FoodProfile.user_id == user.id,
                FoodProfile.is_default,
                FoodProfile.deleted_at.is_(None),
            )
            .options(selectinload(FoodProfile.preferences))
        ).first()
        return list(profile.preferences) if profile is not None else []

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
        menu = self._menu_service.get_menu_for_grounding(
            menu_id=menu_id,
            user_id=user.id,
        )
        context = _build_context(menu, self._diner_preferences(user))
        system = f"{_SYSTEM_RULES}\n\n{context}"
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
