"""📖 Format the website's statechart examples without changing their meaning.

Run ``uv run python scripts/format_docs.py --check`` (the default) to audit
the guide, API reference, and homepage, or pass ``--write`` to update them.
Python needs the development Black dependency; JSON uses only the stdlib.
Deliberate signature sketches are reported and left alone. Malformed or
semantically changed examples fail the run before any files are written.
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import argparse
import ast
import bisect
import io
import json
import re
import sys
import textwrap
import tokenize
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
FENCE = re.compile(r"^( {0,3})(`{3,}|~{3,})([^\r\n]*)")
HIGHLIGHT = re.compile(r"^\s*\{%-?\s*highlight\s+([\w+-]+)[^%]*%\}\s*$")
END_HIGHLIGHT = re.compile(r"^\s*\{%-?\s*endhighlight\s*-?%\}\s*$")
JSON_TOKEN = re.compile(
    r'(?P<space>\s+)|(?P<string>"(?:\\.|[^"\\])*")'
    r"|(?P<comment>//[^\r\n]*|/\*[\s\S]*?\*/)"
    r'|(?P<punct>[{}\[\]:,])|(?P<atom>[^\s{}\[\]:,"/]+)'
)


class FormatError(ValueError):
    """An example cannot safely be reformatted."""


class UnsupportedSnippet(FormatError):
    """A signature or incomplete Python sketch, not an executable example."""


@dataclass(frozen=True)
class Block:
    """One complete Markdown or Liquid code block's source boundaries."""

    start: int
    end: int
    line: int
    language: str
    indent: str = ""


@dataclass
class Report:
    """Counts and diagnostics for one document."""

    blocks: int = 0
    changed: int = 0
    skipped: List[Tuple[int, str]] = field(default_factory=list)
    errors: List[Tuple[int, str]] = field(default_factory=list)


@dataclass(frozen=True)
class JsonToken:
    """A JSON/JSONC lexeme, including comments and illustrative ellipses."""

    kind: str
    text: str
    line: int
    end_line: int


def blocks(source: str) -> Iterator[Block]:
    """Yield outermost fences, respecting marker lengths and Liquid blocks."""
    active: Optional[Tuple[str, str, int, int, str]] = None
    offset = 0
    for line_number, line in enumerate(source.splitlines(keepends=True), 1):
        fence = FENCE.match(line)
        if active is not None:
            marker, language, start, opening_line, indent = active
            closing = (
                bool(END_HIGHLIGHT.match(line))
                if marker == "liquid"
                else bool(
                    fence
                    and fence[2][0] == marker[0]
                    and len(fence[2]) >= len(marker)
                    and not fence[3].strip()
                )
            )
            if closing:
                yield Block(start, offset, opening_line, language, indent)
                active = None
        else:
            highlight = HIGHLIGHT.match(line)
            if highlight:
                active = (
                    "liquid", highlight[1], offset + len(line), line_number,
                    "",
                )  # fmt: skip
            elif fence:
                info = fence[3].strip().split()
                active = (
                    fence[2], info[0] if info else "", offset + len(line),
                    line_number, fence[1],
                )  # fmt: skip
        offset += len(line)
    if active is not None and active[1] in {"python", "py", "json", "jsonc"}:
        raise FormatError(f"unclosed {active[1]} block at line {active[3]}")


def _dict_commas(source: str, tree: ast.AST) -> str:
    """Add Black's magic commas using token positions, never string search."""
    lines = source.splitlines(keepends=True)
    starts, position = [], 0
    for line in lines:
        starts.append(position)
        position += len(line)

    def token_offset(pos: Tuple[int, int]) -> int:
        return starts[pos[0] - 1] + pos[1]

    significant = [
        token
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type
        not in {
            tokenize.NL,
            tokenize.NEWLINE,
            tokenize.INDENT,
            tokenize.DEDENT,
            tokenize.COMMENT,
            tokenize.ENDMARKER,
        }
    ]
    token_starts = [token_offset(t.start) for t in significant]
    insertions = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict) or not node.keys:
            continue
        # 📝 AST columns count UTF-8 bytes; tokenize columns count characters.
        row = node.end_lineno - 1
        column = len(
            lines[row].encode("utf-8")[: node.end_col_offset].decode()
        )
        close = starts[row] + column - 1
        index = bisect.bisect_left(token_starts, close)
        if index >= len(significant) or significant[index].string != "}":
            raise FormatError("dictionary inside a string cannot be expanded")
        previous = significant[index - 1]
        if previous.string != ",":
            insertions.add(token_offset(previous.end))
    for position in sorted(insertions, reverse=True):
        source = source[:position] + "," + source[position:]
    return source


def format_python(source: str) -> str:
    """Expand nonempty dictionaries, preserving comments and the Python AST.

    Bare dictionary-member fragments are validated inside synthetic braces;
    those braces are removed again before returning the displayed fragment.
    """
    wrapped = False
    candidate = source
    try:
        tree = ast.parse(candidate)
    except SyntaxError:
        candidate = "{\n" + source + "\n}\n"
        try:
            tree = ast.parse(candidate)
        except SyntaxError as exc:
            raise UnsupportedSnippet(exc.msg) from exc
        wrapped = True
    if not any(isinstance(n, ast.Dict) and n.keys for n in ast.walk(tree)):
        return source
    try:
        import black
    except ImportError as exc:
        raise FormatError(
            "Python examples require Black (install lint group)"
        ) from exc
    candidate = _dict_commas(candidate, tree)
    try:
        formatted = black.format_str(
            candidate, mode=black.Mode(line_length=79)
        )
        formatted_tree = ast.parse(formatted)
        if ast.dump(tree) != ast.dump(formatted_tree):
            raise FormatError("Black changed the example's Python AST")
    except (SyntaxError, black.InvalidInput) as exc:
        raise FormatError(f"Python formatting failed: {exc}") from exc
    for node in ast.walk(formatted_tree):
        if not isinstance(node, ast.Dict) or not node.keys:
            continue
        entries = [
            (key if key is not None else value).lineno
            for key, value in zip(node.keys, node.values)
        ]
        if node.lineno in entries or len(entries) != len(set(entries)):
            raise FormatError(
                "a formatting directive kept a dictionary compact"
            )
    if wrapped:
        inner = formatted.splitlines()[1:-1]
        formatted = textwrap.dedent("\n".join(inner)) + "\n"
        if ast.dump(tree) != ast.dump(ast.parse("{\n" + formatted + "}\n")):
            raise FormatError("fragment unwrapping changed its Python AST")
    return formatted


def _json_tokens(source: str) -> List[JsonToken]:
    tokens, position, line = [], 0, 1
    while position < len(source):
        match = JSON_TOKEN.match(source, position)
        if match is None:
            raise FormatError(
                f"unrecognized JSON token on snippet line {line}"
            )
        value = match[0]
        end_line = line + value.count("\n")
        if match.lastgroup != "space":
            tokens.append(JsonToken(match.lastgroup, value, line, end_line))
        position, line = match.end(), end_line
    return tokens


def _json_pairs(tokens: List[JsonToken]) -> Dict[int, int]:
    pairs, stack = {}, []
    for index, token in enumerate(tokens):
        if token.kind != "punct":
            continue
        if token.text in {"{", "["}:
            stack.append(index)
        elif token.text in {"}", "]"}:
            if (
                not stack
                or tokens[stack[-1]].text != {"}": "{", "]": "["}[token.text]
            ):
                raise FormatError("unbalanced JSON delimiters")
            pairs[stack.pop()] = index
    if stack:
        raise FormatError("unbalanced JSON delimiters")
    return pairs


def _layout_json(tokens: List[JsonToken]) -> str:
    """Lay out JSON tokens, keeping small scalar lists and empty objects inline."""
    pairs = _json_pairs(tokens)
    output, stack = [], []
    current, depth = "", 0

    def write(value: str) -> None:
        nonlocal current
        if not current:
            current = "  " * depth
        current += value

    def newline() -> None:
        nonlocal current
        if current.strip():
            output.append(current.rstrip())
        current = ""

    for index, token in enumerate(tokens):
        value = token.text
        previous = tokens[index - 1] if index else None
        following = tokens[index + 1] if index + 1 < len(tokens) else None
        if token.kind == "comment":
            if current and previous and token.line == previous.end_line:
                if not current.endswith(" "):
                    write(" ")
            else:
                newline()
            write(value)
            newline()
        elif token.kind == "punct" and value in {"{", "["}:
            inside = tokens[index + 1 : pairs[index]]
            compact = not inside or (
                value == "["
                and all(
                    t.kind != "comment" and t.text not in {"{", "["}
                    for t in inside
                )
                and sum(len(t.text) + 1 for t in inside) + depth * 2 < 77
            )
            if not stack and previous and token.line > previous.end_line:
                newline()
            write(value)
            stack.append(not compact)
            if not compact:
                newline()
                depth += 1
        elif token.kind == "punct" and value in {"}", "]"}:
            if stack.pop():
                newline()
                depth -= 1
            write(value)
        elif token.kind == "punct" and value == ",":
            write(",")
            trailing_comment = (
                following
                and following.kind == "comment"
                and following.line == token.end_line
            )
            if (not stack or stack[-1]) and not trailing_comment:
                newline()
            else:
                write(" ")
        elif token.kind == "punct" and value == ":":
            write(": ")
        else:
            write(value)
    newline()
    return "\n".join(output) + "\n"


def _ordered_pairs(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    """Reject duplicate keys instead of silently discarding their values."""
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def format_json(source: str) -> str:
    """Use two-space JSON, preserving every lexeme in JSONC and fragments."""
    try:
        value = json.loads(source, object_pairs_hook=_ordered_pairs)
    except ValueError:
        tokens = _json_tokens(source)
        formatted = _layout_json(tokens)
        before = [(t.kind, t.text) for t in tokens]
        after = [(t.kind, t.text) for t in _json_tokens(formatted)]
        if before != after:
            raise FormatError("fragment formatting changed JSON tokens")
        return formatted
    try:
        canonical = json.dumps(value, ensure_ascii=False, allow_nan=False)
    except ValueError as exc:
        raise FormatError("non-finite numbers are not valid JSON") from exc
    formatted = _layout_json(_json_tokens(canonical))
    if json.loads(formatted, object_pairs_hook=list) != json.loads(
        source, object_pairs_hook=list
    ):
        raise FormatError("formatting changed JSON values or key order")
    return formatted


def format_document(source: str) -> Tuple[str, Report]:
    """Format supported examples; leave surrounding prose and fences intact."""
    report, edits = Report(), []
    try:
        discovered = list(blocks(source))
    except FormatError as exc:
        report.errors.append((1, str(exc)))
        return source, report
    for block in discovered:
        language = block.language.lower()
        if language not in {"python", "py", "json", "jsonc"}:
            continue
        report.blocks += 1
        body = source[block.start : block.end]
        snippet = (
            "\n".join(
                (
                    line[len(block.indent) :]
                    if line.startswith(block.indent)
                    else line
                )
                for line in body.splitlines()
            )
            + "\n"
        )
        try:
            formatted = (
                format_python(snippet)
                if language in {"python", "py"}
                else format_json(snippet)
            )
            if block.indent:
                formatted = textwrap.indent(formatted, block.indent)
        except UnsupportedSnippet as exc:
            report.skipped.append((block.line, str(exc)))
            continue
        except (FormatError, ValueError, tokenize.TokenError) as exc:
            report.errors.append((block.line, str(exc)))
            continue
        if formatted != body:
            report.changed += 1
            edits.append((block.start, block.end, formatted))
    for start, end, replacement in reversed(edits):
        source = source[:start] + replacement + source[end:]
    return source, report


def default_paths(root: Path = ROOT) -> List[Path]:
    """Return only the published guide, API reference, and homepage sources."""
    return [
        *sorted((root / "docs" / "_guide").rglob("*.md")),
        root / "docs" / "api" / "index.md",
        root / "docs" / "index.html",
    ]


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Audit by default; write only after every example passes safety checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true", help="report drift (default)"
    )
    mode.add_argument(
        "--write", action="store_true", help="format website examples"
    )
    parser.add_argument(
        "paths", nargs="*", type=Path, help="optional individual files"
    )
    args = parser.parse_args(argv)
    results = []
    for path in args.paths or default_paths():
        try:
            source = path.read_text(encoding="utf-8")
            formatted, report = format_document(source)
        except OSError as exc:
            formatted, report = "", Report(errors=[(1, str(exc))])
        results.append((path, formatted, report))
        for line, message in report.skipped:
            print(f"{path}:{line}: skipped Python sketch: {message}")
        for line, message in report.errors:
            print(f"{path}:{line}: ERROR: {message}", file=sys.stderr)
        if report.changed:
            print(f"{path}: {report.changed} block(s) need formatting")
    errors = sum(len(r.errors) for _, _, r in results)
    changed = sum(r.changed for _, _, r in results)
    if args.write and not errors:
        for path, formatted, report in results:
            if report.changed:
                with path.open("w", encoding="utf-8", newline="\n") as handle:
                    handle.write(formatted)
    print(
        f"{len(results)} files; {sum(r.blocks for _, _, r in results)} "
        f"Python/JSON blocks; {changed} {'formatted' if args.write and not errors else 'need formatting'}; "
        f"{sum(len(r.skipped) for _, _, r in results)} skipped sketches; "
        f"{errors} errors"
    )
    return 2 if errors else int(bool(changed and not args.write))


if __name__ == "__main__":
    raise SystemExit(main())
