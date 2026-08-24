from pathlib import Path

import pytest

from videogen.pipeline import workdir


@pytest.fixture(autouse=True)
def reset_root():
    workdir.set_tmp_root(None)
    yield
    workdir.set_tmp_root(None)


def test_no_root_set_uses_os_default_temp_dir() -> None:
    import tempfile

    work_dir = workdir.make_work_dir(prefix="videogen_test_")
    try:
        assert work_dir.parent == Path(tempfile.gettempdir())
        assert work_dir.name.startswith("videogen_test_")
    finally:
        work_dir.rmdir()


def test_custom_root_nests_work_dir_under_it(tmp_path: Path) -> None:
    root = tmp_path / "custom_root"
    workdir.set_tmp_root(str(root))

    work_dir = workdir.make_work_dir(prefix="videogen_test_")

    assert work_dir.parent == root
    assert work_dir.name.startswith("videogen_test_")


def test_custom_root_is_created_if_missing(tmp_path: Path) -> None:
    root = tmp_path / "does" / "not" / "exist" / "yet"
    assert not root.exists()
    workdir.set_tmp_root(str(root))

    work_dir = workdir.make_work_dir(prefix="videogen_test_")

    assert root.exists()
    assert work_dir.parent == root


def test_blank_string_root_behaves_like_none(tmp_path: Path) -> None:
    import tempfile

    workdir.set_tmp_root("")

    work_dir = workdir.make_work_dir(prefix="videogen_test_")
    try:
        assert work_dir.parent == Path(tempfile.gettempdir())
    finally:
        work_dir.rmdir()


def test_set_tmp_root_none_clears_a_previously_set_root(tmp_path: Path) -> None:
    import tempfile

    workdir.set_tmp_root(str(tmp_path / "root"))
    workdir.set_tmp_root(None)

    work_dir = workdir.make_work_dir(prefix="videogen_test_")
    try:
        assert work_dir.parent == Path(tempfile.gettempdir())
    finally:
        work_dir.rmdir()
