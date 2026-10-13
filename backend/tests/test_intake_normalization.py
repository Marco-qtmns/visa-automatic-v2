from backend.app.services.address_normalization import normalize_address
from backend.app.services.country_normalization import normalize_country, split_country_values


def test_portuguese_nationality_and_alpha2_normalize_to_alpha3():
    assert normalize_country("Brasileira").code == "BRA"
    assert normalize_country("brasileiro").code == "BRA"
    assert normalize_country("BR").code == "BRA"
    assert normalize_country("Canadense").code == "CAN"
    assert normalize_country("Alemanha").code == "DEU"


def test_multiple_citizenships_remain_separate_source_values():
    assert split_country_values("Brasileira; Canadense / Alemã") == [
        "Brasileira", "Canadense", "Alemã"
    ]


def test_unknown_country_is_explicitly_unresolved():
    result = normalize_country("Unknownland")
    assert result.code is None
    assert result.issue == "unknown_or_ambiguous_country"


def test_brazilian_address_preserves_raw_and_parses_only_certain_components():
    result = normalize_address("Rua das Flores, 123, Apto 4, Centro, 01310-100")
    assert result.raw == "Rua das Flores, 123, Apto 4, Centro, 01310-100"
    assert result.postal_code == "01310-100"
    assert result.street_name == "Rua das Flores"
    assert result.street_number == "123"
    assert result.unit == "4"
    assert result.unresolved_text == "Centro"
    assert result.review_status == "needs_review"


def test_addr_01_to_03_supported_and_ambiguous_formats_preserve_source():
    full = normalize_address("Rua das Flores, 25, Centro, Brasília - DF, 70000-000")
    assert (full.street_name, full.street_number, full.city, full.province_or_state) == (
        "Rua das Flores", "25", "Brasília", "DF"
    )
    assert full.postal_code == "70000-000" and full.raw.startswith("Rua das Flores")
    for source, street, number, unit in (
        ("Rua das Flores 25", "Rua das Flores", "25", None),
        ("25 Rua das Flores", "Rua das Flores", "25", None),
        ("Av. Paulista, 1578", "Av. Paulista", "1578", None),
        ("Rua das Flores, 25, Apto 302", "Rua das Flores", "25", "302"),
    ):
        parsed = normalize_address(source)
        assert (parsed.street_name, parsed.street_number, parsed.unit, parsed.raw) == (
            street, number, unit, source
        )
    ambiguous = normalize_address("Centro, Brasília, próximo ao shopping")
    assert ambiguous.street_name is None and ambiguous.street_number is None
    assert ambiguous.unresolved_text == "Centro, Brasília, próximo ao shopping"
