import pytest

from backend.filesystem import safe_project_path


def test_project_path_stays_inside_workspace():
    path = safe_project_path("Demo")
    assert path.name == "Demo"
    assert path.parent.name == "Projects"


def test_project_parent_traversal_is_rejected():
    with pytest.raises(ValueError):
        safe_project_path("../outside")


def test_project_absolute_traversal_is_rejected():
    with pytest.raises(ValueError):
        safe_project_path("/tmp/outside")
