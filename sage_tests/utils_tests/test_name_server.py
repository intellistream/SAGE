import unittest
import threading
from sage_utils.name_server import NameServer

class TestNameServer(unittest.TestCase):
    
    def setUp(self):
        NameServer.clear_all()
    
    def test_register_unique_name(self):
        """测试注册唯一名称"""
        result = NameServer.register_name("user1")
        self.assertEqual(result, "user1")
        
        # 检查名称已被占用
        self.assertFalse(NameServer.is_name_available("user1"))
        self.assertTrue(NameServer.is_name_available("user2"))
    
    def test_register_duplicate_name(self):
        """测试重复名称自动添加后缀"""
        # 注册第一个
        result1 = NameServer.register_name("service")
        self.assertEqual(result1, "service")
        
        # 注册重复名称
        result2 = NameServer.register_name("service")
        self.assertEqual(result2, "service_1")
        
        # 再次注册
        result3 = NameServer.register_name("service")
        self.assertEqual(result3, "service_2")
    
    def test_unregister_name(self):
        """测试注销名称"""
        name = NameServer.register_name("temp")
        self.assertFalse(NameServer.is_name_available(name))
        
        success = NameServer.unregister_name(name)
        self.assertTrue(success)
        self.assertTrue(NameServer.is_name_available(name))
        
        # 重复注销
        success = NameServer.unregister_name(name)
        self.assertFalse(success)
    
    def test_empty_name_validation(self):
        """测试空名称验证"""
        with self.assertRaises(ValueError):
            NameServer.register_name("")
        
        with self.assertRaises(ValueError):
            NameServer.register_name("   ")
    
    def test_thread_safety(self):
        """测试线程安全"""
        results = []
        
        def register_names():
            for i in range(5):
                result = NameServer.register_name("concurrent")
                results.append(result)
        
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=register_names)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 检查所有结果都是唯一的
        self.assertEqual(len(results), len(set(results)))
        self.assertEqual(len(results), 15)  # 3个线程 * 5次注册
    
    def test_multiple_different_names(self):
        """测试多个不同名称的注册"""
        names = ["api", "database", "cache", "queue"]
        registered = []
        
        for name in names:
            result = NameServer.register_name(name)
            registered.append(result)
        
        # 所有名称都应该保持原样
        self.assertEqual(names, registered)
    
    def test_reuse_after_unregister(self):
        """测试注销后可以重新使用原名称"""
        # 注册原名称
        original = NameServer.register_name("reuse_test")
        self.assertEqual(original, "reuse_test")
        
        # 注册重复名称
        duplicate = NameServer.register_name("reuse_test")
        self.assertEqual(duplicate, "reuse_test_1")
        
        # 注销原名称
        NameServer.unregister_name("reuse_test")
        
        # 重新注册应该可以使用原名称
        new_register = NameServer.register_name("reuse_test")
        self.assertEqual(new_register, "reuse_test")

if __name__ == "__main__":
    unittest.main()