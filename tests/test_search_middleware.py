from core.search import SearchMiddleware


def test_python_find_search_recurses_for_type_file(tmp_path) -> None:
    nested_dir = tmp_path / "pkg"
    nested_dir.mkdir()
    nested_file = nested_dir / "module.py"
    nested_file.write_text("pass\n", encoding="utf-8")

    middleware = SearchMiddleware(workspace_root=tmp_path, prefer_system_tools=False, verbose=False)
    output = middleware._find_by_name_impl(
        SearchDirectory=str(tmp_path),
        Pattern="*.py",
        Type="file",
    )

    assert "Found 1 results" in output
    assert str(nested_file) in output


def test_python_find_search_stops_recursion_at_max_results(tmp_path) -> None:
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_c = tmp_path / "c"
    dir_a.mkdir()
    dir_b.mkdir()
    dir_c.mkdir()

    file_a = dir_a / "one.py"
    file_b = dir_b / "two.py"
    file_c = dir_c / "three.py"
    file_a.write_text("pass\n", encoding="utf-8")
    file_b.write_text("pass\n", encoding="utf-8")
    file_c.write_text("pass\n", encoding="utf-8")

    middleware = SearchMiddleware(
        workspace_root=tmp_path,
        max_results=2,
        prefer_system_tools=False,
        verbose=False,
    )
    output = middleware._find_by_name_impl(
        SearchDirectory=str(tmp_path),
        Pattern="*.py",
        Type="file",
    )

    assert "Found 2 results" in output
    assert str(file_a) in output
    assert str(file_b) in output
    assert str(file_c) not in output
