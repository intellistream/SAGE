"""
Unit tests for PropertyGraphService

测试范围:
- Service 初始化和索引创建
- 插入实体节点和关系
- 按属性检索实体
- 获取相关实体
"""

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection import UnifiedCollection
from sage.middleware.components.sage_mem.neuromem.services.hierarchical import (
    PropertyGraphService,
)
from sage.middleware.components.sage_mem.neuromem.services import MemoryServiceRegistry


class TestPropertyGraphInitialization:
    """测试初始化"""

    def test_service_creation(self):
        """测试 Service 创建"""
        collection = UnifiedCollection("entities")
        service = PropertyGraphService(collection)

        assert service.collection.name == "entities"
        assert "property_graph" in service.collection.indexes

    def test_service_via_registry(self):
        """测试通过注册表创建 Service"""
        collection = UnifiedCollection("entities")
        service = MemoryServiceRegistry.create("property_graph", collection)

        assert isinstance(service, PropertyGraphService)
        assert "property_graph" in service.collection.indexes


class TestBasicOperations:
    """测试基础操作"""

    @pytest.fixture
    def service(self):
        """创建 Service 实例"""
        collection = UnifiedCollection("entities")
        return PropertyGraphService(collection)

    def test_insert_entity_simple(self, service):
        """测试插入简单实体"""
        entity_id = service.insert("Apple Inc.")

        assert entity_id is not None
        entity = service.get(entity_id)
        assert entity is not None
        assert entity["text"] == "Apple Inc."

    def test_insert_entity_with_properties(self, service):
        """测试插入带属性的实体"""
        entity_id = service.insert(
            "Apple Inc.",
            metadata={
                "entity_type": "Company",
                "properties": {"founded": 1976, "industry": "Technology"},
            },
        )

        entity = service.get(entity_id)
        assert entity["metadata"]["entity_type"] == "Company"
        assert entity["metadata"]["properties"]["founded"] == 1976

    def test_insert_entity_with_relationships(self, service):
        """测试插入带关系的实体"""
        # 先插入目标实体
        company_id = service.insert(
            "Apple Inc.", metadata={"entity_type": "Company"}
        )

        # 插入源实体并建立关系
        person_id = service.insert(
            "Steve Jobs",
            metadata={"entity_type": "Person"},
            relationships=[
                (company_id, "FOUNDED", {"year": 1976}),
                (company_id, "CEO", {"from": 1997, "to": 2011}),
            ],
        )

        assert person_id is not None
        # 验证实体已插入
        person = service.get(person_id)
        assert person is not None


class TestRelationshipManagement:
    """测试关系管理"""

    @pytest.fixture
    def service_with_entities(self):
        """创建有实体的 Service"""
        collection = UnifiedCollection("entities")
        service = PropertyGraphService(collection)

        # 创建实体
        company = service.insert(
            "Google", metadata={"entity_type": "Company"}
        )
        person = service.insert(
            "Larry Page", metadata={"entity_type": "Person"}
        )

        return service, {"company": company, "person": person}

    def test_add_relationship(self, service_with_entities):
        """测试添加关系"""
        service, entities = service_with_entities

        result = service.add_relationship(
            source_id=entities["person"],
            target_id=entities["company"],
            relation_type="FOUNDED",
            properties={"year": 1998},
        )

        assert result is True

    def test_add_relationship_with_properties(self, service_with_entities):
        """测试添加带属性的关系"""
        service, entities = service_with_entities

        result = service.add_relationship(
            source_id=entities["person"],
            target_id=entities["company"],
            relation_type="WORKS_AT",
            properties={"since": 1998, "position": "CEO"},
        )

        assert result is True

    def test_add_relationship_invalid_source(self, service_with_entities):
        """测试添加关系 (源实体不存在)"""
        service, entities = service_with_entities

        result = service.add_relationship(
            source_id="nonexistent_id",
            target_id=entities["company"],
            relation_type="FOUNDED",
        )

        assert result is False

    def test_add_relationship_invalid_target(self, service_with_entities):
        """测试添加关系 (目标实体不存在)"""
        service, entities = service_with_entities

        result = service.add_relationship(
            source_id=entities["person"],
            target_id="nonexistent_id",
            relation_type="FOUNDED",
        )

        assert result is False


class TestRetrieval:
    """测试检索功能"""

    @pytest.fixture
    def service_with_data(self):
        """创建有数据的 Service"""
        collection = UnifiedCollection("entities")
        service = PropertyGraphService(collection)

        # 创建多个实体
        apple = service.insert(
            "Apple Inc.",
            metadata={
                "entity_type": "Company",
                "properties": {"industry": "Technology", "founded": 1976},
            },
        )
        google = service.insert(
            "Google",
            metadata={
                "entity_type": "Company",
                "properties": {"industry": "Technology", "founded": 1998},
            },
        )
        walmart = service.insert(
            "Walmart",
            metadata={
                "entity_type": "Company",
                "properties": {"industry": "Retail", "founded": 1962},
            },
        )

        return service, {"apple": apple, "google": google, "walmart": walmart}

    def test_retrieve_by_entity_type(self, service_with_data):
        """测试按实体类型检索"""
        service, _ = service_with_data

        companies = service.retrieve("", top_k=10, entity_type="Company")

        assert len(companies) == 3
        assert all(e["metadata"]["entity_type"] == "Company" for e in companies)

    def test_retrieve_by_property_filter(self, service_with_data):
        """测试按属性过滤检索"""
        service, _ = service_with_data

        tech_companies = service.retrieve(
            "",
            top_k=10,
            entity_type="Company",
            property_filters={"industry": "Technology"},
        )

        assert len(tech_companies) == 2  # Apple and Google
        assert all(
            e["metadata"]["properties"]["industry"] == "Technology"
            for e in tech_companies
        )

    def test_retrieve_by_specific_property(self, service_with_data):
        """测试按特定属性值检索"""
        service, _ = service_with_data

        companies_1998 = service.retrieve(
            "",
            top_k=10,
            entity_type="Company",
            property_filters={"founded": 1998},
        )

        assert len(companies_1998) == 1  # Only Google
        assert companies_1998[0]["text"] == "Google"

    def test_retrieve_by_id(self, service_with_data):
        """测试按 ID 检索"""
        service, entities = service_with_data

        result = service.retrieve(entities["apple"], top_k=1)

        assert len(result) == 1
        assert result[0]["text"] == "Apple Inc."


class TestRelatedEntities:
    """测试相关实体查询"""

    @pytest.fixture
    def service_with_graph(self):
        """创建有关系图的 Service"""
        collection = UnifiedCollection("entities")
        service = PropertyGraphService(collection)

        # 创建实体和关系:
        # Steve Jobs -FOUNDED-> Apple
        # Steve Jobs -CEO-> Apple
        # Tim Cook -CEO-> Apple
        apple = service.insert("Apple Inc.", metadata={"entity_type": "Company"})
        steve = service.insert(
            "Steve Jobs",
            metadata={"entity_type": "Person"},
            relationships=[
                (apple, "FOUNDED", {"year": 1976}),
                (apple, "CEO", {"from": 1997, "to": 2011}),
            ],
        )
        tim = service.insert(
            "Tim Cook",
            metadata={"entity_type": "Person"},
            relationships=[(apple, "CEO", {"from": 2011})],
        )

        return service, {"apple": apple, "steve": steve, "tim": tim}

    def test_get_related_entities_outgoing(self, service_with_graph):
        """测试获取出边相关实体"""
        service, entities = service_with_graph

        # Steve Jobs 的出边 (FOUNDED/CEO -> Apple)
        related = service.get_related_entities(
            entities["steve"], direction="outgoing"
        )

        # 应该能找到 Apple
        related_ids = [e["id"] for e in related]
        assert entities["apple"] in related_ids

    def test_get_related_entities_multiple_relations(self, service_with_graph):
        """测试多重关系"""
        service, entities = service_with_graph

        # Apple 的相关实体 (应包含 Steve 和 Tim)
        related = service.get_related_entities(entities["apple"])

        # 应该至少能找到部分相关实体
        assert len(related) > 0


class TestEdgeCases:
    """测试边界情况"""

    @pytest.fixture
    def service(self):
        """创建 Service 实例"""
        collection = UnifiedCollection("entities")
        return PropertyGraphService(collection)

    def test_retrieve_empty_collection(self, service):
        """测试空 Collection 检索"""
        results = service.retrieve("", top_k=10, entity_type="Company")
        assert results == []

    def test_get_related_entities_no_relationships(self, service):
        """测试没有关系的实体"""
        entity_id = service.insert("Isolated Entity")
        related = service.get_related_entities(entity_id)
        assert related == []

    def test_delete_entity(self, service):
        """测试删除实体"""
        entity_id = service.insert("To be deleted")
        assert service.delete(entity_id) is True
        assert service.get(entity_id) is None

    def test_list_indexes(self, service):
        """测试列出索引"""
        indexes = service.list_indexes()
        assert len(indexes) == 1
        assert indexes[0]["name"] == "property_graph"
        assert indexes[0]["type"] == "graph"


class TestComplexScenarios:
    """测试复杂场景"""

    def test_knowledge_graph_scenario(self):
        """测试知识图谱场景"""
        collection = UnifiedCollection("kg")
        service = PropertyGraphService(collection)

        # 创建知识图谱:
        # Apple (Company) <- FOUNDED <- Steve Jobs (Person)
        # Apple <- WORKS_AT <- Tim Cook (Person)
        # iPhone (Product) <- MANUFACTURED_BY <- Apple

        apple = service.insert(
            "Apple Inc.",
            metadata={"entity_type": "Company", "properties": {"founded": 1976}},
        )

        steve = service.insert(
            "Steve Jobs",
            metadata={"entity_type": "Person"},
            relationships=[(apple, "FOUNDED", {"year": 1976})],
        )

        tim = service.insert(
            "Tim Cook",
            metadata={"entity_type": "Person"},
            relationships=[(apple, "WORKS_AT", {"since": 2011, "position": "CEO"})],
        )

        iphone = service.insert(
            "iPhone",
            metadata={"entity_type": "Product"},
            relationships=[(apple, "MANUFACTURED_BY", {})],
        )

        # 验证所有实体都已插入
        assert service.get(apple) is not None
        assert service.get(steve) is not None
        assert service.get(tim) is not None
        assert service.get(iphone) is not None

        # 验证可以按类型检索
        companies = service.retrieve("", entity_type="Company")
        assert len(companies) == 1

        people = service.retrieve("", entity_type="Person")
        assert len(people) == 2
