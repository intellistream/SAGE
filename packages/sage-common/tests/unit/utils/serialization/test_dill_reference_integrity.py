"""
测试 dill 序列化器的对象引用完整性

本测试文件验证 GitHub issue #254 的修复：
"对象引用去重在序列化过程中失效"

问题描述：
在 A->B,C B->D C->D 的引用结构中，序列化前 `B.d is C.d` 为 `True`，
但反序列化后 `restored_B.d is restored_C.d` 为 `False`，
即原本共享的对象 D 被重复创建了多份。

修复方案：
使用对象映射表 (_object_map) 维护引用关系，确保相同的原始对象
在预处理过程中始终映射到同一个新实例。
"""

import pytest

from sage.common.utils.serialization.dill import deserialize_object, serialize_object


class SharedResource:
    """共享资源类 - 对应issue中的对象D"""

    def __init__(self, name, data):
        self.name = name
        self.data = data

    def __repr__(self):
        return f"SharedResource(name={self.name}, data={self.data})"

    def __eq__(self, other):
        # 使用宽松的类型检查，适应序列化/反序列化的行为
        return (
            hasattr(other, "name")
            and hasattr(other, "data")
            and self.name == other.name
            and self.data == other.data
        )


class NodeB:
    """节点B类"""

    def __init__(self, shared_d):
        self.d = shared_d

    def __repr__(self):
        return f"NodeB(d={self.d})"


class NodeC:
    """节点C类"""

    def __init__(self, shared_d):
        self.d = shared_d

    def __repr__(self):
        return f"NodeC(d={self.d})"


class NodeA:
    """节点A类 - 包含B和C的引用"""

    def __init__(self, node_b, node_c):
        self.b = node_b
        self.c = node_c

    def __repr__(self):
        return f"NodeA(b={self.b}, c={self.c})"


class TestObjectReferenceIntegrity:
    """测试对象引用完整性"""

    def test_issue_254_basic_shared_reference(self):
        """
        测试基本的共享引用场景 (GitHub issue #254)

        验证 A->B,C B->D C->D 引用结构中，
        序列化后 B.d 和 C.d 仍然是同一个对象。
        """
        # 创建共享对象D
        shared_d = SharedResource("test", {"value": 42})

        # 创建引用链 A->B,C B->D C->D
        node_b = NodeB(shared_d)
        node_c = NodeC(shared_d)
        node_a = NodeA(node_b, node_c)

        # 序列化前：B.d 和 C.d 是同一个对象
        assert node_a.b.d is node_a.c.d, "序列化前引用应该相同"
        assert node_a.b.d == node_a.c.d, "序列化前数据应该相等"

        # 序列化和反序列化
        serialized = serialize_object(node_a)
        restored_a = deserialize_object(serialized)

        # 序列化后：引用完整性应该保持
        assert restored_a.b.d is restored_a.c.d, "序列化后引用应该保持相同 (issue #254 修复验证)"
        assert restored_a.b.d == restored_a.c.d, "序列化后数据应该相等"

        # 验证数据内容正确
        assert restored_a.b.d.name == "test"
        assert restored_a.b.d.data == {"value": 42}

    def test_circular_reference(self):
        """测试循环引用场景"""

        class CircularA:
            def __init__(self):
                self.b: CircularB | None = None

            def __repr__(self):
                return f"CircularA(b={'...' if self.b else None})"

        class CircularB:
            def __init__(self, a: CircularA):
                self.a = a

            def __repr__(self):
                return f"CircularB(a={'...' if self.a else None})"

        # 创建循环引用
        a = CircularA()
        b = CircularB(a)
        a.b = b

        # 序列化前检查
        assert a.b and a.b.a is a, "循环引用应该正确"

        # 序列化和反序列化
        serialized = serialize_object(a)
        restored_a = deserialize_object(serialized)

        # 序列化后检查循环引用
        assert restored_a.b.a is restored_a, "循环引用应该保持"

    def test_multiple_shared_objects(self):
        """测试多个共享对象"""

        shared1 = SharedResource("shared1", {"type": "A"})
        shared2 = SharedResource("shared2", {"type": "B"})

        class Container:
            def __init__(self, obj1, obj2):
                self.obj1 = obj1
                self.obj2 = obj2

        # 创建复杂引用结构
        container1 = Container(shared1, shared2)
        container2 = Container(shared1, shared2)  # 重用相同的共享对象

        root = Container(container1, container2)

        # 序列化前检查
        assert root.obj1.obj1 is root.obj2.obj1, "shared1应该是同一个对象"
        assert root.obj1.obj2 is root.obj2.obj2, "shared2应该是同一个对象"

        # 序列化和反序列化
        serialized = serialize_object(root)
        restored_root = deserialize_object(serialized)

        # 序列化后检查
        assert restored_root.obj1.obj1 is restored_root.obj2.obj1, (
            "restored shared1应该是同一个对象"
        )
        assert restored_root.obj1.obj2 is restored_root.obj2.obj2, (
            "restored shared2应该是同一个对象"
        )

    def test_list_with_shared_objects(self):
        """测试列表中的共享对象"""

        shared = SharedResource("shared_in_list", {"value": 999})

        # 创建包含共享对象的列表
        list_data = [shared, shared, shared]
        dict_data = {"a": shared, "b": shared}

        container = {"list": list_data, "dict": dict_data}

        # 序列化前检查
        assert container["list"][0] is container["list"][1], "列表中的对象应该相同"
        assert container["list"][0] is container["dict"]["a"], "列表和字典中的对象应该相同"

        # 序列化和反序列化
        serialized = serialize_object(container)
        restored = deserialize_object(serialized)

        # 序列化后检查
        assert restored["list"][0] is restored["list"][1], "恢复后列表中的对象应该相同"
        assert restored["list"][0] is restored["dict"]["a"], "恢复后列表和字典中的对象应该相同"

    def test_deep_nested_sharing(self):
        """测试深度嵌套的共享"""

        shared = SharedResource("deep_shared", {"level": "deep"})

        # 创建深度嵌套结构
        level3 = {"shared": shared}
        level2 = {"nested": level3, "also_shared": shared}
        level1 = {"data": level2, "direct_shared": shared}

        # 序列化前检查
        assert level1["data"]["nested"]["shared"] is level1["direct_shared"], (
            "深度嵌套的共享对象应该相同"
        )

        # 序列化和反序列化
        serialized = serialize_object(level1)
        restored = deserialize_object(serialized)

        # 序列化后检查
        assert restored["data"]["nested"]["shared"] is restored["direct_shared"], (
            "恢复后深度嵌套的共享对象应该相同"
        )


if __name__ == "__main__":
    # 允许直接运行测试文件
    pytest.main([__file__, "-v"])
