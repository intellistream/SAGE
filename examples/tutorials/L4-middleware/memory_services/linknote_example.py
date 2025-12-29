"""
LinknoteGraphService 完整使用示例

展示如何使用 Linknote 服务构建和查询笔记链接网络。
"""

from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    UnifiedCollection,
)
from sage.middleware.components.sage_mem.neuromem.services import (
    MemoryServiceRegistry,
)

# 导入服务类以触发装饰器注册


def basic_usage():
    """基础用法：创建笔记和链接"""
    print("=" * 60)
    print("1. 基础用法：创建笔记和链接")
    print("=" * 60)

    # 创建服务
    collection = UnifiedCollection("my_notes")
    service = MemoryServiceRegistry.create("linknote_graph", collection)

    # 插入笔记
    python_note = service.insert(
        "Python 是一种高级编程语言，以简洁和可读性著称。",
        metadata={"topic": "programming", "difficulty": "beginner"},
    )
    print(f"创建笔记: {python_note}")

    # 插入链接笔记
    oop_note = service.insert(
        "面向对象编程 (OOP) 是 Python 的核心特性之一。",
        links=[python_note],
        metadata={"topic": "programming", "difficulty": "intermediate"},
    )
    print(f"创建链接笔记: {oop_note}")

    classes_note = service.insert(
        "类和对象是 OOP 的基础概念。",
        links=[oop_note],
        metadata={"topic": "programming", "difficulty": "intermediate"},
    )
    print(f"创建链接笔记: {classes_note}")

    print(f"\n总笔记数: {collection.size()}")


def query_backlinks():
    """查询反向链接"""
    print("\n" + "=" * 60)
    print("2. 查询反向链接")
    print("=" * 60)

    collection = UnifiedCollection("backlinks_demo")
    service = MemoryServiceRegistry.create("linknote_graph", collection)

    # 创建笔记网络
    ai_note = service.insert("人工智能概述")
    ml_note = service.insert("机器学习", links=[ai_note])
    service.insert("深度学习", links=[ml_note])
    service.insert("自然语言处理", links=[ai_note])

    # 查询反向链接
    ai_backlinks = service.get_backlinks(ai_note)
    print(f"\n引用 AI 笔记的笔记数: {len(ai_backlinks)}")

    ml_backlinks = service.get_backlinks(ml_note)
    print(f"引用 ML 笔记的笔记数: {len(ml_backlinks)}")


def graph_traversal():
    """图遍历检索"""
    print("\n" + "=" * 60)
    print("3. 图遍历检索 (BFS vs DFS)")
    print("=" * 60)

    collection = UnifiedCollection("traversal_demo")
    service = MemoryServiceRegistry.create("linknote_graph", collection)

    # 创建笔记链
    root = service.insert("编程基础")
    python = service.insert("Python 编程", links=[root])
    java = service.insert("Java 编程", links=[root])
    service.insert("Django 框架", links=[python])
    service.insert("Flask 框架", links=[python])
    service.insert("Spring 框架", links=[java])

    # BFS 遍历
    bfs_results = service.retrieve(root, max_hops=2, method="bfs")
    print(f"\nBFS 遍历结果 (max_hops=2): {len(bfs_results)} 个笔记")
    for note in bfs_results:
        print(f"  - {note['text']}")

    # DFS 遍历
    dfs_results = service.retrieve(root, max_hops=2, method="dfs")
    print(f"\nDFS 遍历结果 (max_hops=2): {len(dfs_results)} 个笔记")
    for note in dfs_results:
        print(f"  - {note['text']}")


def neighbor_queries():
    """邻居节点查询"""
    print("\n" + "=" * 60)
    print("4. 邻居节点查询")
    print("=" * 60)

    collection = UnifiedCollection("neighbors_demo")
    service = MemoryServiceRegistry.create("linknote_graph", collection)

    # 创建笔记网络
    center = service.insert("中心笔记")
    note1 = service.insert("笔记 1", links=[center])
    service.insert("笔记 2", links=[center])
    service.insert("笔记 3", links=[note1])

    # 1-hop 邻居
    neighbors_1hop = service.get_neighbors(center, max_hops=1)
    print(f"\n1-hop 邻居: {len(neighbors_1hop)} 个")

    # 2-hop 邻居
    neighbors_2hop = service.get_neighbors(center, max_hops=2)
    print(f"2-hop 邻居: {len(neighbors_2hop)} 个")


def complex_network():
    """复杂笔记网络"""
    print("\n" + "=" * 60)
    print("5. 复杂笔记网络示例")
    print("=" * 60)

    collection = UnifiedCollection("complex_network")
    service = MemoryServiceRegistry.create("linknote_graph", collection)

    # 构建知识网络
    notes = {}

    # 编程语言
    notes["python"] = service.insert(
        "Python - 高级编程语言",
        metadata={"category": "language", "popularity": "high"},
    )
    notes["javascript"] = service.insert(
        "JavaScript - Web 编程语言",
        metadata={"category": "language", "popularity": "high"},
    )

    # 框架
    notes["django"] = service.insert(
        "Django - Python Web 框架",
        links=[notes["python"]],
        metadata={"category": "framework", "type": "web"},
    )
    notes["flask"] = service.insert(
        "Flask - Python 微框架",
        links=[notes["python"]],
        metadata={"category": "framework", "type": "web"},
    )
    notes["react"] = service.insert(
        "React - JavaScript UI 库",
        links=[notes["javascript"]],
        metadata={"category": "framework", "type": "frontend"},
    )

    # 概念
    notes["mvc"] = service.insert(
        "MVC 设计模式",
        links=[notes["django"], notes["flask"]],
        metadata={"category": "concept"},
    )
    notes["component"] = service.insert(
        "组件化开发",
        links=[notes["react"]],
        metadata={"category": "concept"},
    )

    print(f"\n创建了 {len(notes)} 个笔记")
    print(f"总链接数: {sum(len(service.get_backlinks(nid)) for nid in notes.values())}")

    # 查询 Python 相关的所有笔记
    python_related = service.retrieve(notes["python"], max_hops=2, method="bfs")
    print(f"\nPython 相关笔记 (2-hop): {len(python_related)} 个")
    for note in python_related:
        print(f"  - {note['text']}")


def metadata_filtering():
    """元数据过滤示例"""
    print("\n" + "=" * 60)
    print("6. 元数据过滤")
    print("=" * 60)

    collection = UnifiedCollection("metadata_demo")
    service = MemoryServiceRegistry.create("linknote_graph", collection)

    # 创建不同难度的笔记
    service.insert(
        "Python 基础语法",
        metadata={"difficulty": "beginner", "topic": "python"},
    )
    service.insert(
        "Python 装饰器",
        metadata={"difficulty": "intermediate", "topic": "python"},
    )
    service.insert(
        "Python 元类编程",
        metadata={"difficulty": "advanced", "topic": "python"},
    )

    # 通过 Collection 直接查询（未来可在 Service 层支持）
    all_notes = list(collection.raw_data.values())

    beginner_notes = [n for n in all_notes if n.get("metadata", {}).get("difficulty") == "beginner"]
    print(f"\n初级笔记数: {len(beginner_notes)}")

    advanced_notes = [n for n in all_notes if n.get("metadata", {}).get("difficulty") == "advanced"]
    print(f"高级笔记数: {len(advanced_notes)}")


def deletion_example():
    """删除操作示例"""
    print("\n" + "=" * 60)
    print("7. 删除操作")
    print("=" * 60)

    collection = UnifiedCollection("deletion_demo")
    service = MemoryServiceRegistry.create("linknote_graph", collection)

    # 创建笔记链
    note1 = service.insert("笔记 1")
    note2 = service.insert("笔记 2", links=[note1])
    note3 = service.insert("笔记 3", links=[note2])

    print(f"删除前: {collection.size()} 个笔记")

    # 删除中间节点
    service.delete(note2)
    print(f"删除后: {collection.size()} 个笔记")

    # 检查 note3 的反向链接（应该为空）
    backlinks = service.get_backlinks(note3)
    print(f"笔记 3 的反向链接数: {len(backlinks)}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("LinknoteGraphService 完整示例")
    print("=" * 60)

    basic_usage()
    query_backlinks()
    graph_traversal()
    neighbor_queries()
    complex_network()
    metadata_filtering()
    deletion_example()

    print("\n" + "=" * 60)
    print("示例运行完成！")
    print("=" * 60)
