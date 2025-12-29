"""
混合知识库示例

展示如何同时使用 LinknoteGraphService 和 PropertyGraphService
构建混合知识管理系统。
"""

from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    UnifiedCollection,
)
from sage.middleware.components.sage_mem.neuromem.services import (
    MemoryServiceRegistry,
)

# 导入服务类以触发装饰器注册


def hybrid_knowledge_base_demo():
    """混合知识库演示"""
    print("=" * 60)
    print("混合知识库：笔记 + 知识图谱")
    print("=" * 60)

    # 共享底层存储
    shared_collection = UnifiedCollection("hybrid_kb")

    # 创建两种服务
    notes = MemoryServiceRegistry.create("linknote_graph", shared_collection)
    entities = MemoryServiceRegistry.create("property_graph", shared_collection)

    print("\n1. 笔记层：记录学习笔记")
    print("-" * 60)

    # 使用 Linknote 管理学习笔记
    python_note = notes.insert(
        "Python 编程语言学习笔记 - 2025年1月",
        metadata={"type": "note", "category": "learning", "date": "2025-01-01"},
    )
    print("创建笔记: Python 学习笔记")

    oop_note = notes.insert(
        "面向对象编程概念和实践",
        links=[python_note],
        metadata={"type": "note", "category": "learning"},
    )
    print("创建笔记: OOP 概念（链接到 Python 笔记）")

    notes.insert(
        "Python 装饰器深入理解",
        links=[python_note, oop_note],
        metadata={"type": "note", "category": "advanced"},
    )
    print("创建笔记: 装饰器（链接到 Python 和 OOP）")

    print("\n2. 知识图谱层：构建实体关系")
    print("-" * 60)

    # 使用 PropertyGraph 管理结构化知识
    python_entity = entities.insert(
        "Python",
        metadata={
            "type": "entity",
            "entity_type": "Language",
            "year": 1991,
            "paradigm": "multi-paradigm",
        },
    )
    print("创建实体: Python 语言")

    entities.insert(
        "Guido van Rossum",
        metadata={"type": "entity", "entity_type": "Person", "nationality": "Dutch"},
        relationships=[(python_entity, "CREATED", {"year": 1991})],
    )
    print("创建实体: Guido van Rossum（创建者关系）")

    entities.insert(
        "Django",
        metadata={"type": "entity", "entity_type": "Framework", "category": "web"},
        relationships=[(python_entity, "WRITTEN_IN", {})],
    )
    print("创建实体: Django 框架（使用 Python）")

    print("\n3. 数据统计")
    print("-" * 60)
    print(f"共享 Collection 总数据量: {shared_collection.size()}")

    # 统计不同类型的数据
    all_data = list(shared_collection.raw_data.values())
    note_count = sum(1 for d in all_data if d.get("metadata", {}).get("type") == "note")
    entity_count = sum(1 for d in all_data if d.get("metadata", {}).get("type") == "entity")

    print(f"  - 笔记数量: {note_count}")
    print(f"  - 实体数量: {entity_count}")

    print("\n4. 跨层查询")
    print("-" * 60)

    # 笔记层查询
    python_backlinks = notes.get_backlinks(python_note)
    print(f"Python 笔记的反向链接数: {len(python_backlinks)}")

    # 实体层查询
    python_related = entities.get_related_entities(python_entity)
    print(f"Python 实体的相关实体数: {len(python_related)}")
    for rel in python_related:
        print(f"  - {rel['text']} ({rel['metadata']['entity_type']})")


def research_workflow_demo():
    """研究工作流示例"""
    print("\n" + "=" * 60)
    print("研究工作流：论文 + 概念图谱")
    print("=" * 60)

    collection = UnifiedCollection("research_kb")
    notes = MemoryServiceRegistry.create("linknote_graph", collection)
    concepts = MemoryServiceRegistry.create("property_graph", collection)

    print("\n1. 阅读论文并记录笔记")
    print("-" * 60)

    # 论文笔记
    paper1 = notes.insert(
        "论文笔记: Attention Is All You Need (2017)",
        metadata={
            "type": "paper_note",
            "authors": "Vaswani et al.",
            "year": 2017,
        },
    )
    print("记录论文笔记: Transformer 论文")

    notes.insert(
        "论文笔记: BERT (2018)",
        links=[paper1],
        metadata={
            "type": "paper_note",
            "authors": "Devlin et al.",
            "year": 2018,
        },
    )
    print("记录论文笔记: BERT 论文（引用 Transformer）")

    notes.insert(
        "论文笔记: GPT-3 (2020)",
        links=[paper1],
        metadata={
            "type": "paper_note",
            "authors": "Brown et al.",
            "year": 2020,
        },
    )
    print("记录论文笔记: GPT-3 论文（引用 Transformer）")

    print("\n2. 提取核心概念构建知识图谱")
    print("-" * 60)

    # 核心概念
    transformer = concepts.insert(
        "Transformer",
        metadata={"type": "concept", "concept_type": "Architecture", "year": 2017},
    )
    print("提取概念: Transformer 架构")

    concepts.insert(
        "Self-Attention",
        metadata={"type": "concept", "concept_type": "Mechanism"},
        relationships=[(transformer, "CORE_COMPONENT_OF", {})],
    )
    print("提取概念: Self-Attention（Transformer 核心组件）")

    bert = concepts.insert(
        "BERT",
        metadata={"type": "concept", "concept_type": "Model", "year": 2018},
        relationships=[(transformer, "BASED_ON", {})],
    )
    print("提取概念: BERT（基于 Transformer）")

    gpt = concepts.insert(
        "GPT",
        metadata={"type": "concept", "concept_type": "Model", "year": 2020},
        relationships=[(transformer, "BASED_ON", {})],
    )
    print("提取概念: GPT（基于 Transformer）")

    # 应用领域
    nlp = concepts.insert(
        "Natural Language Processing",
        metadata={"type": "concept", "concept_type": "Field"},
    )
    concepts.add_relationship(bert, nlp, "APPLIED_TO")
    concepts.add_relationship(gpt, nlp, "APPLIED_TO")
    print("关联领域: NLP")

    print("\n3. 知识发现")
    print("-" * 60)

    # 通过笔记链接发现论文引用关系
    transformer_paper_refs = notes.get_backlinks(paper1)
    print(f"引用 Transformer 论文的数量: {len(transformer_paper_refs)}")

    # 通过知识图谱发现概念关系
    transformer_based_models = concepts.get_related_entities(transformer, direction="incoming")
    print("基于 Transformer 的模型:")
    for model in transformer_based_models:
        year = model["metadata"].get("year", "未知")
        print(f"  - {model['text']} ({year})")

    # 发现共同应用领域
    nlp_models = concepts.get_related_entities(nlp, direction="incoming")
    print("\nNLP 领域的模型:")
    for model in nlp_models:
        print(f"  - {model['text']}")


def project_management_demo():
    """项目管理示例"""
    print("\n" + "=" * 60)
    print("项目管理：任务 + 资源图谱")
    print("=" * 60)

    collection = UnifiedCollection("project_kb")
    tasks = MemoryServiceRegistry.create("linknote_graph", collection)
    resources = MemoryServiceRegistry.create("property_graph", collection)

    print("\n1. 任务管理（笔记层）")
    print("-" * 60)

    # 项目任务
    project = tasks.insert(
        "项目: AI 聊天助手开发",
        metadata={"type": "task", "status": "in_progress", "priority": "high"},
    )

    task1 = tasks.insert(
        "任务 1: 数据收集和清洗",
        links=[project],
        metadata={"type": "task", "status": "completed"},
    )

    tasks.insert(
        "任务 2: 模型训练",
        links=[project, task1],
        metadata={"type": "task", "status": "in_progress"},
    )

    tasks.insert(
        "任务 3: 前端开发",
        links=[project],
        metadata={"type": "task", "status": "not_started"},
    )

    print(f"创建项目和 {tasks.get_backlinks(project).__len__()} 个任务")

    print("\n2. 资源管理（知识图谱层）")
    print("-" * 60)

    # 团队成员
    alice = resources.insert(
        "Alice", metadata={"type": "resource", "resource_type": "Person", "role": "ML Engineer"}
    )

    bob = resources.insert(
        "Bob",
        metadata={"type": "resource", "resource_type": "Person", "role": "Frontend Developer"},
    )

    # 技术栈
    pytorch = resources.insert(
        "PyTorch", metadata={"type": "resource", "resource_type": "Technology"}
    )
    react = resources.insert("React", metadata={"type": "resource", "resource_type": "Technology"})

    # 资源关系
    resources.add_relationship(alice, pytorch, "SKILLED_IN")
    resources.add_relationship(bob, react, "SKILLED_IN")

    print(f"创建 {collection.size() - 4} 个资源实体")

    print("\n3. 资源分配查询")
    print("-" * 60)

    # 查找 PyTorch 专家
    pytorch_experts = resources.get_related_entities(pytorch, direction="incoming")
    print("PyTorch 专家:")
    for expert in pytorch_experts:
        print(f"  - {expert['text']} ({expert['metadata']['role']})")

    # 查找 React 开发者
    react_devs = resources.get_related_entities(react, direction="incoming")
    print("React 开发者:")
    for dev in react_devs:
        print(f"  - {dev['text']} ({dev['metadata']['role']})")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("混合知识库完整示例")
    print("=" * 60)

    hybrid_knowledge_base_demo()
    research_workflow_demo()
    project_management_demo()

    print("\n" + "=" * 60)
    print("示例运行完成！")
    print("=" * 60)
