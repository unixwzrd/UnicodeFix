import importlib.util
import re

import pytest
from markdown_it import MarkdownIt

from unicodefix.markdown import audit_markdown, unwrap_markdown


def test_audit_markdown_reports_soft_breaks_and_hard_breaks():
    report = audit_markdown("a wrapped\nparagraph\n\nline with hard break  \nnext\n")
    assert report["soft_break_candidates"] == 1
    assert report["protected_hard_breaks"] == 1


def test_audit_markdown_reports_list_continuations():
    report = audit_markdown("- item wraps\n  onto this line\n- next item\n")
    assert report["wrapped_list_item_continuations"] == 1


@pytest.mark.skipif(
    importlib.util.find_spec("mdformat") is None,
    reason="mdformat is an optional dependency",
)
def test_unwrap_markdown_preserves_distinct_blocks_and_hard_breaks():
    text = """A paragraph that wraps\nonto another physical line.\n\n- first item wraps\n  onto its continuation\n- second item remains separate\n\n1. ordered item wraps\n   across its continuation\n2. next ordered item\n\n> quoted prose wraps\n> on the next line\n\nline with hard break  \nnext line\n\n```python\nvalue = (\n    1\n)\n```\n\n| one | two |\n| --- | --- |\n| a | b |\n"""
    result = unwrap_markdown(text)
    assert "A paragraph that wraps onto another physical line." in result
    assert "- first item wraps onto its continuation" in result
    assert "- second item remains separate" in result
    assert "1. ordered item wraps across its continuation" in result
    assert "next ordered item" in result
    assert "> quoted prose wraps on the next line" in result
    assert "line with hard break\\\nnext line" in result
    assert "    1" in result
    assert "| one | two |" in result
    assert unwrap_markdown(result) == result


@pytest.mark.skipif(
    importlib.util.find_spec("mdformat") is None,
    reason="mdformat is an optional dependency",
)
def test_unwrap_markdown_preserves_nested_and_task_list_items():
    text = """- [ ] task wraps\n  onto a continuation\n  - nested item wraps\n    onto a continuation\n  - sibling stays separate\n- [x] separate task\n"""
    result = unwrap_markdown(text)
    assert "- [ ] task wraps onto a continuation" in result
    assert "- nested item wraps onto a continuation" in result
    assert "- sibling stays separate" in result
    assert "- [x] separate task" in result


@pytest.mark.skipif(
    importlib.util.find_spec("mdformat") is None,
    reason="mdformat is an optional dependency",
)
def test_unwrap_markdown_handles_a_list_inside_a_blockquote():
    result = unwrap_markdown(
        "> - quoted list item wraps\n>   onto a continuation\n> - separate quoted item\n"
    )
    assert "> - quoted list item wraps onto a continuation" in result
    assert "> - separate quoted item" in result


def test_unwrap_markdown_preserves_rendered_commonmark_structure():
    text = """Paragraph wraps
onto its continuation.

- first item wraps
  onto its continuation
- second item

> quote wraps
> onto its continuation
"""
    renderer = MarkdownIt("commonmark")
    result = unwrap_markdown(text)

    def normalize(html):
        return re.sub(r"\s+", " ", html).strip()

    assert normalize(renderer.render(result)) == normalize(renderer.render(text))
