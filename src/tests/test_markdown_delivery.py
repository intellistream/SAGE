"""Complete bounded documents, not paragraph-only splitting or text truncation."""

import hashlib

import pytest
import regex
from markdown_it import MarkdownIt

from sage.runtime.markdown_delivery import (
    MarkdownDeliveryError,
    character_units,
    plan_markdown,
)


@pytest.mark.parametrize("source", [
    "# Heading\n\n**bold and _nested emphasis_** with [full source](https://example.org/a?b=1&c=two).\n",
    "7. first\n   - **nested**\n     - deepest\n8. second\n\n> quote\n>\n> more\n",
    "text [reference][source]\n\n[source]: https://example.org/complete/path \"Full title\"\n",
    "| A | B |\n|---|---|\n| one | [two](https://example.org/full) |\n| three | four |\n",
    "```python\n  print('``` stays code')\n\n```\n\ninline `` `code` `` and ~~deleted~~\n",
    "Literal <@U123> <!channel> <#C123|channel> <script>unsafe()</script> and \\*escaped\\*.\n",
    "    indented code\n    more code\n",
    "```\n```\n\n![alt text](https://example.org/image.png \"title\")\n\n---\n",
    "- [x] done\n- [ ] not done\n",
])
def test_small_document_is_complete_and_parseable(source):
    plan = plan_markdown(source, max_chars=12000)
    plan.validate()
    assert plan.source_sha256 == hashlib.sha256(source.encode()).hexdigest()
    assert len(plan.frames) == 1
    assert plan.frames[0].start == 0 and plan.frames[0].end == plan.source_units
    assert MarkdownIt().parse(plan.frames[0].text)
    assert "unsafe()" not in repr(plan)


@pytest.mark.parametrize("kind", ["paragraph", "strong_link", "nested", "code", "table"])
def test_long_document_has_no_gaps_and_preserves_tail_and_full_links(kind):
    url = "https://example.org/a/complete/source?" + "key=value&" * 8
    words = " ".join(f"word{index:04}" for index in range(600)) + " FINAL_SENTINEL"
    source = {
        "paragraph": words,
        "strong_link": f"**[{words}]({url})**",
        "nested": f"3. outer\n   - **{words}**\n4. FINAL_LIST_ITEM",
        "code": "```python\n" + words + "\n```",
        "table": "| Name | Evidence |\n|---|---|\n" + "\n".join(
            f"| row{i} | [source{i}]({url}) |" for i in range(40)) + "\n| final | FINAL_SENTINEL |",
    }[kind]
    plan = plan_markdown(source, max_chars=700)
    assert len(plan.frames) > 1
    plan.validate()
    combined = "\n".join(frame.text for frame in plan.frames)
    assert "FINAL_SENTINEL" in combined
    if kind == "nested":
        assert "FINAL_LIST_ITEM" in combined
    if kind in {"table", "strong_link"}:
        assert url in combined
        all_links = []
        for frame in plan.frames:
            links = [token.attrGet("href") for block in MarkdownIt().parse(frame.text)
                     for token in (block.children or []) if token.type == "link_open"]
            if kind == "strong_link":
                assert links, "every caption fragment must retain its complete destination"
            assert all(link == url for link in links)
            all_links.extend(links)
        assert len(all_links) >= (40 if kind == "table" else len(plan.frames))
    if kind in {"paragraph", "strong_link", "nested"}:
        visible = "".join(token.content for frame in plan.frames
                          for block in MarkdownIt().parse(frame.text)
                          for token in (block.children or []) if token.type == "text")
        expected = "outer" + words + "FINAL_LIST_ITEM" if kind == "nested" else words
        assert "".join(visible.split()) == "".join(expected.split())
    if kind == "code":
        bodies = [block.content.removesuffix("\n") for frame in plan.frames
                  for block in MarkdownIt().parse(frame.text) if block.type == "fence"]
        assert "".join(bodies) == words
    assert all(character_units(frame.text) <= 700 for frame in plan.frames)


def test_unicode_graphemes_are_not_split():
    cluster = "👩🏽‍🔬e\u0301"
    plan = plan_markdown(cluster * 100, max_chars=80)
    recovered = "".join(frame.text.rstrip("\n") for frame in plan.frames)
    assert recovered == cluster * 100
    for frame in plan.frames:
        assert all(grapheme in set(regex.findall(r"\X", cluster))
                   for grapheme in regex.findall(r"\X", frame.text.rstrip("\n")))


def test_indivisible_url_is_rejected_without_truncation():
    source = "[source](https://example.org/" + "x" * 1000 + ")"
    with pytest.raises(MarkdownDeliveryError, match="indivisible_markdown"):
        plan_markdown(source, max_chars=100)


@pytest.mark.parametrize("mutation", [
    lambda text: text.replace("CANARY", ""),
    lambda text: text.replace("example.org", "wrong.org"),
    lambda text: text.replace("**", ""),
])
def test_independent_render_check_rejects_content_link_or_format_drift(monkeypatch, mutation):
    from mdformat.renderer import MDRenderer
    original = MDRenderer.render

    def altered(self, *args, **kwargs):
        return mutation(original(self, *args, **kwargs))

    monkeypatch.setattr(MDRenderer, "render", altered)
    with pytest.raises(MarkdownDeliveryError, match="markdown_rendering_changed_content"):
        plan_markdown("**CANARY** [source](https://example.org/full)", max_chars=12000)


def test_platform_control_tokens_are_literal_code_not_mentions():
    controls = ("<@U123>", "<!channel>", "<#C123|name>")
    plan = plan_markdown("**hello <@U123>** <!channel> <#C123|name> `already code`",
                         max_chars=12000, literal_tokens=controls)
    parsed = MarkdownIt().parse(plan.frames[0].text)
    codes = [token.content for block in parsed for token in (block.children or [])
             if token.type == "code_inline"]
    assert codes == [*controls, "already code"]


@pytest.mark.parametrize("source", [
    "> 2. **_" + "abc * escaped \\* text " * 150 + "_**",
    "| A | B | C |\n|---|---|---|\n| left | " + "longcell " * 500 + " | right |",
    "\n".join(f"{i}. number{i}" for i in range(7, 90)),
    "**a** **b** _c_ ` d ` " * 300,
    "**" + "one\ntwo\n" * 100 + "tail**",
    "before a*b*c after " * 150,
    "> quoted\n>\n> **" + "long quote " * 300 + "**",
], ids=["nested-style", "long-table-cell", "ordered-numbers", "adjacent-spans",
        "multiline-style", "intraword-emphasis", "long-blockquote"])
def test_structural_stress_regression(source):
    plan = plan_markdown(source, max_chars=300)
    plan.validate()
    assert len(plan.frames) > 1


@pytest.mark.parametrize("source,limit", [("", 100), ("   ", 100), ("text", True), ("text", 0)])
def test_invalid_plan_input_is_explicit(source, limit):
    with pytest.raises(MarkdownDeliveryError, match="invalid_markdown_plan_input"):
        plan_markdown(source, max_chars=limit)
