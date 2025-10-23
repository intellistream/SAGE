from sage.tools.templates import pipeline_blueprints


def test_match_blueprints_surface_relevant_candidate():
    requirements = {
        "goal": "构建客户支持知识助手",
        "description": "需要针对客服 ticket 自动回答",
    }

    matches = pipeline_blueprints.match_blueprints(requirements)
    assert matches, "should return at least one blueprint"
    top_blueprint, score = matches[0]
    assert top_blueprint.id == "rag-simple-demo"
    assert score > 0


def test_build_mock_pipeline_plan_uses_blueprint_components():
    blueprint = pipeline_blueprints.select_blueprint(
        {"goal": "运行hello world批处理示例"}
    )
    plan = pipeline_blueprints.build_pipeline_plan(
        blueprint, {"goal": "运行hello world批处理示例"}
    )

    assert plan["source"]["class"] == "examples.tutorials.hello_world.HelloBatch"
    classes = [stage["class"] for stage in plan["stages"]]
    assert "examples.tutorials.hello_world.UpperCaseMap" in classes
    assert plan["sink"]["class"] in {
        "examples.tutorials.hello_world.PrintSink",
        "sage.libs.io.sink.PrintSink",
    }
    notes = plan.get("notes") or []
    assert notes, "blueprint plan should include descriptive notes"


def test_render_blueprint_prompt_contains_metadata():
    blueprint = pipeline_blueprints.select_blueprint({"goal": "ops 告警分析"})
    snippet = pipeline_blueprints.render_blueprint_prompt(blueprint, 0.75)

    assert "Blueprint" in snippet
    assert blueprint.title in snippet
    assert blueprint.id in snippet
    assert "主要组件" in snippet


def test_multimodal_blueprint_references_real_components():
    candidates = [
        blueprint
        for blueprint in pipeline_blueprints.BLUEPRINT_LIBRARY
        if blueprint.id == "rag-multimodal-fusion"
    ]
    assert candidates, "multimodal blueprint should be registered"
    blueprint = candidates[0]
    assert blueprint.source.class_path == (
        "sage.benchmark.benchmark_rag.implementations.qa_multimodal_fusion.MultimodalQuestionSource"
    )
    stage_classes = [stage.class_path for stage in blueprint.stages]
    assert (
        "sage.benchmark.benchmark_rag.implementations.qa_multimodal_fusion.MultimodalFusionRetriever"
        in stage_classes
    )
    assert "sage.libs.rag.generator.OpenAIGenerator" in stage_classes
    assert blueprint.sink.class_path == "sage.libs.io.sink.TerminalSink"
