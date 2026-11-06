import re
from typing import Any


THREAT_LEVELS = {"low", "medium", "high"}
_SEVERITY = {"low": 1, "medium": 2, "high": 3}

_KEYWORD_LEVELS = {
    "high": (
        "kill you",
        "kill me",
        "going to kill",
        "i will kill",
        "murder",
        "rape",
        "sexual assault",
        "kidnap",
        "strangle",
        "choke",
        "gun",
        "knife",
        "stab",
    ),
    "medium": (
        "threaten",
        "threatened",
        "stalk",
        "follow me",
        "blackmail",
        "coerce",
        "force me",
        "forced me",
        "beat me",
        "hit me",
        "assault",
        "harass",
    ),
    "low": (
        "insult",
        "unwanted message",
        "inappropriate comment",
        "verbal abuse",
    ),
}


def _keyword_matches(description: str) -> dict[str, list[str]]:
    normalized_description = description.casefold()
    matches = {}

    for level, keywords in _KEYWORD_LEVELS.items():
        found = [
            keyword
            for keyword in keywords
            if re.search(
                rf"(?<!\w){re.escape(keyword)}(?!\w)",
                normalized_description,
            )
        ]
        if found:
            matches[level] = found

    return matches


def assess_incident(
    user_selected_level: str | None = None,
    indicators: dict[str, Any] | None = None,
    description: str = "",
) -> dict[str, Any]:
    """
    Produce a preliminary threat assessment.

    This is a rules-based aid, not a validated prediction model.

    Automated rules may raise, but never lower, the survivor-selected
    level. Missing or ambiguous information is not proof that the
    survivor is safe.
    """

    indicators = indicators or {}

    # Validate the survivor-selected level.
    if user_selected_level:
        selected_level = user_selected_level.strip().lower()

        if selected_level not in THREAT_LEVELS:
            raise ValueError(
                "Threat level must be low, medium, or high."
            )

    else:
        selected_level = None

    keyword_matches = _keyword_matches(description)
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

    indicator_level = None
    if immediate_danger or serious_threat:
        indicator_level = "high"
    elif credible_threat or coercion or repeated_harassment:
        indicator_level = "medium"
    elif inappropriate_behavior:
        indicator_level = "low"

    keyword_level = max(
        keyword_matches,
        key=lambda level: _SEVERITY[level],
        default=None,
    )
    automated_level = max(
        (level for level in (indicator_level, keyword_level) if level),
        key=lambda level: _SEVERITY[level],
        default=None,
    )

    if selected_level and (
        automated_level is None
        or _SEVERITY[selected_level] >= _SEVERITY[automated_level]
    ):
        return {
            "level": selected_level,
            "suggested_level": automated_level,
            "source": "user_selected",
            "reason": (
                "The survivor selected this threat level. "
                "Automated keyword and indicator checks did not "
                "identify a higher level."
            ),
            "needs_review": False,
            "keyword_matches": keyword_matches,
        }

    if automated_level:
        reason = (
            "Keyword or incident-indicator checks identified a "
            "preliminary threat level. Human review is required."
        )
        if selected_level:
            reason += (
                " The automated result raised the survivor-selected "
                "level to avoid understating the reported risk."
            )
        return {
            "level": automated_level,
            "suggested_level": automated_level,
            "source": "rules",
            "reason": reason,
            "needs_review": True,
            "keyword_matches": keyword_matches,
        }

    if selected_level:
        return {
            "level": selected_level,
            "suggested_level": None,
            "source": "user_selected",
            "reason": "The survivor selected this threat level.",
            "needs_review": False,
            "keyword_matches": keyword_matches,
        }

    # Unknown information must not be silently classified as safe.
    return {
        "level": None,
        "suggested_level": None,
        "source": "insufficient_information",
        "reason": (
            "There is not enough information to suggest a "
            "classification. The survivor can select a level or "
            "provide more information."
        ),
        "needs_review": True,
        "keyword_matches": keyword_matches,
    }