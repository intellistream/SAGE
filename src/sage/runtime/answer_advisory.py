"""Source-bound, advisory-only formula dependency checks.

This never generates, repairs or approves an answer. Trusted declarative
contracts describe applicability and symbol meanings; untrusted answer text
cannot add contracts. A missing dependency is conditional on the cited scope.
No network, model invocation, expression evaluation or answer logging occurs.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import re

_MATH = re.compile(r"\$\$(.+?)\$\$|\\\[(.+?)\\\]|(?<!\$)\$([^$\n]+)\$", re.S)
_DEFINITION = re.compile(
    r"([A-Za-z][A-Za-z0-9_]*)\s*(?:为|表示|代表|是|denotes?\b|is\b)\s*([^，,。;；\n)]+)", re.I
)


def _plain(text: str) -> str:
    text = text.replace(r"\_", "_")
    text = re.sub(r"\\(?:text|mathrm|operatorname)\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"([A-Za-z]+)_\{([A-Za-z0-9]+)\}", r"\1_\2", text)
    return text.replace("$", "").replace("{", "").replace("}", "")


def _symbols(expression: str) -> set[str]:
    """Parse only multiplicative expressions; never eval model-generated code."""
    expression = _plain(expression).strip()
    expression = re.sub(r"\\(?:times|cdot)\b|×|·", "*", expression)
    expression = expression.replace(r"\,", " ").replace(r"\left", "").replace(r"\right", "")
    if len(expression) > 8192:
        raise ValueError("expression too large")
    tree = ast.parse(expression, mode="eval")
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Constant):
            if (
                type(node.value) not in (int, float)
                or not math.isfinite(node.value)
                or node.value <= 0
            ):
                raise ValueError("unsupported constant")
        elif not isinstance(node, (ast.Expression, ast.BinOp, ast.Mult, ast.Div, ast.Load)):
            raise ValueError("not a simple product or quotient")
    return names


def validate_catalog(catalog: object) -> list[dict]:
    if not isinstance(catalog, list) or len(catalog) > 32:
        raise ValueError("catalog must be a bounded list")
    ids = set()
    for ref in catalog:
        if (
            not isinstance(ref, dict)
            or not {
                "id",
                "title",
                "url",
                "excerpt",
                "assumptions",
                "topic_groups",
                "quantities",
                "variables",
                "required",
            }
            <= ref.keys()
        ):
            raise ValueError("invalid source contract")
        if any(
            not isinstance(ref[k], str) or not ref[k].strip()
            for k in ("id", "title", "url", "excerpt", "assumptions")
        ):
            raise ValueError("empty source metadata")
        if ref["id"] in ids or not ref["url"].startswith("https://"):
            raise ValueError("source IDs must be unique and URLs must use HTTPS")
        ids.add(ref["id"])
        if not ref["topic_groups"] or any(
            not isinstance(g, list) or not g or any(not isinstance(t, str) or not t for t in g)
            for g in ref["topic_groups"]
        ):
            raise ValueError("invalid source applicability")
        if not isinstance(ref["variables"], dict) or not 1 <= len(ref["variables"]) <= 32:
            raise ValueError("invalid variables")
        if (
            not isinstance(ref["required"], list)
            or not ref["required"]
            or any(k not in ref["variables"] for k in ref["required"])
        ):
            raise ValueError("invalid required dependencies")
        if not isinstance(ref["quantities"], list) or not ref["quantities"]:
            raise ValueError("missing quantity aliases")
        aliases = set()
        for variable in ref["variables"].values():
            if not isinstance(variable, dict) or not isinstance(variable.get("label"), str):
                raise ValueError("invalid variable metadata")
            for key in ("aliases", "definition_terms"):
                if not isinstance(variable.get(key), list) or any(
                    not isinstance(v, str) or not v for v in variable[key]
                ):
                    raise ValueError("invalid variable aliases")
            for alias in variable["aliases"]:
                if alias in aliases:
                    raise ValueError("ambiguous catalog aliases")
                aliases.add(alias)
    return catalog


def audit_answer(question: str, answer: str, catalog: list[dict]) -> dict:
    """Return exact answer quotes and cited assumptions, never an edited answer."""
    if not isinstance(question, str) or not isinstance(answer, str) or not answer.strip():
        raise ValueError("nonempty answer and textual question required")
    if len(question.encode()) + len(answer.encode()) > 2_000_000:
        raise ValueError("advisory input too large; no truncation performed")
    validate_catalog(catalog)
    topic = (question + "\n" + answer).casefold()
    refs = [
        r
        for r in catalog
        if all(any(term.casefold() in topic for term in group) for group in r["topic_groups"])
    ]
    findings, checked = [], 0
    formulas = list(_MATH.finditer(answer))
    if len(formulas) > 256:
        raise ValueError("too many formulas; no partial coverage reported")
    for ref in refs:
        aliases = {alias: key for key, var in ref["variables"].items() for alias in var["aliases"]}
        ambiguous = set()
        # Explicit answer definitions override defaults, but conflicting meanings
        # cannot be silently selected by declaration order.
        definitions: dict[str, set[str]] = {}
        for symbol, definition in _DEFINITION.findall(_plain(answer)):
            if re.search(r"不是|不表示|并非|\bnot\b", definition, re.I):
                ambiguous.add(symbol)
                continue
            meanings = {
                key
                for key, var in ref["variables"].items()
                if any(term.casefold() in definition.casefold() for term in var["definition_terms"])
            }
            if meanings:
                definitions.setdefault(symbol, set()).update(meanings)
        for symbol, meanings in definitions.items():
            if len(meanings) == 1:
                aliases[symbol] = next(iter(meanings))
            else:
                ambiguous.add(symbol)
        for match in formulas:
            formula = next(group for group in match.groups() if group is not None)
            parts = re.split(r"\\approx|\\propto|≈|=", formula, maxsplit=1)
            if len(parts) != 2 or _plain(parts[0]).strip() not in ref["quantities"]:
                continue
            quote = match.group(0)
            try:
                names = _symbols(parts[1])
            except (ValueError, SyntaxError, RecursionError):
                findings.append(
                    dict(
                        code="formula_unchecked",
                        title="公式结构未能核验",
                        quote=quote,
                        details="此检查只支持明确的乘除关系，未推断其正确性。",
                        source_ids=[ref["id"]],
                    )
                )
                continue
            unknown = names - aliases.keys() | (names & ambiguous)
            if unknown:
                findings.append(
                    dict(
                        code="symbols_unresolved",
                        title="变量含义未能确认",
                        quote=quote,
                        details="尚未确认："
                        + "、".join(sorted(unknown))
                        + "；未据此判定公式错误。",
                        source_ids=[ref["id"]],
                    )
                )
                continue
            checked += 1
            dependencies = {aliases[name] for name in names}
            missing = set(ref["required"]) - dependencies
            if missing:
                labels = [ref["variables"][key]["label"] for key in sorted(missing)]
                findings.append(
                    dict(
                        code="missing_dependency",
                        title="公式可能缺少依赖项",
                        quote=quote,
                        details="若采用下述来源的适用假设，该式未体现："
                        + "、".join(labels)
                        + "。这不是自动纠错或完整数学证明。",
                        source_ids=[ref["id"]],
                    )
                )
    sources = [
        {k: ref[k] for k in ("id", "title", "url", "excerpt", "assumptions")} for ref in refs
    ]
    report = dict(
        version=1,
        mode="advisory",
        answer_sha256=hashlib.sha256(answer.encode()).hexdigest(),
        question_sha256=hashlib.sha256(question.encode()).hexdigest(),
        status="issues" if findings else "no_dependency_gap" if checked else "unchecked",
        checked_formulas=checked,
        findings=findings,
        sources=sources,
        scope="仅核对已匹配来源的公式变量依赖，不证明全部事实、公式等价性或数值正确性。",
        limitations=[
            "原始答案未改写；核验不参与生成或完成状态。",
            "未匹配来源、未知变量及其他事实均未核验；未发现缺项不等于答案正确。",
        ],
    )
    if len(json.dumps(report, ensure_ascii=False).encode()) > 1_000_000:
        raise ValueError("advisory result too large; no partial coverage reported")
    return report
