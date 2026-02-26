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
