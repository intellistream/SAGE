"""Source-neutral named-subject relevance for already-authorized candidates."""

from __future__ import annotations

import re


def subject_candidate_indices(subjects: tuple[str, ...], texts: tuple[str, ...]) -> tuple[int, ...]:
    """Prefer discriminating named subjects, not collection-wide labels.

    Preserve original order and all candidates for any requested subject. A name
    shared by every candidate cannot distinguish relevance (e.g. a source label).
    If no discriminating match exists, leave semantic retrieval unchanged. This
    is a relevance preference, never an authorization or truth check. Callers
    must supply complete permitted text, not truncated display excerpts.
    """
    matches = []
    for subject in dict.fromkeys(subjects):
        if not subject:
            continue
        pattern = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(subject) + r"(?![A-Za-z0-9_])", re.I)
        indices = {i for i, text in enumerate(texts) if pattern.search(text)}
        if indices and len(indices) < len(texts):
            matches.append(indices)
    selected = set().union(*matches) if matches else set(range(len(texts)))
    return tuple(i for i in range(len(texts)) if i in selected)
