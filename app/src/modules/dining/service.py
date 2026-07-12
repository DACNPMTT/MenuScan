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


def _clean_text_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        cleaned.append(text[:160])
    return cleaned


def _append_unique(target: list[str], values: list[str]) -> None:
    seen = {value.lower() for value in target}
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        target.append(value)


def _coerce_verdict(value: object, default: RecommendationVerdict) -> RecommendationVerdict:
    try:
        return RecommendationVerdict(str(value or default.value).upper())
    except ValueError:
        return default


def _decimal_score(value: object, default: float = 100.0) -> Decimal:
    try:
        score = float(value if value is not None else default)
    except (TypeError, ValueError):
        score = default
    return Decimal(str(round(max(0.0, min(100.0, score)), 2)))


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


def _recommendation_explanation(
    *,
    score: float,
    fit_reasons: list[str],
    risk_reasons: list[str],
    scope: str,
) -> str:
    if risk_reasons and fit_reasons:
        return (
            f"Độ phù hợp {scope} {score:.0f}/100. "
            f"Hợp ở điểm: {', '.join(fit_reasons[:2])}. "
            f"Cần chú ý: {', '.join(risk_reasons[:2])}."
        )
    if risk_reasons:
        return (
            f"Độ phù hợp {scope} {score:.0f}/100. "
            f"Cần chú ý: {', '.join(risk_reasons[:3])}."
        )
    if fit_reasons:
        return (
            f"Độ phù hợp {scope} {score:.0f}/100. "
            f"Món này hợp vì {', '.join(fit_reasons[:3])}."
        )
    return (
        f"Độ phù hợp {scope} {score:.0f}/100. "
        "Chưa thấy xung đột rõ với hồ sơ ăn uống đã khai báo."
    )


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
        target_language: str,
        mode: str,
        invite_expires_in_hours: int | None,
    ) -> DiningSessionInviteBundle:
        now = self._clock()
        invite_token = self._create_invite_token()
        dining_session = DiningSession(
            created_by_user_id=user.id,
            mode=DiningSessionMode(mode),
            status=DiningSessionStatus.COLLECTING,
            target_language=target_language,
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
        preferred_language: str,
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
            preferred_language=preferred_language,
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

    def generate_recommendations(
        self,
        *,
        dining_session: DiningSession,
        menu: Menu,
        food_items: list[FoodItem],
        draft_items: list[object] | None = None,
    ) -> None:
        from src.modules.identity.models import FoodProfile

        # Check if we have LLM-generated recommendations in draft_items
        has_draft_recs = False
        if draft_items:
            has_draft_recs = any(getattr(d, "recommendation", None) is not None for d in draft_items)

        if has_draft_recs and draft_items:
            food_item_by_name = {item.original_name.strip().lower(): item for item in food_items}
            participant_by_name = {p.display_name.strip().lower(): p for p in dining_session.participants}

            for d_item in draft_items:
                original_name = getattr(d_item, "original_name", "")
                saved_item = food_item_by_name.get(original_name.strip().lower())
                d_rec = getattr(d_item, "recommendation", None)
                if not saved_item or not d_rec:
                    continue

                verdict_enum = _coerce_verdict(
                    getattr(d_rec, "verdict", None),
                    RecommendationVerdict.RECOMMENDED,
                )
                explanation = str(getattr(d_rec, "explanation", "") or "").strip() or None
                why_suitable = str(getattr(d_rec, "why_suitable", "") or "").strip() or None
                why_not_suitable = str(getattr(d_rec, "why_not_suitable", "") or "").strip() or None
                suggested_for = _clean_text_list(getattr(d_rec, "suggested_for", []))
                warning_for = _clean_text_list(getattr(d_rec, "warning_for", []))
                fit_reasons = _clean_text_list(getattr(d_rec, "fit_reasons", []))
                risk_reasons = _clean_text_list(getattr(d_rec, "risk_reasons", []))
                warning_reasons = _clean_text_list(
                    getattr(d_rec, "warning_reasons", [])
                )

                participant_breakdowns: list[
                    tuple[
                        DiningSessionParticipant,
                        RecommendationVerdict,
                        Decimal,
                        str | None,
                        list[str],
                        list[str],
                    ]
                ] = []
                d_breakdowns = getattr(d_item, "participant_breakdowns", []) or []
                for bd in d_breakdowns:
                    display_name = getattr(bd, "display_name", "")
                    participant = participant_by_name.get(display_name.strip().lower())
                    if participant is None:
                        continue
                    bd_verdict = _coerce_verdict(
                        getattr(bd, "verdict", None),
                        verdict_enum,
                    )
                    bd_fit_reasons = _clean_text_list(getattr(bd, "fit_reasons", []))
                    bd_risk_reasons = _clean_text_list(getattr(bd, "risk_reasons", []))
                    participant_breakdowns.append(
                        (
                            participant,
                            bd_verdict,
                            _decimal_score(getattr(bd, "score", None)),
                            str(getattr(bd, "explanation", "") or "").strip() or None,
                            bd_fit_reasons,
                            bd_risk_reasons,
                        )
                    )

                if not participant_breakdowns:
                    for participant in dining_session.participants:
                        bd_verdict, bd_score, bd_fit, bd_risk = (
                            self._score_item_for_diner(
                                saved_item,
                                participant.preferences,
                            )
                        )
                        participant_breakdowns.append(
                            (
                                participant,
                                bd_verdict,
                                _decimal_score(bd_score),
                                f"Độ phù hợp cá nhân {bd_score:.0f}/100.",
                                bd_fit,
                                bd_risk,
                            )
                        )

                for participant, bd_verdict, _, _, bd_fit, bd_risk in participant_breakdowns:
                    _append_unique(fit_reasons, bd_fit)
                    _append_unique(risk_reasons, bd_risk)
                    if bd_verdict == RecommendationVerdict.RECOMMENDED:
                        _append_unique(suggested_for, [participant.display_name])
                    if bd_verdict in {
                        RecommendationVerdict.AVOID,
                        RecommendationVerdict.CAUTION,
                    }:
                        _append_unique(warning_for, [participant.display_name])
                        _append_unique(warning_reasons, bd_risk)

                if any(
                    breakdown[1] == RecommendationVerdict.AVOID
                    for breakdown in participant_breakdowns
                ):
                    verdict_enum = RecommendationVerdict.AVOID
                elif (
                    verdict_enum != RecommendationVerdict.AVOID
                    and any(
                        breakdown[1] == RecommendationVerdict.CAUTION
                        for breakdown in participant_breakdowns
                    )
                ):
                    verdict_enum = RecommendationVerdict.CAUTION

                if not fit_reasons and why_suitable:
                    fit_reasons = [why_suitable]
                if not risk_reasons and why_not_suitable:
                    risk_reasons = [why_not_suitable]
                if not warning_reasons and verdict_enum in {
                    RecommendationVerdict.AVOID,
                    RecommendationVerdict.CAUTION,
                }:
                    warning_reasons = risk_reasons.copy()
                if not fit_reasons and verdict_enum in {
                    RecommendationVerdict.RECOMMENDED,
                    RecommendationVerdict.OK,
                }:
                    fit_reasons = ["Phù hợp với hồ sơ ăn uống"]
                if not suggested_for and verdict_enum == RecommendationVerdict.RECOMMENDED:
                    suggested_for = [
                        participant.display_name
                        for participant in dining_session.participants
                    ]
                if not why_suitable and fit_reasons:
                    why_suitable = ", ".join(fit_reasons)
                if not why_not_suitable and risk_reasons:
                    why_not_suitable = ", ".join(risk_reasons)
                if not explanation:
                    explanation = (
                        why_not_suitable
                        if verdict_enum
                        in {RecommendationVerdict.AVOID, RecommendationVerdict.CAUTION}
                        else why_suitable
                    )

                rec = FoodItemRecommendation(
                    id=uuid.uuid4(),
                    dining_session_id=dining_session.id,
                    food_item_id=saved_item.id,
                    verdict=verdict_enum,
                    score=_decimal_score(getattr(d_rec, "score", None)),
                    explanation=explanation,
                    why_suitable=why_suitable,
                    why_not_suitable=why_not_suitable,
                    suggested_for=suggested_for,
                    warning_for=warning_for,
                    fit_reasons=fit_reasons,
                    risk_reasons=risk_reasons,
                    warning_reasons=warning_reasons,
                    created_at=self._clock(),
                )
                self._session.add(rec)

                for (
                    participant,
                    bd_verdict,
                    bd_score,
                    bd_explanation,
                    bd_fit_reasons,
                    bd_risk_reasons,
                ) in participant_breakdowns:
                    bd_record = FoodItemRecommendationParticipantBreakdown(
                        id=uuid.uuid4(),
                        food_item_recommendation_id=rec.id,
                        participant_id=participant.id,
                        verdict=bd_verdict,
                        score=bd_score,
                        explanation=bd_explanation or explanation,
                        fit_reasons=bd_fit_reasons or fit_reasons,
                        risk_reasons=bd_risk_reasons or risk_reasons,
                        created_at=self._clock(),
                    )
                    self._session.add(bd_record)

            self._session.commit()
            return

        # Fetch host profile (fallback to local rule-based recommendations)
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

        for item in food_items:
            group_verdict = RecommendationVerdict.RECOMMENDED
            group_score_sum = 0.0
            total_diners = 0

            fit_reasons_all = []
            risk_reasons_all = []
            suggested_for = []
            warning_for = []

            # Score host
            if host_profile is not None:
                host_verdict, host_score, host_fit, host_risk = self._score_item_for_diner(item, host_profile.preferences)
                group_score_sum += host_score
                total_diners += 1

                fit_reasons_all.extend(host_fit)
                risk_reasons_all.extend(host_risk)
                if host_verdict == RecommendationVerdict.RECOMMENDED:
                    suggested_for.append(host_profile.display_name or "Host")
                elif host_verdict == RecommendationVerdict.AVOID:
                    warning_for.append(host_profile.display_name or "Host")
                    group_verdict = RecommendationVerdict.AVOID
                elif host_verdict == RecommendationVerdict.CAUTION:
                    if group_verdict != RecommendationVerdict.AVOID:
                        group_verdict = RecommendationVerdict.CAUTION

            # Score each participant and save their breakdown
            breakdowns = []
            for p in dining_session.participants:
                p_verdict, p_score, p_fit, p_risk = self._score_item_for_diner(item, p.preferences)
                group_score_sum += p_score
                total_diners += 1

                fit_reasons_all.extend(p_fit)
                risk_reasons_all.extend(p_risk)
                if p_verdict == RecommendationVerdict.RECOMMENDED:
                    suggested_for.append(p.display_name)
                elif p_verdict == RecommendationVerdict.AVOID:
                    warning_for.append(p.display_name)
                    group_verdict = RecommendationVerdict.AVOID
                elif p_verdict == RecommendationVerdict.CAUTION:
                    if group_verdict != RecommendationVerdict.AVOID:
                        group_verdict = RecommendationVerdict.CAUTION

                breakdowns.append(
                    FoodItemRecommendationParticipantBreakdown(
                        id=uuid.uuid4(),
                        participant_id=p.id,
                        verdict=p_verdict,
                        score=Decimal(str(round(p_score, 2))),
                        explanation=f"Độ phù hợp cá nhân {p_score:.0f}/100.",
                        fit_reasons=p_fit,
                        risk_reasons=p_risk,
                        created_at=self._clock(),
                    )
                )

            final_score = group_score_sum / total_diners if total_diners > 0 else 100.0
            if total_diners > 0:
                if group_verdict != RecommendationVerdict.AVOID:
                    if final_score >= 75.0:
                        group_verdict = RecommendationVerdict.RECOMMENDED
                    elif final_score >= 40.0:
                        group_verdict = RecommendationVerdict.OK
                    else:
                        group_verdict = RecommendationVerdict.CAUTION
            else:
                group_verdict = RecommendationVerdict.RECOMMENDED

            unique_fit_reasons = list(sorted(set(fit_reasons_all)))
            unique_risk_reasons = list(sorted(set(risk_reasons_all)))
            if not unique_fit_reasons and group_verdict in {
                RecommendationVerdict.RECOMMENDED,
                RecommendationVerdict.OK,
            }:
                unique_fit_reasons = ["Phù hợp với hồ sơ ăn uống"]

            rec = FoodItemRecommendation(
                id=uuid.uuid4(),
                dining_session_id=dining_session.id,
                food_item_id=item.id,
                verdict=group_verdict,
                score=Decimal(str(round(final_score, 2))),
                explanation=f"Độ phù hợp nhóm {final_score:.0f}/100.",
                why_suitable=", ".join(unique_fit_reasons) if unique_fit_reasons else None,
                why_not_suitable=", ".join(unique_risk_reasons) if unique_risk_reasons else None,
                suggested_for=suggested_for,
                warning_for=warning_for,
                fit_reasons=unique_fit_reasons,
                risk_reasons=unique_risk_reasons,
                warning_reasons=unique_risk_reasons if group_verdict in {RecommendationVerdict.AVOID, RecommendationVerdict.CAUTION} else [],
                created_at=self._clock(),
            )
            self._session.add(rec)

            for bd in breakdowns:
                bd.food_item_recommendation_id = rec.id
                if not bd.fit_reasons and bd.verdict in {
                    RecommendationVerdict.RECOMMENDED,
                    RecommendationVerdict.OK,
                }:
                    bd.fit_reasons = unique_fit_reasons
                if not bd.risk_reasons and bd.verdict in {
                    RecommendationVerdict.AVOID,
                    RecommendationVerdict.CAUTION,
                }:
                    bd.risk_reasons = unique_risk_reasons
                self._session.add(bd)

        self._session.commit()

    @staticmethod
    def _score_item_for_diner(
        food_item: FoodItem,
        preferences: list[object],
    ) -> tuple[RecommendationVerdict, float, list[str], list[str]]:
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
