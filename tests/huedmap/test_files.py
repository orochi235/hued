import json

from huedmap import files


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_read_drops_inline_comments_and_header(tmp_path):
    _write(tmp_path / ".hued", "# https://github.com/orochi235/hued\nbackground=#191970  # midnightblue\nsfkey=leaf\n")
    assert files.read(tmp_path / ".hued") == {"background": "#191970", "sfkey": "leaf"}


def test_scan_finds_nested_files_and_skips_empty_ones(tmp_path):
    _write(tmp_path / "a" / ".hued", "background=#111111\n")
    _write(tmp_path / "a" / "deep" / "er" / ".hued", "background=#222222\n")
    _write(tmp_path / "b" / ".hued", "# only a comment\n")
    (tmp_path / "c").mkdir()
    assert files.scan(tmp_path) == {
        str(tmp_path / "a"): {"background": "#111111"},
        str(tmp_path / "a" / "deep" / "er"): {"background": "#222222"},
    }


def test_scan_does_not_descend_into_dependency_directories(tmp_path):
    _write(tmp_path / "node_modules" / "pkg" / ".hued", "background=#111111\n")
    _write(tmp_path / ".git" / ".hued", "background=#222222\n")
    _write(tmp_path / ".config" / ".hued", "background=#333333\n")
    assert files.scan(tmp_path) == {str(tmp_path / ".config"): {"background": "#333333"}}


def test_normalize_hex_forms():
    assert files.normalize("#ABCDEF") == ("#abcdef", None)
    assert files.normalize("abc") == ("#aabbcc", None)
    assert files.normalize("none") == ("none", None)


def test_normalize_names():
    assert files.normalize("MidnightBlue") == ("#191970", "MidnightBlue")
    assert files.normalize("baby-poop green") == files.normalize("babypoopgreen")[:1] + ("baby-poop green",)
    assert files.normalize("notacolor") == ("notacolor", None)


def test_normalize_prefers_xkcd_when_asked():
    assert files.normalize("red")[0] == "#ff0000"
    assert files.normalize("red", xkcd=True)[0] == "#e50000"


def test_unpack_writes_names_as_hex_with_comment(tmp_path, capsys):
    target = tmp_path / "r"
    export = tmp_path / "export.json"
    export.write_text(json.dumps({str(target): {"background": "leaf", "sfkey": "leaf"}}))
    files.unpack(export, force=False)
    leaf = files.normalize("leaf")[0]
    assert (target / ".hued").read_text() == (
        f"# https://github.com/orochi235/hued\nbackground={leaf}  # leaf\nsfkey=leaf\n")


def test_unpack_skips_existing_without_force(tmp_path):
    _write(tmp_path / "r" / ".hued", "background=#000000\n")
    export = tmp_path / "export.json"
    export.write_text(json.dumps({str(tmp_path / "r"): {"background": "#ffffff"}}))
    files.unpack(export, force=False)
    assert "#000000" in (tmp_path / "r" / ".hued").read_text()
    files.unpack(export, force=True)
    assert "#ffffff" in (tmp_path / "r" / ".hued").read_text()


def test_read_takes_a_key_s_last_line(tmp_path):
    (tmp_path / ".hued").write_text("background=#111111\nbackground=#333333  # later\n")
    assert files.read(tmp_path / ".hued") == {"background": "#333333"}
