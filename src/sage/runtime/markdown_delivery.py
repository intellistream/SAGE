"""Bounded, self-contained Markdown frames from a complete syntax tree.

No model, transport, worker or retry policy lives here. Canonical source remains
unchanged; structural wrappers and table headers can repeat across frames.
Requires the ``delivery-markdown`` installation extra.
"""

from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import dataclass, field

import regex
from markdown_it.token import Token
from markdown_it.tree import SyntaxTreeNode
from mdformat._util import build_mdit
from mdformat.renderer import MDRenderer


class MarkdownDeliveryError(ValueError):
    """The complete document cannot be safely represented within this bound."""


def character_units(text: str) -> int:
    """Conservative character bound, also covering UTF-16-counting receivers."""
    return len(text.encode("utf-16-le")) // 2


@dataclass(frozen=True)
class MarkdownFrame:
    start: int
    end: int
    text: str = field(repr=False)


@dataclass(frozen=True)
class MarkdownPlan:
    source_sha256: str
    source_units: int
    max_chars: int
    frames: tuple[MarkdownFrame, ...]

    def validate(self):
        cursor = 0
        for frame in self.frames:
            if (frame.start != cursor or frame.end <= cursor or not frame.text
                    or character_units(frame.text) > self.max_chars):
                raise MarkdownDeliveryError("invalid_markdown_frame_coverage")
            cursor = frame.end
        if not self.frames or cursor != self.source_units:
            raise MarkdownDeliveryError("incomplete_markdown_frame_coverage")


def _signature(tokens):
    """Rendered non-whitespace text, formatting, links, code and table columns.

    Ordinary inter-word whitespace may normalize at message boundaries. Code
    whitespace is exact apart from the required closing-fence newline. This
    check does not establish transport support/display or source authorization.
    """
    output = []

    def walk(node, context=()):
        kind = node.type
        if kind in {"text", "text_special"}:
            output.extend((context, character) for character in node.content if not character.isspace())
            return
        if kind in {"code_inline", "fence", "code_block"}:
            content = node.content if kind == "code_inline" else node.content.removesuffix("\n")
            output.append((context, "code_inline" if kind == "code_inline" else "block_code", node.info, content))
            return
        if kind == "image":
            output.append((context, kind, tuple(sorted(node.attrs.items())), node.content))
            return
        if kind in {"hardbreak", "hr", "html_inline", "html_block"}:
            output.append((context, kind, node.content))
            return
        if kind in {"heading", "blockquote", "em", "strong", "s", "link"}:
            if kind == "link":
                output.append((context, "link", tuple(sorted(node.attrs.items()))))
            context += ((kind, node.tag, tuple(sorted(node.attrs.items()))),)
        elif kind in {"ordered_list", "bullet_list"}:
            context += ((kind, node.attrGet("start") or 1),)
        for index, child in enumerate(node.children):
            nested = context
            if kind in {"tr", "ordered_list", "bullet_list"}:
                nested += ((kind + "_position", index),)
            if child.type in {"th", "td"}:
                nested += ((child.type, index),)
            walk(child, nested)

    walk(SyntaxTreeNode(tokens))
    return output


class _Projection:
    def __init__(self, root):
        self.root = root
        self.spans = {}
        self.clusters = {}
        self.total = 0
        self._index(root)

    def _index(self, node):
        start = self.total
        if node.type == "image" or not node.children:
            if node.type in {"text", "text_special", "code_inline", "fence", "code_block"}:
                clusters = regex.findall(r"\X", node.content)
                self.clusters[id(node)] = clusters
                self.total += len(clusters) or (node.type in {"code_inline", "fence", "code_block"})
            elif not node.is_root and node.type != "inline":
                self.total += 1
        else:
            for child in node.children:
                self._index(child)
        self.spans[id(node)] = (start, self.total)

    @staticmethod
    def _token(token):
        captured = copy.copy(token)
        captured.attrs = copy.deepcopy(token.attrs)
        captured.meta = copy.deepcopy(token.meta)
        return captured

    def tokens(self, start, end):
        return self._project(self.root, start, end)

    def _project(self, node, start, end, *, force=False):
        begin, finish = self.spans[id(node)]
        selected = begin < end and finish > start
        if not selected and not force:
            return []
        if node.type == "image":
            return copy.deepcopy(node.to_tokens()) if selected else []
        if not selected and force and node.type in {"th", "td"}:
            inline = Token("inline", "", 0)
            inline.children = []
            return [self._token(node.nester_tokens.opening), inline,
                    self._token(node.nester_tokens.closing)]
        if not node.children:
            if node.is_root:
                return []
            token = self._token(node.token)
            if id(node) in self.clusters:
                clusters = self.clusters[id(node)]
                token.content = "".join(clusters[max(0, start - begin):max(0, min(finish, end) - begin)])
                if token.type in {"fence", "code_block"} and not token.content.endswith("\n"):
                    token.content += "\n"  # Closing-fence framing, not source content.
            if token.type == "inline":
                token.children = []
                token.content = ""
            return [token]
        children = []
        first_list_index = None
        for index, child in enumerate(node.children):
            # Every table fragment needs its header and every selected row must
            # retain its original column positions, including empty cells.
            if node.type == "table" and child.type == "thead" and selected:
                projected = copy.deepcopy(child.to_tokens())
            else:
                projected = self._project(child, start, end, force=node.type == "tr")
            if projected:
                if first_list_index is None:
                    first_list_index = index
                children.extend(projected)
        if node.is_root:
            return children
        if node.token is not None:
            token = self._token(node.token)
            token.children = children
            token.content = ""
            return [token]
        opening = self._token(node.nester_tokens.opening)
        if node.type == "ordered_list":
            opening.attrs["start"] = (node.attrGet("start") or 1) + (first_list_index or 0)
        if node.type in {"em", "strong", "s"}:
            # A cut can expose whitespace inside a style delimiter, invalid in
            # CommonMark. Keep that whitespace outside the reopened wrapper.
            prefix, suffix = [], []
            while children:
                if children[0].type in {"softbreak", "hardbreak"}:
                    prefix.append(children.pop(0))
                    continue
                if children[0].type != "text":
                    break
                text = children[0].content
                whitespace = text[:len(text) - len(text.lstrip())]
                if whitespace:
                    token = Token("text", "", 0)
                    token.content = whitespace
                    prefix.append(token)
                    children[0].content = text.lstrip()
                    if not children[0].content:
                        children.pop(0)
                        continue
                break
            while children:
                if children[-1].type in {"softbreak", "hardbreak"}:
                    suffix.insert(0, children.pop())
                    continue
                if children[-1].type != "text":
                    break
                text = children[-1].content
                whitespace = text[len(text.rstrip()):]
                if whitespace:
                    token = Token("text", "", 0)
                    token.content = whitespace
                    suffix.insert(0, token)
                    children[-1].content = text.rstrip()
                    if not children[-1].content:
                        children.pop()
                        continue
                break
            if not children:
                return [*prefix, *suffix]
            return [*prefix, opening, *children, self._token(node.nester_tokens.closing), *suffix]
        return [opening, *children, self._token(node.nester_tokens.closing)]


def plan_markdown(source: str, *, max_chars: int, literal_tokens: tuple[str, ...] = ()) -> MarkdownPlan:
    """Plan every parsed content unit, without a summary or truncation fallback.

    CommonMark/GFM formatting is normalized by the pinned maintained renderer.
    Links retain complete destinations in each referencing frame; nested
    containers, style spans, reference definitions and code fences are rebuilt
    as self-contained Markdown. HTML is literal, not an executable transport.
    Unknown/unframeable structure and rendering drift fail before delivery.
    """
    if (not isinstance(source, str) or not source.strip() or type(max_chars) is not int or max_chars < 1
            or not isinstance(literal_tokens, tuple)
            or any(not isinstance(token, str) or not token or "\n" in token or "\r" in token
                   for token in literal_tokens)):
        raise MarkdownDeliveryError("invalid_markdown_plan_input")
    parser = build_mdit(MDRenderer, extensions=("gfm",), codeformatters=())
    parser.options["html"] = False
    environment = {}
    tokens = parser.parse(source, environment)
    if literal_tokens:
        pattern = re.compile("(" + "|".join(re.escape(token) for token in sorted(set(literal_tokens),
                                                                                key=len, reverse=True)) + ")")

        def protect(tokens):
            protected = []
            for token in tokens:
                if token.type == "text":
                    for index, part in enumerate(pattern.split(token.content)):
                        if part:
                            literal = Token("code_inline" if index % 2 else "text", "", 0)
                            literal.content = part
                            protected.append(literal)
                else:
                    if token.children:
                        token.children = protect(token.children)
                    protected.append(token)
            return protected

        tokens = protect(tokens)
    tree = SyntaxTreeNode(tokens)
    projection = _Projection(tree)
    if not projection.total:
        raise MarkdownDeliveryError("markdown_has_no_renderable_content")

    def render(start, end, *, verify=False):
        tokens = projection.tokens(start, end)
        try:
            text = parser.renderer.render(tokens, parser.options, copy.deepcopy(environment))
            if verify and _signature(tokens) != _signature(parser.parse(text, {})):
                raise MarkdownDeliveryError("markdown_rendering_changed_content")
        except MarkdownDeliveryError:
            raise
        except (KeyError, IndexError, ValueError, AssertionError, NotImplementedError):
            raise MarkdownDeliveryError("markdown_structure_not_renderable") from None
        return text

    frames = []
    start = 0
    while start < projection.total:
        end = projection.total
        text = render(start, end)
        if character_units(text) > max_chars:
            low, high, best = start + 1, end, start
            while low <= high:
                middle = (low + high) // 2
                if character_units(render(start, middle)) <= max_chars:
                    best, low = middle, middle + 1
                else:
                    high = middle - 1
            end = best
            if end == start:
                raise MarkdownDeliveryError("indivisible_markdown_exceeds_frame_limit")
        text = render(start, end, verify=True)
        frames.append(MarkdownFrame(start, end, text))
        start = end
    plan = MarkdownPlan(hashlib.sha256(source.encode("utf-8")).hexdigest(),
                        projection.total, max_chars, tuple(frames))
    plan.validate()
    return plan
