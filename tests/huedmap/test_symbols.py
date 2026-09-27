import base64
import plistlib

import pytest

from huedmap import symbols

INDEX = symbols.Index(
    ["map", "map.fill", "mappin", "brain", "mountain.2", "square.and.pencil", "camera"],
    {"mountain.2": ["campground", "camping", "trail"], "camera": ["photo"], "map": ["navigation"]},
)


def test_search_matches_names_with_the_exact_name_first():
    assert INDEX.search("map") == ["map", "map.fill", "mappin"]


def test_search_matches_a_name_that_has_no_keywords():
    assert INDEX.search("brain") == ["brain"]


def test_search_matches_keywords():
    assert INDEX.search("trail") == ["mountain.2"]


def test_search_matches_a_later_part_of_the_name():
    assert INDEX.search("pencil") == ["square.and.pencil"]


def test_search_needs_every_word():
    assert INDEX.search("map fill") == ["map.fill"]
    assert INDEX.search("map trail") == []


def test_search_is_case_insensitive_and_limited():
    assert INDEX.search("MAP", limit=2) == ["map", "map.fill"]


def test_empty_query_finds_nothing():
    assert INDEX.search("  ") == []


def test_load_reads_the_two_plists(tmp_path):
    (tmp_path / "symbol_order.plist").write_bytes(plistlib.dumps(["leaf", "bolt"]))
    (tmp_path / "symbol_search.plist").write_bytes(plistlib.dumps({"bolt": ["lightning"]}))
    index = symbols.Index.load(str(tmp_path))
    assert index.search("lightning") == ["bolt"]


def test_load_returns_none_when_the_index_is_missing(tmp_path):
    assert symbols.Index.load(str(tmp_path)) is None


def test_valid_rejects_anything_that_is_not_a_symbol_name():
    assert symbols.valid("square.stack.3d.up")
    assert not symbols.valid("leaf bolt")
    assert not symbols.valid("")
    assert not symbols.valid("leaf\n")


@pytest.mark.skipif(not symbols.Glyphs.available(), reason="needs macOS with swift")
def test_glyphs_draws_known_symbols_and_omits_unknown_ones():
    glyphs = symbols.Glyphs()
    try:
        got = glyphs.get(["leaf", "not.a.real.symbol", "bad name"])
        assert list(got) == ["leaf"]
        assert base64.b64decode(got["leaf"])[:8] == b"\x89PNG\r\n\x1a\n"
        assert list(glyphs.get(["leaf", "bolt"])) == ["leaf", "bolt"]
    finally:
        glyphs.close()
