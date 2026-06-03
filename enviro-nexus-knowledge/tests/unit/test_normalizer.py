from app.core.normalizer import normalize_alias, normalize_query


def test_normalize_query_ph_question():
    assert normalize_query("pH 怎么测？") == "ph"


def test_normalize_query_ph_value_method():
    assert normalize_query("PH值检测方法") == "ph"


def test_normalize_query_cod_question():
    assert normalize_query("COD 怎么测？") == "cod"


def test_normalize_query_keeps_acidity_keyword():
    assert "酸碱度" in normalize_query("水样酸碱度用什么标准？")


def test_normalize_alias_ph_value():
    assert normalize_alias("pH值") == "ph"
