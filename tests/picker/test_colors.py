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
