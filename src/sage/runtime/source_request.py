"""Source restrictions need a current-request witness, not an inferred topic.

Like AnswerTask, this validates provenance, not semantic correctness. Document
ACLs and explicit transport restrictions remain independently authoritative.
"""
from dataclasses import dataclass


SOURCE_REQUEST_INSTRUCTIONS = """Classify knowledge_sources independently of the topic and confidentiality:
Use null with source_directive=null unless the CURRENT QUESTION explicitly
requests a particular evidence origin. Public facts about a lab, a person or
a course are not a request for private records. Do not turn a private web
disclosure classification into a private-knowledge restriction.
For a restriction, source_directive must quote the contiguous instruction in
the current question selecting that origin, not just its subject or history.
An explicit empty source list needs the directive forbidding all retrieval.
Examples:
"这个团队做什么研究？" -> knowledge_sources=null, source_directive=null.
"只使用私有知识库，介绍课题组" -> ["private"], "只使用私有知识库".
"根据公开 Wiki 介绍课题组" -> ["wiki"], "根据公开 Wiki".
Do not invent or drop source restrictions to get an answer or bypass permissions.
"""


@dataclass(frozen=True)
class SourceRequest:
    origins: tuple[str, ...] | None
    directive: str | None = None

    def validate(self, question: str) -> "SourceRequest":
        if self.origins is None:
            if self.directive is not None:
                raise ValueError("unrestricted sources cannot carry a source directive")
        elif not self.directive or not self.directive.strip() or self.directive not in question:
            raise ValueError("source restriction requires a verbatim current-request directive, not a topic inference")
        return self
