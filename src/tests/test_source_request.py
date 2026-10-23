"""Source provenance must be explicit without widening identity ACLs."""

import pytest

from sage.runtime.source_request import SourceRequest


def test_unrestricted_topic_and_explicit_constraints():
    assert SourceRequest(None).validate("课题组主要研究哪些问题？").origins is None
    assert SourceRequest(("private",), "只使用私有知识库").validate("只使用私有知识库，介绍课题组")
    assert SourceRequest((), "不要检索任何来源").validate("不要检索任何来源，只改写我提供的文字")


@pytest.mark.parametrize("origins,directive", [(('private',), None), ((), None), (('wiki',), '不存在的指令'), (None, '课题组')])
def test_invented_or_missing_witness_is_rejected(origins, directive):
    with pytest.raises(ValueError):
        SourceRequest(origins, directive).validate("课题组主要研究哪些问题？")
