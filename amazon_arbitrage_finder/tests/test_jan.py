from amazon_arbitrage_finder.jan import extract_jan, is_valid_ean13, normalize_jan


def test_checksum():
    assert is_valid_ean13("4901234567894")
    assert not is_valid_ean13("4901234567895")
    assert not is_valid_ean13("490123456789")


def test_normalize_handles_fullwidth_hyphen_float_and_upc():
    assert normalize_jan("４９０１２３４５６７８９４") == "4901234567894"
    assert normalize_jan("4901-2345-67894") == "4901234567894"
    assert normalize_jan("4901234567894.0") == "4901234567894"
    assert normalize_jan("036000291452") == "0036000291452"
    assert normalize_jan("4901234567895") is None
    assert normalize_jan(None) is None


def test_extract_prefers_labelled_code():
    text = "型番 ABC-123 品番4912345678904 JANコード：4901234567894"
    assert extract_jan(text) == "4901234567894"


def test_extract_single_unlabelled_code():
    assert extract_jan("新品 4901234567894 送料無料") == "4901234567894"


def test_extract_refuses_ambiguous_or_invalid():
    assert extract_jan("4901234567894 と 4912345678904 のセット") is None
    assert extract_jan("4901234567895") is None
    assert extract_jan(None, "") is None
