import os

from huedmap import files, index


def hued(d, text="background=#123456\n"):
    d.mkdir(parents=True, exist_ok=True)
    (d / ".hued").write_text(text)
    return str(d.resolve())


def test_configs_walks_and_seeds_when_there_is_no_index(tmp_path):
    a = hued(tmp_path / "tree" / "a")
    assert index.load() is None
    assert index.configs(str(tmp_path / "tree")) == {a: {"background": "#123456"}}
    assert index.load() == [a]


def test_configs_reads_the_index_instead_of_walking(tmp_path, monkeypatch):
    a = hued(tmp_path / "a")
    index.save([a])
    hued(tmp_path / "unindexed")
    monkeypatch.setattr(files, "scan", lambda root: (_ for _ in ()).throw(AssertionError("walked")))
    assert list(index.configs(str(tmp_path))) == [a]


def test_configs_keeps_to_root_and_drops_directories_whose_hued_is_gone(tmp_path):
    inside, outside, gone = hued(tmp_path / "in" / "a"), hued(tmp_path / "out"), hued(tmp_path / "in" / "b")
    index.save([inside, outside, gone])
    os.remove(os.path.join(gone, ".hued"))
    assert list(index.configs(str(tmp_path / "in"))) == [inside]
    assert index.load() == sorted([inside, outside])


def test_add_records_a_directory_once(tmp_path):
    a = hued(tmp_path / "a")
    index.add(a)
    index.add(a)
    assert index.load() == [a]


def test_refresh_replaces_only_what_is_under_root(tmp_path):
    keep, stale = hued(tmp_path / "other"), str(tmp_path / "tree" / "stale")
    new = hued(tmp_path / "tree" / "new")
    index.save([keep, stale])
    index.refresh(str(tmp_path / "tree"), [new])
    assert index.load() == sorted([keep, new])


def test_refresh_does_not_take_a_sibling_sharing_root_as_a_prefix(tmp_path):
    sibling = hued(tmp_path / "tree2")
    index.save([sibling])
    index.refresh(str(tmp_path / "tree"), [])
    assert index.load() == [sibling]


def test_pack_refreshes_the_index(tmp_path, capsys):
    a = hued(tmp_path / "a")
    files.main(["pack", str(tmp_path)])
    assert index.load() == [a]


def test_unpack_indexes_what_it_writes(tmp_path):
    target = tmp_path / "t"
    (tmp_path / "in.json").write_text('{"%s": {"background": "#abcdef"}}' % target)
    files.unpack(str(tmp_path / "in.json"), force=False)
    assert index.load() == [str(target.resolve())]
