from src.picker.colors import RGB, hex_to_rgb, rgb_to_hex


def test_hex_to_rgb_six_digit():
    assert hex_to_rgb("#1a0a0a") == RGB(0x1a, 0x0a, 0x0a)


def test_hex_to_rgb_three_digit_expands():
    assert hex_to_rgb("#f00") == RGB(255, 0, 0)


def test_hex_to_rgb_no_leading_hash():
    assert hex_to_rgb("00ff00") == RGB(0, 255, 0)


def test_hex_to_rgb_uppercase():
    assert hex_to_rgb("#FFAA88") == RGB(255, 170, 136)


def test_rgb_to_hex_pads_zeros():
    assert rgb_to_hex(RGB(1, 2, 3)) == "#010203"


def test_rgb_to_hex_full_range():
    assert rgb_to_hex(RGB(255, 0, 128)) == "#ff0080"


def test_rgb_hex_roundtrip():
    for r in (0, 17, 128, 255):
        for g in (0, 17, 128, 255):
            for b in (0, 17, 128, 255):
                rgb = RGB(r, g, b)
                assert hex_to_rgb(rgb_to_hex(rgb)) == rgb


from src.picker.colors import HSL, rgb_to_hsl, hsl_to_rgb


def test_rgb_to_hsl_black():
    h = rgb_to_hsl(RGB(0, 0, 0))
    assert h.l == 0 and h.s == 0


def test_rgb_to_hsl_white():
    h = rgb_to_hsl(RGB(255, 255, 255))
    assert h.l == 100 and h.s == 0


def test_rgb_to_hsl_pure_red():
    h = rgb_to_hsl(RGB(255, 0, 0))
    assert round(h.h) == 0 and round(h.s) == 100 and round(h.l) == 50


def test_hsl_roundtrip_primaries():
    for rgb in (RGB(255, 0, 0), RGB(0, 255, 0), RGB(0, 0, 255),
                RGB(255, 255, 0), RGB(0, 255, 255), RGB(255, 0, 255)):
        back = hsl_to_rgb(rgb_to_hsl(rgb))
        assert back == rgb


from src.picker.colors import OKLCH, rgb_to_oklch, oklch_to_rgb


def test_rgb_to_oklch_black():
    o = rgb_to_oklch(RGB(0, 0, 0))
    assert o.l == 0 and o.c == 0


def test_rgb_to_oklch_white():
    o = rgb_to_oklch(RGB(255, 255, 255))
    assert o.l == 100 and o.c < 5  # near-zero chroma


def test_oklch_roundtrip_tolerance():
    # Prototype-grade tolerance: each channel within 8 of original
    # (Due to rounding integers: L(0-100), C(0-400), H(0-360))
    for rgb in (RGB(64, 128, 192), RGB(200, 50, 100), RGB(20, 200, 80)):
        back = oklch_to_rgb(rgb_to_oklch(rgb))
        assert abs(back.r - rgb.r) <= 8
        assert abs(back.g - rgb.g) <= 8
        assert abs(back.b - rgb.b) <= 8


from src.picker.colors import Lab, rgb_to_lab, lab_to_rgb


def test_rgb_to_lab_black():
    lab = rgb_to_lab(RGB(0, 0, 0))
    assert lab.l == 0


def test_rgb_to_lab_white():
    lab = rgb_to_lab(RGB(255, 255, 255))
    assert lab.l == 100 and abs(lab.a) <= 1 and abs(lab.b) <= 1


def test_lab_roundtrip_tolerance():
    for rgb in (RGB(64, 128, 192), RGB(200, 50, 100), RGB(20, 200, 80)):
        back = lab_to_rgb(rgb_to_lab(rgb))
        assert abs(back.r - rgb.r) <= 2
        assert abs(back.g - rgb.g) <= 2
        assert abs(back.b - rgb.b) <= 2


from src.picker.colors import nearest_name


def test_nearest_name_exact_match():
    names = {"red": "#ff0000", "green": "#00ff00", "blue": "#0000ff"}
    assert nearest_name(RGB(255, 0, 0), names) == "red"


def test_nearest_name_close_match():
    names = {"red": "#ff0000", "green": "#00ff00", "blue": "#0000ff"}
    assert nearest_name(RGB(250, 5, 5), names) == "red"


def test_nearest_name_empty_returns_empty_string():
    assert nearest_name(RGB(128, 128, 128), {}) == ""
