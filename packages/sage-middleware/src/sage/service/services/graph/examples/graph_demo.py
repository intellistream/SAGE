"""
Graph Service 使用示例
展示如何使用Graph微服务进行知识图谱构建和查询
"""
from sage.core.api.local_environment import LocalEnvironment
from sage.service.graph import create_graph_service_factory


def test_graph_service():
    """测试Graph服务基本功能"""
    print("🚀 Graph Service Demo")
    print("=" * 50)
    
    # 创建环境
    env = LocalEnvironment("graph_service_demo")
    
    # 注册Graph服务 - 内存后端
    graph_factory = create_graph_service_factory(
        service_name="demo_graph_service",
        backend_type="memory",
        max_nodes=10000,
        max_relationships=50000
    )
    env.register_service("demo_graph_service", graph_factory)
    
    print("✅ Graph Service registered with memory backend")
    print("   - Max nodes: 10,000")
    print("   - Max relationships: 50,000")
    
    # 模拟知识图谱构建
    print("\n📝 Knowledge Graph Operations Demo:")
    
    # 创建实体节点
    entities = [
        {"id": "person_1", "labels": ["Person"], "properties": {"name": "Alice", "age": 30}},
        {"id": "person_2", "labels": ["Person"], "properties": {"name": "Bob", "age": 25}},
        {"id": "company_1", "labels": ["Company"], "properties": {"name": "TechCorp", "founded": 2010}},
        {"id": "skill_1", "labels": ["Skill"], "properties": {"name": "Python", "category": "Programming"}},
        {"id": "skill_2", "labels": ["Skill"], "properties": {"name": "AI", "category": "Technology"}}
    ]
    
    print(f"  add_nodes({len(entities)} entities) -> ✅ Added 5 nodes")
    for entity in entities:
        print(f"    - {entity['labels'][0]}: {entity['properties']['name']}")
    
    # 创建关系
    relationships = [
        {"from_node": "person_1", "to_node": "company_1", "rel_type": "WORKS_AT", "properties": {"since": 2020}},
        {"from_node": "person_2", "to_node": "company_1", "rel_type": "WORKS_AT", "properties": {"since": 2021}},
        {"from_node": "person_1", "to_node": "skill_1", "rel_type": "HAS_SKILL", "properties": {"level": "Expert"}},
        {"from_node": "person_1", "to_node": "skill_2", "rel_type": "HAS_SKILL", "properties": {"level": "Intermediate"}},
        {"from_node": "person_2", "to_node": "skill_1", "rel_type": "HAS_SKILL", "properties": {"level": "Beginner"}},
        {"from_node": "person_1", "to_node": "person_2", "rel_type": "COLLEAGUE", "properties": {"since": 2021}}
    ]
    
    print(f"  add_relationships({len(relationships)} relations) -> ✅ Added 6 relationships")
    for rel in relationships:
        print(f"    - {rel['from_node']} --[{rel['rel_type']}]--> {rel['to_node']}")
    
    # 图查询示例
    print("\n🔍 Graph Query Examples:")
    
    queries = [
        {
            "name": "查找Alice的同事",
            "description": "MATCH (alice:Person {name: 'Alice'})-[:COLLEAGUE]->(colleague) RETURN colleague",
            "result": "Bob"
        },
        {
            "name": "查找TechCorp的员工",
            "description": "MATCH (person:Person)-[:WORKS_AT]->(company:Company {name: 'TechCorp'}) RETURN person",
            "result": "Alice, Bob"
        },
        {
            "name": "查找Python专家",
            "description": "MATCH (person:Person)-[r:HAS_SKILL]->(skill:Skill {name: 'Python'}) WHERE r.level = 'Expert' RETURN person",
            "result": "Alice"
        },
        {
            "name": "查找Alice的技能图谱",
            "description": "MATCH (alice:Person {name: 'Alice'})-[:HAS_SKILL]->(skill:Skill) RETURN skill",
            "result": "Python (Expert), AI (Intermediate)"
        }
    ]
    
    for query in queries:
        print(f"  📊 {query['name']}:")
        print(f"      Query: {query['description']}")
        print(f"      Result: {query['result']}")
    
    print("\n💡 Graph Service Features:")
    print("   - 知识图谱构建和管理")
    print("   - 复杂图查询")
    print("   - 图算法 (路径查找、社区发现)")
    print("   - 实体关系推理")
    print("   - 图可视化支持")


def test_graph_algorithms():
    """演示图算法功能"""
    print("\n🧮 Graph Algorithms:")
    
    algorithms = [
        {
            "name": "最短路径",
            "function": "shortest_path(person_1, person_2)",
            "description": "查找两个实体间的最短关系路径",
            "result": "person_1 -> company_1 <- person_2"
        },
        {
            "name": "邻居发现",
            "function": "get_neighbors(person_1, depth=2)",
            "description": "查找指定深度内的所有相关实体",
            "result": "company_1, skill_1, skill_2, person_2"
        },
        {
            "name": "社区检测",
            "function": "detect_communities()",
            "description": "发现图中的紧密连接社区",
            "result": "Community 1: [person_1, person_2, company_1]"
        },
        {
            "name": "中心性分析",
            "function": "centrality_analysis()",
            "description": "分析节点在图中的重要性",
            "result": "company_1: highest centrality (连接最多)"
        }
    ]
    
    for algo in algorithms:
        print(f"  🔄 {algo['name']}: {algo['description']}")
        print(f"      调用: {algo['function']}")
        print(f"      结果: {algo['result']}")


def test_graph_applications():
    """演示Graph服务的应用场景"""
    print("\n🎯 Graph Service Applications:")
    
    applications = [
        {
            "name": "推荐系统",
            "scenario": "基于用户-物品-属性图进行协同过滤推荐",
            "entities": ["User", "Item", "Category", "Tag"],
            "relationships": ["LIKES", "BELONGS_TO", "HAS_TAG", "SIMILAR_TO"]
        },
        {
            "name": "知识问答",
            "scenario": "构建领域知识图谱，支持复杂问答推理",
            "entities": ["Concept", "Entity", "Relation", "Attribute"],
            "relationships": ["IS_A", "PART_OF", "RELATED_TO", "HAS_PROPERTY"]
        },
        {
            "name": "社交网络分析",
            "scenario": "分析用户关系，发现社区和影响者",
            "entities": ["User", "Post", "Topic", "Event"],
            "relationships": ["FOLLOWS", "POSTS", "MENTIONS", "ATTENDS"]
        },
        {
            "name": "欺诈检测",
            "scenario": "通过异常图模式检测可疑行为",
            "entities": ["Account", "Transaction", "Device", "Location"],
            "relationships": ["TRANSFERS", "USES", "LOCATED_AT", "LINKED_TO"]
        }
    ]
    
    for app in applications:
        print(f"  📈 {app['name']}: {app['scenario']}")
        print(f"      实体类型: {', '.join(app['entities'])}")
        print(f"      关系类型: {', '.join(app['relationships'])}")


if __name__ == "__main__":
    test_graph_service()
    test_graph_algorithms()
    test_graph_applications()
    print("\n🎯 Graph Service demo completed!")
