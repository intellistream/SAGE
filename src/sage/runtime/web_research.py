"""Capability-bounded web research policy and observed execution, for any host.

Semantic intent is a proposal, not permission. Never supply retrieved evidence,
conversation history, attachments or credentials to an external query builder.
Unknown disclosure scope is denied, including in user-required mode.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

WEB_RESEARCH_INSTRUCTIONS = """
Also return web_intent with exactly need, disclosure, query, local_only_span.
Classify ONLY current_question, not history, course_context or retrieved sources.
need: forbidden (the user prohibits web access), current (time-sensitive/current external facts), sources (the user asks to
search public web/documents or externally sourced research), none (stable
explanation, local Wiki/lab facts, writing, scheduling or self-contained work).
disclosure: public for a clearly public subject; private for internal lab,
personal, unpublished, confidential or credential-bearing content; unknown for
ambiguous references such as 'it', 'that project', or unresolved pronouns.
query: a nonempty VERBATIM CONTIGUOUS public-subject span of current_question,
without personal/private context, when disclosure=public, otherwise null.
local_only_span: a verbatim current-question span explicitly limiting evidence
to Wiki/private/local sources (e.g. '根据公开 Wiki' or 'only our private KB'),
otherwise null. A preference to retrieve Wiki is NOT a prohibition on web.
Public software release/documentation questions have local_only_span=null.
Do not resolve web queries using history. A quote/negation is not a search
instruction; 'do not search' and Wiki/private-only constraints must be honored.
These fields do not grant membership or source access. Never mark internal lab
progress public simply because its project name is public.
"""


@dataclass(frozen=True)
class WebIntent:
    need: str = "none"
    disclosure: str = "unknown"
    query: str | None = None
    local_only_span: str | None = None

    def __post_init__(self):
        if (
            not isinstance(self.need, str)
            or self.need not in {"forbidden", "current", "sources", "none"}
            or not isinstance(self.disclosure, str)
            or self.disclosure not in {"public", "private", "unknown"}
            or (self.query is not None and not isinstance(self.query, str))
            or (self.local_only_span is not None and not isinstance(self.local_only_span, str))
        ):
            raise ValueError("invalid web intent values")

    @classmethod
    def parse(cls, value):
        if value is None:
            return cls()
        if (
            not isinstance(value, dict)
            or not {"need", "disclosure", "query"} <= set(value)
            or set(value) - {"need", "disclosure", "query", "local_only_span"}
        ):
            raise ValueError("invalid web intent")
        return cls(**value)


@dataclass(frozen=True)
class WebDecision:
    mode: str
    identity: str
    allowed: bool
    reason: str
    query: str | None = None


def decide_web_research(
    *,
    question: str,
    mode: str,
    identity: str,
    intent: WebIntent,
    available: bool = True,
    source_restricted: bool = False,
    active: bool = True,
    contains_private_context: bool = False,
) -> WebDecision:
    if mode not in {"auto", "never", "always"}:
        raise ValueError("invalid web mode")
    if identity not in {"guest", "account", "api_token", "slack", "admin"}:
        raise ValueError("unverified identity kind")

    def denied(reason):
        return WebDecision(mode, identity, False, reason)

    if mode == "never":
        return denied("用户禁止联网，本轮未发送外部搜索请求。")
    if intent.need == "forbidden":
        return denied("当前问题要求不联网，本轮未发送外部搜索请求。")
    if not available:
        return denied("联网能力未启用，本轮未搜索。")
    if not active:
        return denied("本轮为已解决或业务操作，不启动无关联的网页搜索。")
    if source_restricted or intent.local_only_span is not None:
        return denied("本轮限定 Wiki／私有来源，不扩大到外部网页。")
    # This host flag is trusted; model proposals cannot override it.
    if contains_private_context or intent.disclosure != "public":
        return denied("未确认可公开的搜索主题；私密或含糊内容不会发送到外部搜索。")
    query = intent.query
    if not query or not query.strip() or query not in question or len(query) > 512:
        return denied("缺少可逐字核对的当前问题搜索主题，本轮未搜索。")
    # Defense in depth, not a claim of complete secret/PII detection.
    if re.search(
        r"(?i)(?:bearer\s|sk-[a-z0-9_-]{8}|-----BEGIN|password\s*[:=]|"
        r"api[_ -]?key\s*[:=]|[\w.+-]+@[\w.-]+\.[a-z]{2,})",
        question,
    ):
        return denied("当前问题包含疑似敏感标识，不发送到外部搜索。")
    if mode == "auto" and intent.need == "none":
        return denied("本轮无需最新外部信息，优先使用授权来源或直接回答。")
    return WebDecision(
        mode,
        identity,
        True,
        "用户要求联网，已通过公开主题边界检查。"
        if mode == "always"
        else "本轮需要最新信息或公开网页依据，已选择联网。",
        query,
    )


def execute_web_research(decision: WebDecision, search: Callable, observe: Callable):
    """Observe only actual provider execution, not an optimistic workflow graph.

    The host owns HTTP transport/ACLs. Errors never appear as successful search.
    No evidence is automatically persisted or granted to a private corpus.
    """
    if not decision.allowed:
        observe("skipped", decision.reason, None)
        return []
    observe("running", "正在搜索公开网页。", None)
    try:
        hits = list(search(decision.query))
    except Exception:
        observe("failed", "网页搜索失败或超时；不能声称已取得联网依据。", None)
        return []
    checked_at = datetime.now(UTC).isoformat()
    observe(
        "completed" if hits else "empty",
        f"网页搜索返回 {len(hits)} 条候选来源；候选不等于事实已核实。"
        if hits
        else "网页搜索已执行，但未取得可用来源。",
        checked_at,
    )
    return hits
