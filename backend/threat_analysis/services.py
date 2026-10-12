from typing import Any


THREAT_LEVELS = {"low", "medium", "high"}


def assess_incident(
    user_selected_level: str | None = None,
    indicators: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Produce a preliminary threat assessment.

    This is a rules-based aid, not a validated prediction model.

    A survivor-selected level takes precedence over the automated
    suggestion. Missing or ambiguous information must not be
    interpreted as proof that the survivor is safe.
    """

    indicators = indicators or {}

    # Validate the survivor-selected level.
    if user_selected_level:
        selected_level = user_selected_level.strip().lower()

        if selected_level not in THREAT_LEVELS:
            raise ValueError(
                "Threat level must be low, medium, or high."
            )

        return {
            "level": selected_level,
            "source": "user_selected",
            "reason": "The survivor selected this threat level.",
            "needs_review": False,
        }

    # Only explicit Boolean True values activate these rules.
    immediate_danger = (
        indicators.get("immediate_danger") is True
    )

    serious_threat = (
        indicators.get("serious_threat") is True
    )

    credible_threat = (
        indicators.get("credible_threat") is True
    )

    coercion = indicators.get("coercion") is True

    repeated_harassment = (
        indicators.get("repeated_harassment") is True
    )

    inappropriate_behavior = (
        indicators.get("inappropriate_behavior") is True
    )

    # A reported immediate danger or serious threat receives
    # a high-priority preliminary classification.
    if immediate_danger or serious_threat:
        return {
            "level": "high",
            "source": "rules",
            "reason": (
                "The report includes an immediate-danger "
                "indicator or a serious-threat indicator."
            ),
            "needs_review": True,
        }

    # Concerning threats, coercion, or repeated harassment.
    if (
        credible_threat
        or coercion
        or repeated_harassment
    ):
        return {
            "level": "medium",
            "source": "rules",
            "reason": (
                "The report includes an indicator of concerning "
                "harassment, coercion, or threats."
            ),
            "needs_review": True,
        }

    # A reported lower-severity incident.
    if inappropriate_behavior:
        return {
            "level": "low",
            "source": "rules",
            "reason": (
                "The report includes inappropriate behaviour "
                "or lower-severity harassment."
            ),
            "needs_review": True,
        }

    # Unknown information must not be silently classified as safe.
    return {
        "level": None,
        "source": "insufficient_information",
        "reason": (
            "There is not enough information to suggest a "
            "classification. The survivor can select a level "
            "or provide more information."
        ),
        "needs_review": True,
    }