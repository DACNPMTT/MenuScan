"""Dining-session workflow service."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from src.modules.dining.exceptions import (
    DiningInviteInvalidError,
    DiningSessionClosedError,
    DiningSessionNotFoundError,
    DiningParticipantNotFoundError,
)
from src.modules.dining.models import (
    DiningSession,
    DiningSessionInvite,
    DiningSessionMode,
    DiningSessionParticipant,
    DiningSessionParticipantPreference,
    DiningSessionStatus,
    RecommendationVerdict,
    FoodItemRecommendation,
    FoodItemRecommendationParticipantBreakdown,
)
from src.modules.dining.repository import DiningSessionRepository
from src.modules.dining.schemas import DiningPreferenceRequest
from src.modules.identity.models import PreferenceType, User

if TYPE_CHECKING:
    from src.modules.menu.models import FoodItem, Menu


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DiningSessionInviteBundle:
    dining_session: DiningSession
    invite: DiningSessionInvite
    invite_token: str


def _append_unique(target: list[str], values: list[str]) -> None:
    seen = {value.lower() for value in target}
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        target.append(value)


def _dedupe(values: list[str]) -> list[str]:
    """Drop repeats, keep the order they were raised in — allergy before taste."""
    deduped: list[str] = []
    _append_unique(deduped, values)
    return deduped


_PREFERENCE_LABELS = {
    "spicy": "thích vị cay",
    "mild_spicy": "thích cay nhẹ",
    "savory": "thích vị đậm đà",
    "sour": "thích vị chua",
    "fresh": "thích món tươi mát",
    "grilled": "thích món nướng",
    "soup": "thích món nước",
    "noodles": "thích bún/mì/phở",
    "rice": "thích món cơm",
    "vegetables": "thích nhiều rau",
    "too_spicy": "tránh món quá cay",
    "too_sweet": "tránh món quá ngọt",
    "too_oily": "tránh món nhiều dầu",
    "fish_sauce": "tránh món có mắm",
    "strong_smell": "tránh món mùi nặng",
    "raw_food": "tránh đồ sống/tái",
    "organ_meat": "tránh nội tạng",
    "bitter": "tránh vị đắng",
    "heavy_cream": "tránh món quá béo/kem",
    "deep_fried": "tránh chiên ngập dầu",
}


def _preference_label(code: str) -> str:
    normalized = code.strip().lower()
    return _PREFERENCE_LABELS.get(normalized, normalized.replace("_", " "))


def _item_text(food_item: object) -> str:
    parts = [
        getattr(food_item, "original_name", None),
        getattr(food_item, "translated_name", None),
        getattr(food_item, "original_description", None),
        getattr(food_item, "translated_description", None),
        getattr(food_item, "assistant_summary", None),
        getattr(food_item, "risk_notes", None),
        getattr(food_item, "category", None),
    ]
    for attr in (
        "main_ingredients",
        "ingredient_tags",
        "flavor_tags",
        "texture_tags",
        "cooking_methods",
        "allergens",
        "dietary_tags",
    ):
        values = getattr(food_item, attr, None) or []
        parts.extend(str(value) for value in values)
    return " ".join(str(part or "") for part in parts).lower()


def _contains_any(text: str, needles: set[str]) -> bool:
    return any(needle in text for needle in needles)


def _level(food_item: object, attr: str) -> int:
    value = getattr(food_item, attr, None)
    return int(value) if isinstance(value, int) else 0


def _matches_preference(food_item: object, code: str) -> bool:
    normalized = code.strip().lower()
    text = _item_text(food_item)
    allergens = {str(value).lower() for value in (getattr(food_item, "allergens", []) or [])}
    dietary_tags = {
        str(value).lower() for value in (getattr(food_item, "dietary_tags", []) or [])
    }
    cooking_methods = {
        str(value).lower() for value in (getattr(food_item, "cooking_methods", []) or [])
    }
    flavor_tags = {
        str(value).lower() for value in (getattr(food_item, "flavor_tags", []) or [])
    }
    texture_tags = {
        str(value).lower() for value in (getattr(food_item, "texture_tags", []) or [])
    }
    ingredient_tags = {
        str(value).lower() for value in (getattr(food_item, "ingredient_tags", []) or [])
    }
    ingredients = ingredient_tags | {
        str(value).lower() for value in (getattr(food_item, "main_ingredients", []) or [])
    }

    if normalized in allergens or normalized in dietary_tags:
        return True
    if normalized == "seafood" and bool(allergens & {"seafood", "shellfish", "fish"}):
        return True
    if normalized in cooking_methods | flavor_tags | texture_tags | ingredients:
        return True

    match normalized:
        case "spicy":
            return _level(food_item, "spice_level") >= 3 or "spicy" in flavor_tags
        case "mild_spicy":
            return 1 <= _level(food_item, "spice_level") <= 2
        case "savory":
            return (
                _level(food_item, "saltiness_level") >= 2
                or "savory" in flavor_tags
                or "umami" in flavor_tags
            )
        case "sour":
            return _level(food_item, "sourness_level") >= 2 or "sour" in flavor_tags
        case "fresh":
            return (
                "fresh" in texture_tags
                or "raw" in cooking_methods
                or _contains_any(text, {"rau sống", "fresh", "herbs", "salad"})
            )
        case "grilled":
            return "grilled" in cooking_methods or _contains_any(
                text, {"grilled", "nướng", "bbq"}
            )
        case "soup":
            return _contains_any(text, {"soup", "broth", "nước dùng", "canh", "phở"})
        case "noodles":
            return _contains_any(
                text, {"noodle", "noodles", "bún", "mì", "miến", "phở", "hủ tiếu"}
            )
        case "rice":
            return "rice" in ingredients or _contains_any(text, {"rice", "cơm", "xôi"})
        case "vegetables":
            return _contains_any(
                text, {"vegetable", "vegetables", "rau", "herbs", "salad"}
            )
        case "too_spicy":
            return _level(food_item, "spice_level") >= 4
        case "too_sweet":
            return _level(food_item, "sweetness_level") >= 4
        case "too_oily":
            return _level(food_item, "oiliness_level") >= 4 or bool(
                cooking_methods & {"fried", "deep_fried", "stir_fried"}
            )
        case "fish_sauce":
            return _contains_any(
                text, {"fish sauce", "nước mắm", "nuoc mam", "mắm", "mam tom"}
            )
        case "strong_smell":
            return _contains_any(
                text, {"mắm", "fermented", "durian", "sầu riêng", "pungent"}
            )
        case "raw_food":
            return "raw" in cooking_methods or _contains_any(
                text, {"raw", "tái", "sống", "ceviche", "sashimi"}
            )
        case "organ_meat":
            return _contains_any(
                text, {"organ", "liver", "heart", "kidney", "tripe", "lòng", "gan"}
            )
        case "bitter":
            return _level(food_item, "sourness_level") >= 4 and "bitter" in flavor_tags
        case "heavy_cream":
            return (
                _level(food_item, "richness_level") >= 4
                or "dairy" in allergens
                or _contains_any(text, {"cream", "kem", "butter", "bơ"})
            )
        case "deep_fried":
            return "deep_fried" in cooking_methods or _contains_any(
                text, {"deep fried", "chiên giòn", "chiên ngập dầu"}
            )
        case _:
            return normalized in text


def _is_dietary_rule_violated(food_item: object, rule: str) -> bool:
    normalized = rule.strip().lower()
    allergens = {str(value).lower() for value in (getattr(food_item, "allergens", []) or [])}
    tags = {str(value).lower() for value in (getattr(food_item, "dietary_tags", []) or [])}

    if normalized == "vegan":
        return "vegan" not in tags
    if normalized == "vegetarian":
        return "vegetarian" not in tags and "vegan" not in tags
    if normalized in {"no_pork", "contains_pork"}:
        return "contains_pork" in tags
    if normalized in {"no_beef", "contains_beef"}:
        return "contains_beef" in tags
    if normalized in {"no_alcohol", "contains_alcohol"}:
        return "contains_alcohol" in tags
    if normalized in {"no_seafood", "contains_seafood"}:
        return "contains_seafood" in tags or bool(
            allergens & {"seafood", "shellfish", "fish"}
        )
    return _matches_preference(food_item, normalized)


@dataclass(frozen=True, slots=True)
class _Diner:
    """One person whose taste we actually know, for scoring one dish.

    ``participant`` is None for the session host, who is not a row in
    ``dining_session_participants`` and so cannot carry a breakdown.
    """

    display_name: str
    preferences: list[object]
    participant: DiningSessionParticipant | None


class DiningSessionService:
    def __init__(
        self,
        *,
        session: Session,
        repository: DiningSessionRepository | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._repository = repository or DiningSessionRepository()
        self._clock = clock or _utcnow

    def list_sessions(self, user: User) -> list[DiningSession]:
        return self._repository.list_owned(self._session, user_id=user.id)

    def get_session(self, user: User, *, session_id: uuid.UUID) -> DiningSession:
        dining_session = self._repository.get_owned(
            self._session,
            session_id=session_id,
            user_id=user.id,
        )
        if dining_session is None:
            raise DiningSessionNotFoundError()
        return dining_session

    def create_session(
        self,
        user: User,
        *,
        mode: str,
        invite_expires_in_hours: int | None,
    ) -> DiningSessionInviteBundle:
        now = self._clock()
        invite_token = self._create_invite_token()
        dining_session = DiningSession(
            created_by_user_id=user.id,
            mode=DiningSessionMode(mode),
            status=DiningSessionStatus.COLLECTING,
            created_at=now,
            updated_at=now,
        )
        self._repository.add_session(self._session, dining_session)
        self._session.flush()

        invite = DiningSessionInvite(
            dining_session_id=dining_session.id,
            token_hash=self._hash_invite_token(invite_token),
            expires_at=(
                now + timedelta(hours=invite_expires_in_hours)
                if invite_expires_in_hours is not None
                else None
            ),
            max_uses=None,
            use_count=0,
            created_at=now,
        )
        self._repository.add_invite(self._session, invite)
        self._session.commit()
        return DiningSessionInviteBundle(
            dining_session=dining_session,
            invite=invite,
            invite_token=invite_token,
        )

    def get_public_session(self, *, invite_token: str) -> DiningSession:
        invite = self._get_valid_invite(invite_token)
        return invite.dining_session

    def join_with_invite(
        self,
        *,
        invite_token: str,
        display_name: str,
        preferences: list[DiningPreferenceRequest],
    ) -> DiningSessionParticipant:
        invite = self._get_valid_invite(invite_token)
        dining_session = invite.dining_session
        if dining_session.status in {
            DiningSessionStatus.COMPLETED,
            DiningSessionStatus.CLOSED,
        }:
            raise DiningSessionClosedError()

        now = self._clock()
        participant = DiningSessionParticipant(
            dining_session_id=dining_session.id,
            display_name=display_name,
            joined_at=now,
        )
        participant.preferences = self._build_preferences(preferences, created_at=now)
        invite.use_count += 1
        dining_session.updated_at = now
        self._repository.add_participant(self._session, participant)
        self._session.commit()
        return participant

    def delete_session(self, user: User, *, session_id: uuid.UUID) -> None:
        dining_session = self.get_session(user, session_id=session_id)
        now = self._clock()
        dining_session.deleted_at = now
        dining_session.updated_at = now
        self._session.commit()

    def associate_scan_session(
        self,
        user: User,
        *,
        session_id: uuid.UUID,
        scan_session_id: uuid.UUID,
    ) -> DiningSession:
        dining_session = self.get_session(user, session_id=session_id)
        dining_session.scan_session_id = scan_session_id
        dining_session.status = DiningSessionStatus.SCANNING
        dining_session.updated_at = self._clock()
        self._session.commit()
        return dining_session

    def remove_participant(
        self,
        user: User,
        *,
        session_id: uuid.UUID,
        participant_id: uuid.UUID,
    ) -> None:
        dining_session = self.get_session(user, session_id=session_id)
        participant = next(
            (p for p in dining_session.participants if p.id == participant_id),
            None,
        )
        if participant is None:
            raise DiningParticipantNotFoundError()

        self._session.delete(participant)
        dining_session.updated_at = self._clock()
        self._session.commit()

    def attach_menu(
        self,
        *,
        scan_session_id: uuid.UUID,
        menu: Menu,
    ) -> DiningSession | None:
        """Point the dining session that requested this scan at the menu it made.

        Returns None for an ordinary personal scan, which has no session — and
        never creates one. Does not commit: the scan pipeline owns the
        transaction.
        """
        dining_session = (
            self._session.query(DiningSession)
            .filter(
                DiningSession.scan_session_id == scan_session_id,
                DiningSession.deleted_at.is_(None),
            )
            .first()
        )
        if dining_session is None:
            return None

        now = self._clock()
        dining_session.menu_id = menu.id
        dining_session.status = DiningSessionStatus.COMPLETED
        dining_session.updated_at = now
        dining_session.completed_at = now
        self._session.flush()
        return dining_session

    def generate_recommendations(
        self,
        *,
        dining_session: DiningSession,
        food_items: list[FoodItem],
    ) -> int:
        """(Re)score every dish for this session's diners. Returns rows written.

        Idempotent: it wipes the session's existing verdicts first, so calling it
        again after a re-enrichment — or after a new diner joins — rewrites the
        set instead of colliding with the (session, dish) unique key.

        Does NOT commit; the caller owns the transaction. It must only be called
        once the dishes carry their food-intelligence tags, because that is what a
        verdict is scored from. Scoring an untagged dish is what produced the
        "100/100 recommended" advice this rework exists to kill.
        """
        from src.modules.identity.models import FoodProfile

        # delete-orphan on DiningSession.recommendations issues the DELETEs, and
        # each recommendation takes its own breakdowns with it. The flush is
        # load-bearing: without it the unit of work can order the new INSERTs
        # before the DELETEs and trip the unique key.
        dining_session.recommendations.clear()
        self._session.flush()

        host_profile = None
        if dining_session.created_by_user_id is not None:
            host_profile = (
                self._session.query(FoodProfile)
                .filter(
                    FoodProfile.user_id == dining_session.created_by_user_id,
                    FoodProfile.is_default,
                    FoodProfile.deleted_at.is_(None),
                )
                .first()
            )

        # Only diners who have actually told us something. Someone who declared no
        # preference gives no signal, and we will not invent one on their behalf.
        diners: list[_Diner] = []
        if host_profile is not None and host_profile.preferences:
            diners.append(
                _Diner(
                    display_name=host_profile.display_name or "Host",
                    preferences=list(host_profile.preferences),
                    participant=None,
                )
            )
        for participant in dining_session.participants:
            if participant.preferences:
                diners.append(
                    _Diner(
                        display_name=participant.display_name,
                        preferences=list(participant.preferences),
                        participant=participant,
                    )
                )

        if not diners:
            return 0

        return sum(
            self._write_item_verdict(dining_session, item, diners) for item in food_items
        )

    def _write_item_verdict(
        self,
        dining_session: DiningSession,
        item: FoodItem,
        diners: list[_Diner],
    ) -> int:
        group_verdict = RecommendationVerdict.RECOMMENDED
        score_sum = 0.0
        scored_diners = 0
        fit_reasons_all: list[str] = []
        risk_reasons_all: list[str] = []
        suggested_for: list[str] = []
        warning_for: list[str] = []
        breakdowns: list[FoodItemRecommendationParticipantBreakdown] = []

        for diner in diners:
            scored = self._score_item_for_diner(item, diner.preferences)
            if scored is None:
                continue
            verdict, score, fit, risk = scored

            score_sum += score
            scored_diners += 1
            fit_reasons_all.extend(fit)
            risk_reasons_all.extend(risk)

            if verdict == RecommendationVerdict.RECOMMENDED:
                _append_unique(suggested_for, [diner.display_name])
            elif verdict == RecommendationVerdict.AVOID:
                _append_unique(warning_for, [diner.display_name])
                group_verdict = RecommendationVerdict.AVOID
            elif verdict == RecommendationVerdict.CAUTION:
                if group_verdict != RecommendationVerdict.AVOID:
                    group_verdict = RecommendationVerdict.CAUTION

            # Only participants get a breakdown row; the host is not a participant.
            if diner.participant is not None:
                breakdowns.append(
                    FoodItemRecommendationParticipantBreakdown(
                        id=uuid.uuid4(),
                        participant_id=diner.participant.id,
                        verdict=verdict,
                        score=Decimal(str(round(score, 2))),
                        explanation=f"Độ phù hợp cá nhân {score:.0f}/100.",
                        fit_reasons=fit,
                        risk_reasons=risk,
                        created_at=self._clock(),
                    )
                )

        if scored_diners == 0:
            return 0

        final_score = score_sum / scored_diners
        if group_verdict != RecommendationVerdict.AVOID:
            if final_score >= 75.0:
                group_verdict = RecommendationVerdict.RECOMMENDED
            elif final_score >= 40.0:
                group_verdict = RecommendationVerdict.OK
            else:
                group_verdict = RecommendationVerdict.CAUTION

        # Keep the order the reasons were raised in: allergy first, then diet, then
        # taste. Sorting them alphabetically (as this used to) buries the reason
        # that matters under whichever one happens to start with an "A".
        fit_reasons = _dedupe(fit_reasons_all)
        risk_reasons = _dedupe(risk_reasons_all)
        if not fit_reasons and group_verdict in {
            RecommendationVerdict.RECOMMENDED,
            RecommendationVerdict.OK,
        }:
            fit_reasons = ["Phù hợp với hồ sơ ăn uống"]

        rec = FoodItemRecommendation(
            id=uuid.uuid4(),
            dining_session_id=dining_session.id,
            food_item_id=item.id,
            verdict=group_verdict,
            score=Decimal(str(round(final_score, 2))),
            explanation=f"Độ phù hợp {final_score:.0f}/100.",
            why_suitable=", ".join(fit_reasons) if fit_reasons else None,
            why_not_suitable=", ".join(risk_reasons) if risk_reasons else None,
            suggested_for=suggested_for,
            warning_for=warning_for,
            fit_reasons=fit_reasons,
            risk_reasons=risk_reasons,
            warning_reasons=(
                risk_reasons
                if group_verdict
                in {RecommendationVerdict.AVOID, RecommendationVerdict.CAUTION}
                else []
            ),
            created_at=self._clock(),
        )
        self._session.add(rec)

        for breakdown in breakdowns:
            breakdown.food_item_recommendation_id = rec.id
            if not breakdown.fit_reasons and breakdown.verdict in {
                RecommendationVerdict.RECOMMENDED,
                RecommendationVerdict.OK,
            }:
                breakdown.fit_reasons = fit_reasons
            if not breakdown.risk_reasons and breakdown.verdict in {
                RecommendationVerdict.AVOID,
                RecommendationVerdict.CAUTION,
            }:
                breakdown.risk_reasons = risk_reasons
            self._session.add(breakdown)

        return 1


    @staticmethod
    def _score_item_for_diner(
        food_item: FoodItem,
        preferences: list[object],
    ) -> tuple[RecommendationVerdict, float, list[str], list[str]] | None:
        """Score one dish against one diner. None when we know nothing about them.

        The score starts at 100 and is only pushed down by a preference that
        matches, so a diner who has declared nothing scores every dish 100/100
        RECOMMENDED — the app confidently advising someone it knows nothing about.
        Returning None instead means the UI shows no verdict, which is the truth.
        """
        if not preferences:
            return None

        score = 100.0
        verdict = RecommendationVerdict.RECOMMENDED
        fit_reasons: list[str] = []
        risk_reasons: list[str] = []

        for pref in preferences:
            code = getattr(pref, "code", "")
            pref_type = getattr(pref, "preference_type", "")
            pref_type = pref_type.value if hasattr(pref_type, "value") else str(pref_type)
            importance = getattr(pref, "importance", 3) or 3
            label = _preference_label(code)

            if pref_type == "ALLERGY":
                if _matches_preference(food_item, code):
                    score = 0.0
                    verdict = RecommendationVerdict.AVOID
                    _append_unique(risk_reasons, [f"Dị ứng với {label}"])

            elif pref_type == "DIETARY_RULE":
                if _is_dietary_rule_violated(food_item, code):
                    score = 0.0
                    verdict = RecommendationVerdict.AVOID
                    _append_unique(risk_reasons, [f"Không phù hợp quy tắc ăn: {label}"])

            elif pref_type == "AVOID":
                if _matches_preference(food_item, code):
                    penalty = 15.0 + importance * 8.0
                    score = max(0.0, score - penalty)
                    if verdict != RecommendationVerdict.AVOID:
                        verdict = RecommendationVerdict.CAUTION
                    _append_unique(risk_reasons, [f"Nên cân nhắc vì bạn {label}"])

            elif pref_type == "DISLIKE":
                if _matches_preference(food_item, code):
                    penalty = 10.0 + importance * 5.0
                    score = max(0.0, score - penalty)
                    if verdict not in {RecommendationVerdict.AVOID, RecommendationVerdict.CAUTION}:
                        verdict = RecommendationVerdict.OK
                    _append_unique(risk_reasons, [f"Có điểm bạn không thích: {label}"])

            elif pref_type == "LIKE":
                if _matches_preference(food_item, code):
                    score = min(100.0, score + 5.0 + importance * 3.0)
                    _append_unique(fit_reasons, [f"Phù hợp vì bạn {label}"])

        if score >= 75.0:
            verdict = RecommendationVerdict.RECOMMENDED
        elif score >= 40.0:
            if verdict not in {RecommendationVerdict.AVOID, RecommendationVerdict.CAUTION}:
                verdict = RecommendationVerdict.OK
        else:
            if verdict != RecommendationVerdict.AVOID:
                verdict = RecommendationVerdict.CAUTION

        return verdict, score, fit_reasons, risk_reasons

    def _get_valid_invite(self, invite_token: str) -> DiningSessionInvite:
        invite = self._repository.get_invite_by_hash(
            self._session,
            token_hash=self._hash_invite_token(invite_token),
        )
        now = self._clock()
        if (
            invite is None
            or invite.revoked_at is not None
            or invite.dining_session.deleted_at is not None
            or (invite.expires_at is not None and invite.expires_at <= now)
            or (invite.max_uses is not None and invite.use_count >= invite.max_uses)
        ):
            raise DiningInviteInvalidError()
        return invite

    @staticmethod
    def _build_preferences(
        preferences: list[DiningPreferenceRequest],
        *,
        created_at: datetime,
    ) -> list[DiningSessionParticipantPreference]:
        seen: set[tuple[str, str]] = set()
        records: list[DiningSessionParticipantPreference] = []
        for item in preferences:
            key = (item.code, item.preference_type)
            if key in seen:
                continue
            seen.add(key)
            records.append(
                DiningSessionParticipantPreference(
                    code=item.code,
                    category=item.category,
                    preference_type=PreferenceType(item.preference_type),
                    intensity=item.intensity,
                    importance=item.importance,
                    note=item.note,
                    created_at=created_at,
                )
            )
        return records

    @staticmethod
    def _create_invite_token() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def _hash_invite_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
