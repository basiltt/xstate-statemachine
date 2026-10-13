"""📖 Documentation formatting preserves programs, fragments, and comments."""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import ast
import importlib.util
import json
from pathlib import Path
from typing import Dict, Optional, Set

# -------------------------------------------------------------------------
# 📥 Third-Party Imports
# -------------------------------------------------------------------------
import pytest

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from scripts.format_docs import (
    FormatError,
    UnsupportedSnippet,
    blocks,
    default_paths,
    format_document,
    format_json,
    format_python,
    main,
)

HAS_BLACK = importlib.util.find_spec("black") is not None


@pytest.mark.skipif(not HAS_BLACK, reason="Python formatting needs Black")
class TestPythonFormatting:
    """Magic trailing commas expand nested mappings without AST changes."""

    def test_every_nested_nonempty_dictionary_expands(self) -> None:
        source = (
            'chart = {"id": "m", "initial": "idle", "states": '
            '{"idle": {"on": {"GO": "done"}}, "done": {}}}\n'
        )
        formatted = format_python(source)
        assert ast.dump(ast.parse(source)) == ast.dump(ast.parse(formatted))
        for node in ast.walk(ast.parse(formatted)):
            if isinstance(node, ast.Dict) and node.keys:
                assert node.lineno != node.end_lineno
                assert len({key.lineno for key in node.keys}) == len(node.keys)
        assert '"done": {}' in formatted
        assert format_python(formatted) == formatted

    def test_unicode_columns_and_comments(self) -> None:
        source = (
            'label = "café"; chart = {"context": {"é": "🌿"},\n'
            '    "states": {"idle": {}} # keep this explanation\n'
            "}\n"
        )
        formatted = format_python(source)
        assert "# keep this explanation" in formatted
        assert '"🌿"' in formatted
        assert ast.dump(ast.parse(source)) == ast.dump(ast.parse(formatted))

    def test_parenthesized_values_unpacking_and_lambda(self) -> None:
        source = 'chart = {"context": (context), **(extra), "entry": lambda: {"ok": True}}\n'
        formatted = format_python(source)
        assert ast.dump(ast.parse(source)) == ast.dump(ast.parse(formatted))
        assert format_python(formatted) == formatted

    def test_string_contents_are_not_scanned_as_dictionaries(self) -> None:
        source = 'chart = {"description": "{do not split, these braces}", "states": {"idle": {}}}\n'
        formatted = format_python(source)
        assert '"{do not split, these braces}"' in formatted

    def test_bare_member_fragment_is_unwrapped(self) -> None:
        source = '# invocation\n"invoke": {"src": "worker", "input": lambda ctx, e: {"n": ctx["n"]}}\n'
        formatted = format_python(source)
        assert formatted.startswith('# invocation\n"invoke": {\n')
        before = ast.parse("{\n" + source + "}\n")
        after = ast.parse("{\n" + formatted + "}\n")
        assert ast.dump(before) == ast.dump(after)
        assert format_python(formatted) == formatted

    def test_signature_sketch_is_explicitly_unsupported(self) -> None:
        with pytest.raises(UnsupportedSnippet):
            format_python("MachineBuilder(machine_id: str)\n")

    def test_code_without_mapping_does_not_get_incidental_edits(self) -> None:
        source = "green  = State('green', initial=True)\n"
        assert format_python(source) == source

    def test_formatting_directive_cannot_silently_leave_a_dense_chart(
        self,
    ) -> None:
        with pytest.raises(FormatError, match="kept a dictionary compact"):
            format_python('chart = {"id": "m"}  # fmt: skip\n')


class TestJsonFormatting:
    """JSON fragments must keep every non-whitespace token in its order."""

    def test_complete_json_keeps_order_and_small_scalar_lists(self) -> None:
        source = '{"states":{"idle":{"on":{"GO":"done"}},"done":{}},"entry":["one","two"]}'
        formatted = format_json(source)
        assert '"entry": ["one", "two"]' in formatted
        assert '"done": {}' in formatted
        assert '\n  "states": {\n' in formatted
        assert json.loads(source, object_pairs_hook=list) == json.loads(
            formatted, object_pairs_hook=list
        )
        assert format_json(formatted) == formatted

    def test_lists_of_transition_objects_expand(self) -> None:
        source = '{"on":{"GO":[{"target":"yes","guard":"allowed"},{"target":"no"}]}}'
        formatted = format_json(source)
        assert '"GO": [\n      {\n' in formatted
        assert '\n        "guard": "allowed"\n' in formatted
        assert json.loads(formatted) == json.loads(source)

    def test_commented_multiple_examples_keep_comments(self) -> None:
        source = (
            '// Preferred\n{"target":"yes","guard":"allowed"}\n\n'
            '// Legacy\n{"target":"yes","cond":"allowed"}\n'
        )
        formatted = format_json(source)
        assert formatted.count("//") == 2
        assert "// Preferred\n{\n" in formatted
        assert "// Legacy\n{\n" in formatted
        assert format_json(formatted) == formatted

    def test_fragment_keeps_ellipsis_trailing_comments_and_urls(self) -> None:
        source = (
            '"invoke": [{"src":"worker", // keep the source\n'
            '"url":"https://example.test/{a,b}","onDone":...}]\n'
        )
        formatted = format_json(source)
        assert '"src": "worker", // keep the source' in formatted
        assert '"url": "https://example.test/{a,b}"' in formatted
        assert '"onDone": ...' in formatted
        assert format_json(formatted) == formatted

    def test_duplicate_keys_are_preserved_not_discarded(self) -> None:
        formatted = format_json('{"id":"first","id":"second"}')
        assert formatted.count('"id":') == 2

    def test_non_finite_numbers_fail_loudly(self) -> None:
        with pytest.raises(FormatError, match="not valid JSON"):
            format_json('{"delay": Infinity}')

    @pytest.mark.parametrize(
        "source", ['{"states": [}', '{"states": {', '{"id": "broken}']
    )
    def test_unsafe_json_is_rejected(self, source: str) -> None:
        with pytest.raises(FormatError):
            format_json(source)


class TestDocumentBoundaries:
    """Only the intended fence contents may change."""

    def test_longer_outer_fence_hides_the_inner_example(self) -> None:
        source = (
            'Before\n````markdown\n```json\n{"states":{"idle":{}}}\n'
            '```\n````\nAfter\n```json\n{"on":{"GO":"done"}}\n```\n'
        )
        discovered = list(blocks(source))
        assert [b.language for b in discovered] == ["markdown", "json"]
        formatted, report = format_document(source)
        assert report.blocks == 1 and report.changed == 1
        assert '```json\n{"states":{"idle":{}}}\n```' in formatted
        assert formatted.startswith("Before\n")
        assert "\nAfter\n" in formatted

    def test_liquid_highlight_and_tilde_fences(self) -> None:
        source = (
            '<section>\n{% highlight json %}\n{"states":{"idle":{}}}\n'
            '{% endhighlight %}\n</section>\n~~~json\n{"id":"x"}\n~~~\n'
        )
        formatted, report = format_document(source)
        assert report.blocks == report.changed == 2
        assert "{% highlight json %}\n{\n" in formatted
        assert "{% endhighlight %}\n</section>" in formatted
        assert format_document(formatted)[0] == formatted

    def test_indented_markdown_fence(self) -> None:
        source = '  ```json\n  {"on":{"GO":"done"}}\n  ```\n'
        formatted, report = format_document(source)
        assert report.changed == 1
        assert formatted.startswith('  ```json\n  {\n    "on": {\n')
        assert format_document(formatted)[0] == formatted

    def test_unclosed_supported_fence_is_an_error(self) -> None:
        source = '```json\n{"states": {}}\n'
        formatted, report = format_document(source)
        assert formatted == source
        assert report.errors and not report.changed

    def test_unsupported_python_is_reported_not_rewritten(self) -> None:
        source = "```python\n.state(name: str)\n```\n"
        formatted, report = format_document(source)
        assert formatted == source
        assert report.skipped and not report.errors


class TestCommandLine:
    """A failed safety check must never leave a partially reformatted site."""

    def test_default_is_read_only_then_write_is_idempotent(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "sample.md"
        source = '```json\n{"states":{"idle":{}}}\n```\n'
        path.write_text(source, encoding="utf-8")
        assert main([str(path)]) == 1
        assert path.read_text(encoding="utf-8") == source
        assert main(["--write", str(path)]) == 0
        assert main(["--check", str(path)]) == 0

    def test_any_error_prevents_all_writes(self, tmp_path: Path) -> None:
        good = tmp_path / "good.md"
        bad = tmp_path / "bad.md"
        source = '```json\n{"id":"m"}\n```\n'
        good.write_text(source, encoding="utf-8")
        bad.write_text('```json\n{"states":[}\n```\n', encoding="utf-8")
        assert main(["--write", str(good), str(bad)]) == 2
        assert good.read_text(encoding="utf-8") == source

    def test_missing_file_is_a_reported_error(self, tmp_path: Path) -> None:
        assert main([str(tmp_path / "missing.md")]) == 2

    def test_default_scope_excludes_readme_research_and_templates(
        self, tmp_path: Path
    ) -> None:
        paths = default_paths(tmp_path)
        assert paths == [
            tmp_path / "docs" / "api" / "index.md",
            tmp_path / "docs" / "index.html",
        ]


@pytest.mark.skipif(not HAS_BLACK, reason="Python formatting needs Black")
def test_published_examples_stay_formatted() -> None:
    """Exercise real sources so a new compact snippet cannot slip through."""
    checked, failures = 0, []
    for path in default_paths():
        source = path.read_text(encoding="utf-8")
        formatted, report = format_document(source)
        checked += report.blocks
        if source != formatted or report.errors:
            failures.append((str(path), report.changed, report.errors))
    assert checked > 700, "website example discovery regressed"
    assert not failures, (
        "Run python scripts/format_docs.py --write after reviewing: "
        f"{failures}"
    )


# 📝 These are signature notation, plus one deliberately abbreviated plugin
# sketch. An unexpected syntax failure must not hide a newly broken chart.
_KNOWN_SKETCHES: Dict[str, Set[str]] = {
    "docs/_guide/cli-templates.md": {"class CheckoutObserver(PluginBase):"},
    "docs/api/index.md": {
        "State(",
        "state.to(",
        "state.internal(",
        "MachineBuilder(machine_id: str)",
        ".state(",
        ".transition(",
        ".child_states(",
        ".build(context: Optional[Dict] = None) -> MachineNode",
        "transition(",
        "Interpreter(",
        "SyncInterpreter(",
        "(interpreter: BaseInterpreter, context: Dict, event: Event, "
        "action_def: ActionDefinition) -> None",
        "(context: Dict, event: Event) -> bool",
        "(interpreter: BaseInterpreter, context: Dict, event: Event) -> Any",
        "LogicLoader.get_instance() -> LogicLoader",
        "machine.get_state_by_id(state_id: str) -> Optional[StateNode]",
        "machine.get_next_state(from_state_id: str, event: Event) "
        "-> Optional[Set[str]]",
        "machine.structure_hash -> str",
        "machine.is_known_event(event_type: str) -> bool",
    },
}


def _fence_body(source: str, indent: str) -> str:
    """Remove only indentation belonging to the surrounding Markdown fence."""
    return (
        "\n".join(
            line[len(indent) :] if line.startswith(indent) else line
            for line in source.splitlines()
        )
        + "\n"
    )


def _layout_tree(source: str, relative_path: str) -> Optional[ast.AST]:
    """Parse Python or a bare member fragment without importing Black."""
    try:
        return ast.parse(source)
    except SyntaxError:
        try:
            return ast.parse("{\n" + source + "\n}\n")
        except SyntaxError as exc:
            first_line = source.strip().splitlines()[0]
            assert first_line in _KNOWN_SKETCHES.get(
                relative_path, set()
            ), f"Unexpected unparseable example in {relative_path}: {exc}"
            assert "{" not in source and "}" not in source, (
                f"Signature-sketch exemption cannot hide a mapping: "
                f"{relative_path}: {first_line}"
            )
            return None


def _assert_dictionary_layout(tree: ast.AST, label: str) -> int:
    """Require multiline mappings and one non-unpack key per source line."""
    checked = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict) or not node.keys:
            continue
        checked += 1
        location = f"{label}, snippet line {node.lineno}"
        assert node.lineno < node.end_lineno, f"Compact mapping: {location}"
        key_lines = [key.lineno for key in node.keys if key is not None]
        assert len(key_lines) == len(
            set(key_lines)
        ), f"Multiple mapping keys on one line: {location}"
        assert (
            node.lineno not in key_lines
        ), f"Mapping key shares the opening-brace line: {location}"
    return checked


def test_published_dictionary_layout_without_black() -> None:
    """Minimal CI still checks every Python/JSON chart, including fragments."""
    root = Path(__file__).resolve().parents[1]
    checked, dictionaries = 0, 0
    for path in default_paths(root):
        source = path.read_text(encoding="utf-8")
        relative = path.relative_to(root).as_posix()
        for block in blocks(source):
            language = block.language.lower()
            if language not in {"python", "py", "json", "jsonc"}:
                continue
            checked += 1
            body = _fence_body(source[block.start : block.end], block.indent)
            label = f"{relative}:{block.line}"
            if language in {"json", "jsonc"}:
                assert format_json(body) == body, f"JSON layout drift: {label}"
            else:
                tree = _layout_tree(body, relative)
                if tree is not None:
                    dictionaries += _assert_dictionary_layout(tree, label)
    assert checked > 700, "website example discovery regressed"
    assert dictionaries > 2000, "Python dictionary discovery regressed"


def test_embedded_and_plain_text_chart_layout_without_black() -> None:
    """Protect the generated TEST module and intentionally text-labelled data."""
    root = Path(__file__).resolve().parents[1]
    testing = root / "docs" / "_guide" / "integration-testing.md"
    comparison = root / "docs" / "_guide" / "comparisons" / "vs-transitions.md"
    seen = set()
    for path in (testing, comparison):
        source = path.read_text(encoding="utf-8")
        for block in blocks(source):
            body = _fence_body(source[block.start : block.end], block.indent)
            label = f"{path.name}:{block.line}"
            if path == comparison and block.language == "text":
                assert _assert_dictionary_layout(ast.parse(body), label) > 0
                seen.add("competitor text")
            elif path == testing and block.language == "text":
                if body.lstrip().startswith("{"):
                    assert format_json(body) == body, label
                    seen.add("coverage text")
            elif path == testing and block.language in {"python", "py"}:
                for node in ast.walk(ast.parse(body)):
                    if not isinstance(node, ast.Assign) or not any(
                        isinstance(target, ast.Name) and target.id == "TEST"
                        for target in node.targets
                    ):
                        continue
                    assert isinstance(node.value, ast.Constant)
                    assert isinstance(node.value.value, str)
                    nested = ast.parse(node.value.value)
                    assert _assert_dictionary_layout(nested, label) > 0
                    seen.add("embedded TEST")
    assert seen == {"competitor text", "coverage text", "embedded TEST"}


@pytest.mark.parametrize(
    "source",
    ['chart = {"one": 1}', 'chart = {\n    "one": 1, "two": 2,\n}\n'],
)
def test_dependency_free_layout_gate_rejects_dense_mappings(
    source: str,
) -> None:
    """Prove the stdlib invariant detects both compact and partly split maps."""
    with pytest.raises(AssertionError):
        _assert_dictionary_layout(ast.parse(source), "deliberate regression")


def test_dependency_free_layout_gate_rejects_unknown_sketches() -> None:
    """A syntax error is not a blanket exemption from documentation checks."""
    with pytest.raises(AssertionError, match="Unexpected unparseable example"):
        _layout_tree(".state(name: str)\n", "docs/_guide/new-example.md")
