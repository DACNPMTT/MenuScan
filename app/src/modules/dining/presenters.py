"""One place that answers "what is this dish's verdict for whoever is looking".

There used to be three copies of this: `MenuService.get_menu`, `MenuService.
list_menu_items` (byte-for-byte identical), and a third, differently-written one
in the scan-result endpoint. They drifted — two looked the session up by
`menu_id`, one by `scan_session_id` — and the menu ones lazily walked
`recommendation.participant_breakdowns` and then `breakdown.participant` per dish,
so rendering a 40-dish menu fired well over a hundred queries.

Two ways a dish gets a verdict:

- **Group menu** (a real dining session a host created and people joined): the
  verdicts were scored and persisted when the menu was enriched. Read them.
- **Personal menu** (an ordinary scan, no session): score live against the diner's
  current food profile. Nothing is persisted — one reader does not justify write
  amplification, and a stored copy of their profile would go stale the moment they
  edited it.

Either way, a diner who has declared no preferences gets **no verdict at all**,
not a fabricated one.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.modules.dining.models import (
    DiningSession,
    FoodItemRecommendation,
    FoodItemRecommendationParticipantBreakdown,
)
from src.modules.dining.schemas import (
    ParticipantBreakdownResponse,
    RecommendationResponse,
)
from src.modules.dining.service import DiningSessionService
from src.modules.identity.models import FoodProfile
from src.modules.menu.models import FoodItem


@dataclass(frozen=True, slots=True)
class RecommendationView:
    """Resolves every dish of one menu, with all rows it needs already loaded."""

    _persisted: dict[uuid.UUID, RecommendationResponse]
    _profile: FoodProfile | None

    @classmethod
    def empty(cls) -> RecommendationView:
        return cls(_persisted={}, _profile=None)

    def for_item(self, item: FoodItem) -> RecommendationResponse | None:
        if self._persisted:
            return self._persisted.get(item.id)
        if self._profile is None:
            return None

        scored = DiningSessionService._score_item_for_diner(
            item,
            list(self._profile.preferences),
        )
        if scored is None:
            # The diner has told us nothing. Say nothing.
            return None

        verdict, score, fit, risk = scored
        return _personal_response(
            display_name=self._profile.display_name or "Bạn",
            verdict=verdict.value,
            score=score,
            fit=fit,
            risk=risk,
        )


def load_recommendation_view(
    session: Session,
    *,
    menu_id: uuid.UUID,
    user_id: uuid.UUID | None,
) -> RecommendationView:
    dining_session = session.scalars(
        select(DiningSession).where(
            DiningSession.menu_id == menu_id,
            DiningSession.deleted_at.is_(None),
        )
    ).first()

    if dining_session is not None:
        recommendations = session.scalars(
            select(FoodItemRecommendation)
            .where(FoodItemRecommendation.dining_session_id == dining_session.id)
            .options(
                selectinload(
                    FoodItemRecommendation.participant_breakdowns
                ).selectinload(FoodItemRecommendationParticipantBreakdown.participant)
            )
        ).all()
        return RecommendationView(
            _persisted={
                recommendation.food_item_id: _persisted_response(recommendation)
                for recommendation in recommendations
            },
            _profile=None,
        )

    if user_id is None:
        return RecommendationView.empty()

    profile = session.scalars(
        select(FoodProfile)
        .where(
            FoodProfile.user_id == user_id,
            FoodProfile.is_default,
            FoodProfile.deleted_at.is_(None),
        )
        .options(selectinload(FoodProfile.preferences))
    ).first()
    return RecommendationView(_persisted={}, _profile=profile)


def _persisted_response(
    recommendation: FoodItemRecommendation,
) -> RecommendationResponse:
    return RecommendationResponse(
        verdict=recommendation.verdict.value,
        score=float(recommendation.score) if recommendation.score is not None else None,
        explanation=recommendation.explanation,
        why_suitable=recommendation.why_suitable,
        why_not_suitable=recommendation.why_not_suitable,
        suggested_for=recommendation.suggested_for or [],
        warning_for=recommendation.warning_for or [],
        fit_reasons=recommendation.fit_reasons or [],
        risk_reasons=recommendation.risk_reasons or [],
        warning_reasons=recommendation.warning_reasons or [],
        participant_breakdowns=[
            ParticipantBreakdownResponse(
                display_name=getattr(
                    breakdown.participant, "display_name", "Thành viên"
                ),
                verdict=breakdown.verdict.value,
                score=float(breakdown.score) if breakdown.score is not None else None,
                explanation=breakdown.explanation,
                fit_reasons=breakdown.fit_reasons or [],
                risk_reasons=breakdown.risk_reasons or [],
            )
            for breakdown in recommendation.participant_breakdowns
        ],
    )


def _personal_response(
    *,
    display_name: str,
    verdict: str,
    score: float,
    fit: list[str],
    risk: list[str],
) -> RecommendationResponse:
    explanation = f"Độ phù hợp cá nhân {score:.0f}/100."
    return RecommendationResponse(
        verdict=verdict,
        score=score,
        explanation=explanation,
        why_suitable=", ".join(fit) if fit else None,
        why_not_suitable=", ".join(risk) if risk else None,
        suggested_for=[display_name] if verdict == "RECOMMENDED" else [],
        warning_for=[display_name] if verdict == "AVOID" else [],
        fit_reasons=fit,
        risk_reasons=risk,
        warning_reasons=risk if verdict in {"AVOID", "CAUTION"} else [],
        participant_breakdowns=[
            ParticipantBreakdownResponse(
                display_name=display_name,
                verdict=verdict,
                score=score,
                explanation=explanation,
                fit_reasons=fit,
                risk_reasons=risk,
            )
        ],
    )
