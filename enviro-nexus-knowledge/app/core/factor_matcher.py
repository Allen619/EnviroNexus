from dataclasses import dataclass


@dataclass(frozen=True)
class AliasCandidate:
    alias: str
    normalized_alias: str
    factor: str
    card_id: str
    priority: int
    enabled: bool = True


@dataclass(frozen=True)
class MatchResult:
    alias: str
    matched_alias: str
    factor: str
    card_id: str
    confidence: float
    priority: int


def choose_best_match(
    normalized_query: str,
    candidates: list[AliasCandidate],
) -> MatchResult | None:
    matches: list[MatchResult] = []
    query = normalized_query.strip()
    if not query:
        return None

    for candidate in candidates:
        if not candidate.enabled:
            continue

        alias = candidate.normalized_alias.strip()
        if not alias:
            continue

        confidence = _match_confidence(query, alias)
        if confidence is None:
            continue

        matches.append(
            MatchResult(
                alias=candidate.alias,
                matched_alias=candidate.normalized_alias,
                factor=candidate.factor,
                card_id=candidate.card_id,
                confidence=confidence,
                priority=candidate.priority,
            )
        )

    if not matches:
        return None

    return sorted(matches, key=lambda item: (-item.confidence, item.priority))[0]


def _match_confidence(query: str, alias: str) -> float | None:
    if query == alias:
        return 1.0

    if _is_ascii_alnum(query) and _is_ascii_alnum(alias):
        return None

    if alias in query:
        return 0.9

    if query in alias:
        return 0.8

    return None


def _is_ascii_alnum(value: str) -> bool:
    return value.isascii() and value.isalnum()
