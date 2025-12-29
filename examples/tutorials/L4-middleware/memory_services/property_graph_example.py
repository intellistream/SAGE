"""
PropertyGraphService 完整使用示例

展示如何使用 PropertyGraph 服务构建和查询知识图谱。
"""

from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    UnifiedCollection,
)
from sage.middleware.components.sage_mem.neuromem.services import (
    MemoryServiceRegistry,
)

# 导入服务类以触发装饰器注册


def basic_usage():
    """基础用法：创建实体和关系"""
    print("=" * 60)
    print("1. 基础用法：创建实体和关系")
    print("=" * 60)

    # 创建服务
    collection = UnifiedCollection("knowledge_graph")
    service = MemoryServiceRegistry.create("property_graph", collection)

    # 插入实体
    python = service.insert(
        "Python",
        metadata={"entity_type": "Language", "year": 1991, "paradigm": "multi-paradigm"},
    )
    print(f"创建实体: Python (ID: {python})")

    guido = service.insert(
        "Guido van Rossum",
        metadata={"entity_type": "Person", "nationality": "Dutch"},
    )
    print(f"创建实体: Guido van Rossum (ID: {guido})")

    # 添加关系
    service.add_relationship(guido, python, "CREATED", properties={"year": 1991})
    print(f"添加关系: {guido} -[CREATED]-> {python}")

    print(f"\n总实体数: {collection.size()}")


def insert_with_relationships():
    """插入时同时创建关系"""
    print("\n" + "=" * 60)
    print("2. 插入时创建关系")
    print("=" * 60)

    collection = UnifiedCollection("insert_with_rel")
    service = MemoryServiceRegistry.create("property_graph", collection)

    # 先创建目标实体
    apple = service.insert("Apple Inc.", metadata={"entity_type": "Company"})
    print(f"创建公司: {apple}")

    # 插入时同时创建多个关系
    steve = service.insert(
        "Steve Jobs",
        metadata={"entity_type": "Person"},
        relationships=[
            (apple, "FOUNDED", {"year": 1976}),
            (apple, "CEO", {"from": 1997, "to": 2011}),
        ],
    )
    print(f"创建人物并添加关系: {steve}")

    tim = service.insert(
        "Tim Cook",
        metadata={"entity_type": "Person"},
        relationships=[(apple, "CEO", {"from": 2011})],
    )
    print(f"创建人物并添加关系: {tim}")


def query_related_entities():
    """查询相关实体"""
    print("\n" + "=" * 60)
    print("3. 查询相关实体（双向查询）")
    print("=" * 60)

    collection = UnifiedCollection("query_demo")
    service = MemoryServiceRegistry.create("property_graph", collection)

    # 构建知识图谱
    company = service.insert("TechCorp", metadata={"entity_type": "Company"})
    service.insert(
        "Alice",
        metadata={"entity_type": "Person"},
        relationships=[(company, "WORKS_AT", {"position": "Engineer"})],
    )
    service.insert(
        "Bob",
        metadata={"entity_type": "Person"},
        relationships=[(company, "WORKS_AT", {"position": "Manager"})],
    )
    product = service.insert("Product X", metadata={"entity_type": "Product"})
    service.add_relationship(product, company, "MANUFACTURED_BY")

    # 查询公司的相关实体（双向，默认）
    print("\n双向查询 (direction='both'):")
    related = service.get_related_entities(company)
    for entity in related:
        print(f"  - {entity['text']} ({entity['metadata']['entity_type']})")

    # 只查询入边（谁指向公司）
    print("\n入边查询 (direction='incoming'):")
    incoming = service.get_related_entities(company, direction="incoming")
    for entity in incoming:
        print(f"  - {entity['text']} ({entity['metadata']['entity_type']})")

    # 只查询出边（公司指向谁）
    print("\n出边查询 (direction='outgoing'):")
    outgoing = service.get_related_entities(company, direction="outgoing")
    for entity in outgoing:
        print(f"  - {entity['text']} ({entity['metadata']['entity_type']})")


def retrieve_by_metadata():
    """按元数据检索实体"""
    print("\n" + "=" * 60)
    print("4. 按元数据检索实体")
    print("=" * 60)

    collection = UnifiedCollection("retrieve_demo")
    service = MemoryServiceRegistry.create("property_graph", collection)

    # 插入不同类型的实体
    service.insert("Python", metadata={"entity_type": "Language", "year": 1991})
    service.insert("Java", metadata={"entity_type": "Language", "year": 1995})
    service.insert("Alice", metadata={"entity_type": "Person", "occupation": "Engineer"})
    service.insert("Bob", metadata={"entity_type": "Person", "occupation": "Manager"})
    service.insert("TechCorp", metadata={"entity_type": "Company"})

    # 按类型检索
    print("\n检索所有编程语言:")
    languages = service.retrieve(query="", entity_type="Language")
    for lang in languages:
        print(f"  - {lang['text']} ({lang['metadata']['year']})")

    print("\n检索所有人物:")
    persons = service.retrieve(query="", entity_type="Person")
    for person in persons:
        print(f"  - {person['text']} ({person['metadata']['occupation']})")

    # 多条件过滤
    print("\n检索所有工程师:")
    engineers = service.retrieve(
        query="", entity_type="Person", property_filters={"occupation": "Engineer"}
    )
    for eng in engineers:
        print(f"  - {eng['text']}")


def complex_knowledge_graph():
    """复杂知识图谱示例"""
    print("\n" + "=" * 60)
    print("5. 复杂知识图谱构建")
    print("=" * 60)

    collection = UnifiedCollection("complex_kg")
    service = MemoryServiceRegistry.create("property_graph", collection)

    # 构建技术栈知识图谱
    entities = {}

    # 编程语言
    entities["python"] = service.insert(
        "Python", metadata={"entity_type": "Language", "type": "interpreted"}
    )
    entities["javascript"] = service.insert(
        "JavaScript", metadata={"entity_type": "Language", "type": "interpreted"}
    )

    # 框架
    entities["django"] = service.insert(
        "Django",
        metadata={"entity_type": "Framework", "category": "web"},
        relationships=[(entities["python"], "WRITTEN_IN", {})],
    )
    entities["react"] = service.insert(
        "React",
        metadata={"entity_type": "Framework", "category": "frontend"},
        relationships=[(entities["javascript"], "WRITTEN_IN", {})],
    )

    # 公司
    entities["meta"] = service.insert("Meta", metadata={"entity_type": "Company"})
    service.add_relationship(entities["react"], entities["meta"], "DEVELOPED_BY")

    # 概念
    entities["spa"] = service.insert("Single Page Application", metadata={"entity_type": "Concept"})
    service.add_relationship(entities["react"], entities["spa"], "ENABLES")

    print(f"\n创建了 {len(entities)} 个实体")

    # 多层关系遍历
    print("\n从 Python 出发的关系链:")
    python_related = service.get_related_entities(entities["python"], direction="incoming")
    for framework in python_related:
        print(f"  框架: {framework['text']}")

    print("\n从 React 出发的关系链:")
    react_related = service.get_related_entities(entities["react"])
    for related in react_related:
        print(f"  相关: {related['text']} ({related['metadata']['entity_type']})")


def multi_hop_traversal():
    """多跳关系遍历"""
    print("\n" + "=" * 60)
    print("6. 多跳关系遍历")
    print("=" * 60)

    collection = UnifiedCollection("multi_hop")
    service = MemoryServiceRegistry.create("property_graph", collection)

    # 构建链式关系: Company → Product → Technology → Feature
    company = service.insert("TechCorp", metadata={"entity_type": "Company"})
    product = service.insert(
        "Smart Device",
        metadata={"entity_type": "Product"},
        relationships=[(company, "MANUFACTURED_BY", {})],
    )
    tech = service.insert(
        "AI Chip",
        metadata={"entity_type": "Technology"},
        relationships=[(product, "USES", {})],
    )
    service.insert(
        "Voice Recognition",
        metadata={"entity_type": "Feature"},
        relationships=[(tech, "ENABLES", {})],
    )

    # 1-hop: Company → Product
    print("\n从公司出发 (1-hop):")
    hop1 = service.get_related_entities(company, direction="incoming")
    for item in hop1:
        print(f"  - {item['text']}")

    # 2-hop: Company → Product → Technology
    print("\n从公司出发 (2-hop):")
    for prod in hop1:
        hop2 = service.get_related_entities(prod["id"], direction="outgoing")
        for tech in hop2:
            print(f"  - {tech['text']}")


def relationship_properties():
    """关系属性示例"""
    print("\n" + "=" * 60)
    print("7. 关系属性")
    print("=" * 60)

    collection = UnifiedCollection("rel_props")
    service = MemoryServiceRegistry.create("property_graph", collection)

    # 创建实体
    person = service.insert("Alice", metadata={"entity_type": "Person"})
    company = service.insert("TechCorp", metadata={"entity_type": "Company"})

    # 添加带属性的关系
    service.add_relationship(
        person,
        company,
        "WORKS_AT",
        properties={
            "position": "Senior Engineer",
            "department": "AI Research",
            "start_year": 2020,
            "salary_range": "high",
        },
    )

    print("创建了带属性的关系:")
    print("  Alice -[WORKS_AT]-> TechCorp")
    print("  属性:")
    print("    - position: Senior Engineer")
    print("    - department: AI Research")
    print("    - start_year: 2020")
    print("    - salary_range: high")

    # 注意：当前版本不支持直接查询边属性
    # 这是未来的扩展方向


def deletion_example():
    """删除操作示例"""
    print("\n" + "=" * 60)
    print("8. 删除操作")
    print("=" * 60)

    collection = UnifiedCollection("deletion_demo")
    service = MemoryServiceRegistry.create("property_graph", collection)

    # 创建实体和关系
    company = service.insert("Company A", metadata={"entity_type": "Company"})
    person1 = service.insert(
        "Person 1",
        metadata={"entity_type": "Person"},
        relationships=[(company, "WORKS_AT", {})],
    )
    service.insert(
        "Person 2",
        metadata={"entity_type": "Person"},
        relationships=[(company, "WORKS_AT", {})],
    )

    print(f"删除前: {collection.size()} 个实体")

    # 删除公司（关系也会被删除）
    service.delete(company)
    print(f"删除后: {collection.size()} 个实体")

    # 检查人物的关系（应该为空）
    related = service.get_related_entities(person1)
    print(f"Person 1 的相关实体数: {len(related)}")


def edge_cases():
    """边界情况处理"""
    print("\n" + "=" * 60)
    print("9. 边界情况处理")
    print("=" * 60)

    collection = UnifiedCollection("edge_cases")
    service = MemoryServiceRegistry.create("property_graph", collection)

    # 自环（会被过滤）
    entity = service.insert("Self-ref Entity")
    service.add_relationship(entity, entity, "SELF_RELATION")

    related = service.get_related_entities(entity)
    print(f"自环实体的相关实体数: {len(related)} (应该为0)")

    # 不存在的实体
    nonexistent_related = service.get_related_entities("nonexistent_id")
    print(f"不存在实体的相关实体数: {len(nonexistent_related)}")

    # 无效关系目标
    valid_entity = service.insert("Valid Entity")
    result = service.add_relationship(valid_entity, "nonexistent_target", "INVALID")
    print(f"添加无效关系的结果: {result} (应该为False)")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PropertyGraphService 完整示例")
    print("=" * 60)

    basic_usage()
    insert_with_relationships()
    query_related_entities()
    retrieve_by_metadata()
    complex_knowledge_graph()
    multi_hop_traversal()
    relationship_properties()
    deletion_example()
    edge_cases()

    print("\n" + "=" * 60)
    print("示例运行完成！")
    print("=" * 60)
