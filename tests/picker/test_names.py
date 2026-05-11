from src.picker.names import NAMED_COLORS


def test_named_colors_nonempty():
    assert len(NAMED_COLORS) > 100


def test_named_colors_known_entries():
    assert NAMED_COLORS["red"] == "#ff0000"
    assert NAMED_COLORS["midnightblue"] == "#191970"
    assert NAMED_COLORS["aliceblue"] == "#f0f8ff"


def test_named_colors_all_valid_hex():
    import re
    for name, hex_val in NAMED_COLORS.items():
        assert re.match(r"^#[0-9a-f]{6}$", hex_val), f"{name}={hex_val}"
