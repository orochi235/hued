import json
import os
import threading
import urllib.error
import urllib.request

import pytest

from huedmap import server, symbols

HUED = os.path.join(os.path.dirname(__file__), "..", "..", "bin", "hued")
TOKEN = "secret"


def _hued(path, text):
    path.mkdir(parents=True, exist_ok=True)
    (path / ".hued").write_text(text)


@pytest.fixture
def tree(tmp_path):
    _hued(tmp_path / "alpha", "background=#ff0000  # red\nsfkey=leaf\n")
    _hued(tmp_path / "beta" / "inner", "background=midnightblue\n")
    _hued(tmp_path / "quiet", "background=none\n")
    _hued(tmp_path / "textonly", "foreground=#99ffff\n")
    (tmp_path / "new").mkdir()
    return tmp_path


@pytest.fixture
def app(tree):
    target = str(tree / "new")
    index = symbols.Index(["leaf", "leaf.fill", "bolt"], {})
    return server.App(server.load_repos(str(tree), target), str(tree), target,
                      HUED, TOKEN, index=index, env={"HUED_TTY": os.devnull})


def get(app, path):
    status, _, body = app.handle("GET", path)
    return status, body


def get_json(app, path):
    status, body = get(app, path)
    assert status == 200
    return json.loads(body)


def test_load_repos_keeps_only_real_backgrounds(tree):
    repos = server.load_repos(str(tree), str(tree / "new"))
    assert [(r["name"], r["hex"], r["sfkey"]) for r in repos] == [
        ("alpha", "#ff0000", "leaf"),
        (os.path.join("beta", "inner"), "#191970", ""),
    ]


def test_load_repos_leaves_out_the_directory_being_colored(tree):
    _hued(tree / "new", "background=#123456\n")
    names = [r["name"] for r in server.load_repos(str(tree), str(tree / "new"))]
    assert "new" not in names


def test_writes_adds_dark_text_only_on_a_light_background():
    assert server.writes("#320053") == [("bg", "background", "#320053")]
    assert server.writes("#ffffc4", "leaf") == [
        ("bg", "background", "#ffffc4"), ("fg", "foreground", "#000000"), ("sfkey", "sfkey", "leaf")]


@pytest.mark.parametrize("path", ["/", "/data", "/field.png", "/?t=wrong", "/near?h=1&l=0.5"])
def test_requests_without_the_token_are_refused(app, path):
    assert get(app, path)[0] == 403


def test_post_without_the_token_is_refused_and_writes_nothing(app, tree):
    status, _, _ = app.handle("POST", "/use", b'{"background": "#123456"}')
    assert status == 403
    assert not (tree / "new" / ".hued").exists()
    assert not app.done.is_set()


def test_page_and_images_are_served(app):
    status, kind, body = app.handle("GET", f"/?t={TOKEN}")
    assert (status, kind) == (200, "text/html; charset=utf-8")
    assert b"<canvas" in body
    for name in ("field.png", "grays.png"):
        assert get(app, f"/{name}?t={TOKEN}")[1][:4] == b"\x89PNG"


def test_unknown_path_is_not_found(app):
    assert get(app, f"/nope?t={TOKEN}")[0] == 404


def test_data_lists_repos_and_gaps_for_each_limit(app, tree):
    data = get_json(app, f"/data?t={TOKEN}")
    assert data["name"] == "new"
    assert [r["name"] for r in data["repos"]] == ["alpha", os.path.join("beta", "inner")]
    assert set(data["gaps"]) == {"any", "dark", "light"}
    first = data["gaps"]["any"][0]
    assert first["tag"] == "gap 1"
    assert first["writes"][0] == f"background={first['hex']}"
    assert len(first["neighbors"]) == 2
    assert data["symbols"] == {"search": True, "glyphs": False}
    assert data["current"] == {}


def test_data_reports_the_current_file(app, tree):
    _hued(tree / "new", "background=#123456\nsfkey=bolt\n")
    assert get_json(app, f"/data?t={TOKEN}")["current"] == {"background": "#123456", "sfkey": "bolt"}


def test_near_flags_a_swatch_that_sits_on_a_taken_color(app):
    red = next(r for r in app.repos if r["name"] == "alpha")
    swatches = get_json(app, f"/near?t={TOKEN}&h={red['h']}&l={red['l']}")["swatches"]
    assert [s["tag"] for s in swatches] == ["vivid", "medium", "muted", "lighter", "darker"]
    assert swatches[0]["neighbors"][0]["name"] == "alpha"
    assert swatches[0]["neighbors"][0]["close"]


@pytest.mark.parametrize("hue", ["red", "nan", "inf"])
def test_near_rejects_a_hue_that_is_not_a_number(app, hue):
    assert get(app, f"/near?t={TOKEN}&h={hue}&l=0.5")[0] == 400


def test_symbols_marks_the_taken_ones(app):
    names = get_json(app, f"/symbols?t={TOKEN}&q=leaf")["names"]
    assert names == [{"name": "leaf", "taken": "alpha"}, {"name": "leaf.fill", "taken": None}]


def test_glyphs_is_empty_without_a_helper(app):
    assert get_json(app, f"/glyphs?t={TOKEN}&names=leaf") == {}


def test_use_writes_the_file_and_finishes(app, tree):
    status, _, body = app.handle("POST", f"/use?t={TOKEN}", b'{"background": "#FFFFC4", "sfkey": "bolt"}')
    assert status == 200
    assert json.loads(body)["written"] == ["background=#ffffc4", "foreground=#000000", "sfkey=bolt"]
    assert (tree / "new" / ".hued").read_text() == (
        "# https://github.com/orochi235/hued\nbackground=#ffffc4\nforeground=#000000\nsfkey=bolt\n")
    assert app.finished() == "picked"


def test_use_keeps_other_keys_in_an_existing_file(app, tree):
    _hued(tree / "new", "background=#123456\naccent=#89fe05\n")
    app.handle("POST", f"/use?t={TOKEN}", b'{"background": "#320053"}')
    text = (tree / "new" / ".hued").read_text()
    assert "accent=#89fe05" in text
    assert "background=#320053" in text
    assert "#123456" not in text


@pytest.mark.parametrize("body", [
    b'{"background": "red"}',
    b'{"background": "#12345"}',
    b'{"background": "#123456", "sfkey": "leaf; rm -rf"}',
    b'not json',
])
def test_use_refuses_bad_input_and_writes_nothing(app, tree, body):
    status, _, _ = app.handle("POST", f"/use?t={TOKEN}", body)
    assert status == 400
    assert not (tree / "new" / ".hued").exists()
    assert app.finished() is None


def test_closing_the_tab_ends_the_server_after_a_pause(app, monkeypatch):
    app.handle("POST", f"/bye?t={TOKEN}")
    assert app.finished() is None
    monkeypatch.setattr(server, "LEAVE_SECONDS", 0)
    assert app.finished() == "closed"


def test_a_reload_cancels_the_goodbye(app, monkeypatch):
    app.handle("POST", f"/bye?t={TOKEN}")
    app.handle("GET", f"/?t={TOKEN}")
    monkeypatch.setattr(server, "LEAVE_SECONDS", 0)
    assert app.finished() is None


def test_idle_server_stops(app, monkeypatch):
    monkeypatch.setattr(server, "IDLE_SECONDS", 0)
    assert app.finished() == "idle"


def test_starting_the_server_looks_nothing_up(app, monkeypatch):
    def lookup(*args):
        raise AssertionError("name lookup at bind")

    monkeypatch.setattr("socket.getfqdn", lookup)
    httpd = server.make_server(app)
    httpd.server_close()


def test_over_a_real_socket(app, tree):
    httpd = server.make_server(app)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        assert httpd.server_address[0] == "127.0.0.1"
        base = server.url(httpd, TOKEN)
        assert b"<canvas" in urllib.request.urlopen(base).read()
        with pytest.raises(urllib.error.HTTPError) as refused:
            urllib.request.urlopen(base.replace(TOKEN, "wrong"))
        assert refused.value.code == 403
        request = urllib.request.Request(
            base.replace("/?", "/use?"), data=b'{"background": "#320053"}', method="POST")
        assert json.loads(urllib.request.urlopen(request).read())["written"] == ["background=#320053"]
        assert server.wait(app) == "picked"
    finally:
        httpd.shutdown()
        httpd.server_close()
    assert "background=#320053" in (tree / "new" / ".hued").read_text()
