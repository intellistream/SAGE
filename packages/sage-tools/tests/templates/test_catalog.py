from sage.tools import templates


def test_template_ids_cover_examples():
    template_ids = set(templates.list_template_ids())
    assert {
        "rag-simple-demo",
        "hello-world-batch",
        "hello-world-log",
        "rag-multimodal-fusion",
    }.issubset(template_ids)


def test_multimodal_template_pipeline_plan_uses_real_components():
    template = templates.get_template("rag-multimodal-fusion")
    plan = template.pipeline_plan()

    source_class = plan["source"]["class"]
    stage_classes = [stage["class"] for stage in plan["stages"]]

    assert source_class == "sage_benchmark.rag.qa_multimodal_fusion.MultimodalQuestionSource"
    assert (
        "sage_benchmark.rag.qa_multimodal_fusion.MultimodalFusionRetriever" in stage_classes
    )
    assert "sage.libs.rag.generator.OpenAIGenerator" in stage_classes
    assert plan["sink"]["class"] == "sage.libs.io_utils.sink.TerminalSink"


def test_match_templates_scores_chinese_support_requests():
    matches = templates.match_templates(
        {
            "goal": "构建客户支持知识助手",
            "description": "需要针对客服 ticket 自动回答",
        },
        top_k=2,
    )

    assert matches, "模板匹配应返回候选"
    assert matches[0].template.id == "rag-simple-demo"
    assert matches[0].score > 0


def test_render_prompt_mentions_example_path():
    template = templates.get_template("hello-world-batch")
    snippet = template.render_prompt(0.5)

    assert template.example_path in snippet
    assert template.title in snippet
    assert "默认Pipeline" in snippet
