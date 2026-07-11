"""Dining-session workflow service."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DiningSessionInviteBundle:
    dining_session: DiningSession
    invite: DiningSessionInvite
    invite_token: str


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
        from src.modules.menu.models import Menu, FoodItem

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

                try:
                    verdict_str = getattr(d_rec, "verdict", "RECOMMENDED")
                    verdict_enum = RecommendationVerdict(verdict_str.upper())
                except Exception:
                    verdict_enum = RecommendationVerdict.RECOMMENDED

                rec = FoodItemRecommendation(
                    id=uuid.uuid4(),
                    dining_session_id=dining_session.id,
                    food_item_id=saved_item.id,
                    verdict=verdict_enum,
                    score=Decimal(str(round(getattr(d_rec, "score", 100.0) or 100.0, 2))),
                    explanation=getattr(d_rec, "explanation", None),
                    why_suitable=getattr(d_rec, "why_suitable", None),
                    why_not_suitable=getattr(d_rec, "why_not_suitable", None),
                    suggested_for=getattr(d_rec, "suggested_for", []),
                    warning_for=getattr(d_rec, "warning_for", []),
                    fit_reasons=getattr(d_rec, "fit_reasons", []),
                    risk_reasons=getattr(d_rec, "risk_reasons", []),
                    warning_reasons=getattr(d_rec, "warning_reasons", []),
                    created_at=self._clock(),
                )
                self._session.add(rec)

                d_breakdowns = getattr(d_item, "participant_breakdowns", []) or []
                for bd in d_breakdowns:
                    display_name = getattr(bd, "display_name", "")
                    p = participant_by_name.get(display_name.strip().lower())
                    if not p:
                        continue
                    try:
                        bd_verdict_str = getattr(bd, "verdict", "RECOMMENDED")
                        bd_verdict = RecommendationVerdict(bd_verdict_str.upper())
                    except Exception:
                        bd_verdict = RecommendationVerdict.RECOMMENDED

                    bd_record = FoodItemRecommendationParticipantBreakdown(
                        id=uuid.uuid4(),
                        food_item_recommendation_id=rec.id,
                        participant_id=p.id,
                        verdict=bd_verdict,
                        score=Decimal(str(round(getattr(bd, "score", 100.0) or 100.0, 2))),
                        explanation=getattr(bd, "explanation", None),
                        fit_reasons=getattr(bd, "fit_reasons", []),
                        risk_reasons=getattr(bd, "risk_reasons", []),
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
                    FoodProfile.is_default == True,
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

            rec = FoodItemRecommendation(
                id=uuid.uuid4(),
                dining_session_id=dining_session.id,
                food_item_id=item.id,
                verdict=group_verdict,
                score=Decimal(str(round(final_score, 2))),
                explanation=f"Độ phù hợp nhóm {final_score:.0f}/100.",
                why_suitable=", ".join(sorted(set(fit_reasons_all))) if fit_reasons_all else None,
                why_not_suitable=", ".join(sorted(set(risk_reasons_all))) if risk_reasons_all else None,
                suggested_for=suggested_for,
                warning_for=warning_for,
                fit_reasons=list(sorted(set(fit_reasons_all))),
                risk_reasons=list(sorted(set(risk_reasons_all))),
                warning_reasons=list(sorted(set(risk_reasons_all))) if group_verdict in {RecommendationVerdict.AVOID, RecommendationVerdict.CAUTION} else [],
                created_at=self._clock(),
            )
            self._session.add(rec)

            for bd in breakdowns:
                bd.food_item_recommendation_id = rec.id
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

        def matches(code: str) -> bool:
            c = code.strip().lower()
            if c in [a.lower() for a in food_item.allergens]:
                return True
            if c in [t.lower() for t in food_item.dietary_tags]:
                return True
            name_search = f"{food_item.original_name} {food_item.translated_name or ''} {food_item.original_description or ''} {food_item.translated_description or ''}".lower()
            return c in name_search

        for pref in preferences:
            code = getattr(pref, "code", "")
            pref_type = getattr(pref, "preference_type", "")
            pref_type = pref_type.value if hasattr(pref_type, "value") else str(pref_type)

            if pref_type == "ALLERGY":
                if matches(code):
                    score = 0.0
                    verdict = RecommendationVerdict.AVOID
                    risk_reasons.append(f"Dị ứng với {code}")

            elif pref_type == "DIETARY_RULE":
                rule = code.strip().lower()
                violated = False
                if rule == "vegan":
                    if "vegan" not in [t.lower() for t in food_item.dietary_tags]:
                        violated = True
                elif rule == "vegetarian":
                    tags = [t.lower() for t in food_item.dietary_tags]
                    if "vegetarian" not in tags and "vegan" not in tags:
                        violated = True
                elif rule in {"no_pork", "contains_pork"}:
                    if "contains_pork" in [t.lower() for t in food_item.dietary_tags]:
                        violated = True
                elif rule in {"no_alcohol", "contains_alcohol"}:
                    if "contains_alcohol" in [t.lower() for t in food_item.dietary_tags]:
                        violated = True
                elif matches(code):
                    if rule in {"no_beef", "contains_beef"} and "contains_beef" in [t.lower() for t in food_item.dietary_tags]:
                        violated = True
                    elif rule in {"no_seafood", "contains_seafood"} and ("contains_seafood" in [t.lower() for t in food_item.dietary_tags] or "seafood" in [a.lower() for a in food_item.allergens]):
                        violated = True

                if violated:
                    score = 0.0
                    verdict = RecommendationVerdict.AVOID
                    risk_reasons.append(f"Kiêng {code}")

            elif pref_type == "AVOID":
                if matches(code):
                    score = max(0.0, score - 50.0)
                    if verdict != RecommendationVerdict.AVOID:
                        verdict = RecommendationVerdict.CAUTION
                    risk_reasons.append(f"Hạn chế {code}")

            elif pref_type == "DISLIKE":
                if matches(code):
                    score = max(0.0, score - 30.0)
                    if verdict not in {RecommendationVerdict.AVOID, RecommendationVerdict.CAUTION}:
                        verdict = RecommendationVerdict.OK
                    risk_reasons.append(f"Không thích {code}")

            elif pref_type == "LIKE":
                if matches(code):
                    score = min(100.0, score + 15.0)
                    fit_reasons.append(f"Thích {code}")

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
