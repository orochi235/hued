import struct
import zlib

import pytest

from huedmap import color


def test_distance_is_zero_for_the_same_color_and_large_for_opposites():
    assert color.distance(color.lab("#336699"), color.lab("#336699")) == 0
    assert color.distance(color.lab("#000000"), color.lab("#ffffff")) == pytest.approx(1.0, abs=0.01)


def test_place_reports_hue_lightness_and_gray():
    red = color.place("#ff0000")
    assert red["h"] == pytest.approx(29.2, abs=0.5)
    assert red["l"] == pytest.approx(0.628, abs=0.005)
    assert not red["gray"]
    assert color.place("#222222")["gray"]


def test_place_marks_light_backgrounds():
    assert color.place("#ffffc4")["light"]
    assert not color.place("#320053")["light"]


def test_from_lch_lands_on_the_requested_hue_and_lightness():
    for h in (10, 100, 200, 300):
        for l in (0.3, 0.5, 0.8):
            got = color.place(color.from_lch(l, h, 0.97))
            assert got["l"] == pytest.approx(l, abs=0.02)
            assert got["h"] == pytest.approx(h, abs=4)


def test_from_lch_with_no_chroma_is_gray():
    hexv = color.from_lch(0.5, 123, 0)
    assert hexv[1:3] == hexv[3:5] == hexv[5:7]


TAKEN = ["#ff0000", "#00ff00", "#0000ff", "#222222", "#ffffc4"]


def test_gaps_returns_the_count_asked_for_and_no_duplicates():
    picks = color.gaps(TAKEN, "any", count=6)
    assert len(picks) == len(set(picks)) == 6


def test_gaps_stay_away_from_taken_colors_and_each_other():
    picks = color.gaps(TAKEN, "any", count=6)
    everything = [color.lab(h) for h in TAKEN + picks]
    for i, pick in enumerate(picks):
        others = everything[:len(TAKEN) + i]
        assert min(color.distance(color.lab(pick), o) for o in others) > color.CLOSE


def test_gaps_pick_the_farthest_candidate_first():
    first = color.gaps(TAKEN, "any", count=1)[0]
    taken = [color.lab(h) for h in TAKEN]
    best = min(color.distance(color.lab(first), t) for t in taken)
    for candidate in ("#ff00ff", "#00ffff", "#ff8800", "#8800ff", "#008888"):
        assert min(color.distance(color.lab(candidate), t) for t in taken) <= best + 1e-9


@pytest.mark.parametrize("band", ["any", "dark", "light"])
def test_gaps_respect_the_lightness_limit_and_skip_grays(band):
    lo, hi = color.BANDS[band]
    for pick in color.gaps(TAKEN, band, count=6):
        placed = color.place(pick)
        assert lo <= placed["l"] <= hi
        assert not placed["gray"]


def test_gaps_work_with_nothing_taken():
    assert len(color.gaps([], "any", count=6)) == 6


def test_near_gives_five_tagged_swatches_at_the_clicked_spot():
    swatches = color.near(200, 0.5, gray=False)
    assert [s["tag"] for s in swatches] == ["vivid", "medium", "muted", "lighter", "darker"]
    assert swatches[0]["l"] == pytest.approx(0.5, abs=0.02)
    assert swatches[3]["l"] > swatches[0]["l"] > swatches[4]["l"]


def test_near_in_the_gray_column_gives_grays():
    assert all(s["gray"] for s in color.near(0, 0.5, gray=True))


def test_near_keeps_lightness_in_range_at_the_edges():
    for s in color.near(200, 0.99, gray=False) + color.near(200, 0.01, gray=False):
        assert 0 < s["l"] < 1


def test_neighbors_are_sorted_and_flag_close_ones():
    repos = [
        {"name": "far", "hex": "#00ff00", "sfkey": ""},
        {"name": "twin", "hex": "#fe0101", "sfkey": "leaf"},
        {"name": "mid", "hex": "#aa0000", "sfkey": ""},
    ]
    got = color.neighbors("#ff0000", repos, count=2)
    assert [n["name"] for n in got] == ["twin", "mid"]
    assert got[0]["close"] and not got[1]["close"]
    assert got[0]["sfkey"] == "leaf"


def test_field_png_is_a_png_of_the_requested_size():
    png = color.field_png(12, 6)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", png[16:24])
    assert (width, height) == (12, 6)
    idat = png[png.index(b"IDAT") + 4:png.index(b"IEND") - 8]
    assert len(zlib.decompress(idat)) == 6 * (1 + 12 * 3)


def test_field_png_gets_lighter_toward_the_top():
    png = color.field_png(4, 8)
    raw = zlib.decompress(png[png.index(b"IDAT") + 4:png.index(b"IEND") - 8])
    rows = [raw[i * 13 + 1:(i + 1) * 13] for i in range(8)]
    assert sum(rows[0]) > sum(rows[-1])
