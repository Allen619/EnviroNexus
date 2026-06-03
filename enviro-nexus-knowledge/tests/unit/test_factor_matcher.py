from app.core.factor_matcher import AliasCandidate, choose_best_match


def candidates() -> list[AliasCandidate]:
    return [
        AliasCandidate(
            alias="pH 值",
            normalized_alias="ph",
            factor="pH 值",
            card_id="water_ph_hj1147_2020",
            priority=10,
            enabled=True,
        ),
        AliasCandidate(
            alias="酸碱度",
            normalized_alias="酸碱度",
            factor="pH 值",
            card_id="water_ph_hj1147_2020",
            priority=30,
            enabled=True,
        ),
        AliasCandidate(
            alias="CODMn",
            normalized_alias="codmn",
            factor="高锰酸盐指数",
            card_id="water_permanganate_index_hj1445_2026",
            priority=10,
            enabled=True,
        ),
    ]


def test_ph_matches_ph_card():
    result = choose_best_match("ph", candidates())

    assert result is not None
    assert result.card_id == "water_ph_hj1147_2020"
    assert result.confidence == 1.0


def test_acidity_matches_ph_card():
    result = choose_best_match("水样酸碱度", candidates())

    assert result is not None
    assert result.card_id == "water_ph_hj1147_2020"
    assert result.matched_alias == "酸碱度"


def test_cod_does_not_match_ph_card():
    assert choose_best_match("cod", candidates()) is None


def test_codmn_matches_permanganate_index_card():
    result = choose_best_match("codmn", candidates())

    assert result is not None
    assert result.card_id == "water_permanganate_index_hj1445_2026"
    assert result.factor == "高锰酸盐指数"
    assert result.confidence == 1.0


def test_ascii_abbreviation_does_not_use_reverse_contains_match():
    result = choose_best_match(
        "cod",
        [
            AliasCandidate(
                alias="CODMn",
                normalized_alias="codmn",
                factor="高锰酸盐指数",
                card_id="water_permanganate_index_hj1445_2026",
                priority=10,
                enabled=True,
            )
        ],
    )

    assert result is None
