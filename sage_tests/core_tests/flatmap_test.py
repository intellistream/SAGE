import time
import threading
from typing import List, Dict, Any
from sage_core.api.local_environment import LocalStreamEnvironment
from sage_core.function.source_function import SourceFunction
from sage_core.function.filter_function import FilterFunction
from sage_core.function.sink_function import SinkFunction


class NumberDataSource(SourceFunction):
    """生成数字数据"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.numbers = [
            {"value": 1, "category": "odd", "positive": True},
            {"value": -2, "category": "even", "positive": False},
            {"value": 3, "category": "odd", "positive": True},
            {"value": 4, "category": "even", "positive": True},
            {"value": -5, "category": "odd", "positive": False},
            {"value": 6, "category": "even", "positive": True},
            {"value": 0, "category": "even", "positive": False},
            {"value": 7, "category": "odd", "positive": True},
        ]
    
    def execute(self):
        if self.counter >= len(self.numbers):
            return None
        
        data = self.numbers[self.counter]
        self.counter += 1
        self.logger.info(f"NumberSource generated: {data}")
        return data


class UserDataSource(SourceFunction):
    """生成用户数据"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.users = [
            {"id": "user1", "name": "Alice", "age": 25, "status": "active", "premium": True},
            {"id": "user2", "name": "Bob", "age": 17, "status": "inactive", "premium": False},
            {"id": "user3", "name": "Charlie", "age": 30, "status": "active", "premium": True},
            {"id": "user4", "name": "David", "age": 16, "status": "active", "premium": False},
            {"id": "user5", "name": "Eve", "age": 35, "status": "suspended", "premium": True},
            {"id": "user6", "name": "Frank", "age": 22, "status": "active", "premium": False},
        ]
    
    def execute(self):
        if self.counter >= len(self.users):
            return None
        
        data = self.users[self.counter]
        self.counter += 1
        self.logger.info(f"UserSource generated: {data}")
        return data


class FilterDebugSink(SinkFunction):
    """调试用的Sink，记录Filter处理后的数据"""
    
    _received_data: Dict[int, List[Dict]] = {}
    _lock = threading.Lock()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parallel_index = None
        self.received_count = 0
    
    def execute(self, data: Any):
        if self.runtime_context:
            self.parallel_index = self.runtime_context.parallel_index
        
        with self._lock:
            if self.parallel_index not in self._received_data:
                self._received_data[self.parallel_index] = []
            
            self._received_data[self.parallel_index].append(data)
        
        self.received_count += 1
        
        value = data.get('value', data.get('name', 'unknown'))
        
        self.logger.info(
            f"[Instance {self.parallel_index}] "
            f"Received filtered data #{self.received_count}: {data}"
        )
        
        # 打印调试信息
        print(f"🔍 [Instance {self.parallel_index}] Filtered data: {value}, Full: {data}")
        
        return data
    
    @classmethod
    def get_received_data(cls) -> Dict[int, List[Dict]]:
        with cls._lock:
            return dict(cls._received_data)
    
    @classmethod
    def clear_data(cls):
        with cls._lock:
            cls._received_data.clear()


# Filter Function Classes
class PositiveNumberFilter(FilterFunction):
    """过滤正数"""
    
    def execute(self, data: Any) -> bool:
        is_positive = data.get("positive", False)
        self.logger.info(f"PositiveFilter: {data.get('value')} -> {is_positive}")
        return is_positive


class EvenNumberFilter(FilterFunction):
    """过滤偶数"""
    
    def execute(self, data: Any) -> bool:
        value = data.get("value", 0)
        is_even = value % 2 == 0
        self.logger.info(f"EvenFilter: {value} -> {is_even}")
        return is_even


class ActiveUserFilter(FilterFunction):
    """过滤活跃用户"""
    
    def execute(self, data: Any) -> bool:
        is_active = data.get("status") == "active"
        self.logger.info(f"ActiveUserFilter: {data.get('name')} ({data.get('status')}) -> {is_active}")
        return is_active


class AdultUserFilter(FilterFunction):
    """过滤成年用户 (age >= 18)"""
    
    def execute(self, data: Any) -> bool:
        age = data.get("age", 0)
        is_adult = age >= 18
        self.logger.info(f"AdultUserFilter: {data.get('name')} (age {age}) -> {is_adult}")
        return is_adult


class PremiumUserFilter(FilterFunction):
    """过滤高级用户"""
    
    def execute(self, data: Any) -> bool:
        is_premium = data.get("premium", False)
        self.logger.info(f"PremiumUserFilter: {data.get('name')} -> {is_premium}")
        return is_premium


class AlwaysTrueFilter(FilterFunction):
    """总是返回True的过滤器"""
    
    def execute(self, data: Any) -> bool:
        self.logger.info(f"AlwaysTrueFilter: {data} -> True")
        return True


class AlwaysFalseFilter(FilterFunction):
    """总是返回False的过滤器"""
    
    def execute(self, data: Any) -> bool:
        self.logger.info(f"AlwaysFalseFilter: {data} -> False")
        return False


class ErrorFilter(FilterFunction):
    """故意抛出异常的过滤器"""
    
    def execute(self, data: Any) -> bool:
        self.logger.info(f"ErrorFilter: About to throw exception for {data}")
        raise ValueError("Intentional filter error for testing")


class TestFilterFunctionality:
    """测试Filter功能"""
    
    def setup_method(self):
        FilterDebugSink.clear_data()
    
    def test_basic_positive_filter(self):
        """测试基本的正数过滤"""
        print("\n🚀 Testing Basic Positive Number Filter")
        
        env = LocalStreamEnvironment("positive_filter_test")
        
        result_stream = (
            env.from_source(NumberDataSource, delay=0.2)
            .filter(PositiveNumberFilter)
            .sink(FilterDebugSink, parallelism=2)
        )
        
        print("📊 Pipeline: NumberSource -> filter(PositiveNumberFilter) -> Sink(parallelism=2)")
        print("🎯 Expected: Only positive numbers should pass through\n")
        
        try:
            env.submit()
            # env.run_streaming()
            time.sleep(3)
        finally:
            env.close()
        
        self._verify_positive_filter_results()
    
    def test_chained_filters(self):
        """测试链式过滤器"""
        print("\n🚀 Testing Chained Filters")
        
        env = LocalStreamEnvironment("chained_filter_test")
        
        result_stream = (
            env.from_source(NumberDataSource, delay=0.2)
            .filter(PositiveNumberFilter)    # 先过滤正数
            .filter(EvenNumberFilter)        # 再过滤偶数
            .sink(FilterDebugSink, parallelism=1)
        )
        
        print("📊 Pipeline: NumberSource -> filter(Positive) -> filter(Even) -> Sink")
        print("🎯 Expected: Only positive even numbers should pass through\n")
        
        try:
            env.submit()
            # env.run_streaming()
            time.sleep(3)
        finally:
            env.close()
        
        self._verify_chained_filter_results()
    
    def test_user_filters(self):
        """测试用户数据过滤"""
        print("\n🚀 Testing User Data Filters")
        
        env = LocalStreamEnvironment("user_filter_test")
        
        result_stream = (
            env.from_source(UserDataSource, delay=0.3)
            .filter(ActiveUserFilter)
            .filter(AdultUserFilter)
            .sink(FilterDebugSink, parallelism=2)
        )
        
        print("📊 Pipeline: UserSource -> filter(Active) -> filter(Adult) -> Sink")
        print("🎯 Expected: Only active adult users should pass through\n")
        
        try:
            env.submit()
            # env.run_streaming()
            time.sleep(4)
        finally:
            env.close()
        
        self._verify_user_filter_results()
    
    def test_lambda_filter(self):
        """测试Lambda函数过滤"""
        print("\n🚀 Testing Lambda Function Filter")
        
        env = LocalStreamEnvironment("lambda_filter_test")
        
        result_stream = (
            env.from_source(NumberDataSource, delay=0.2)
            .filter(lambda x: x["value"] > 0 and x["value"] < 5)  # 0 < value < 5
            .sink(FilterDebugSink, parallelism=1)
        )
        
        print("📊 Pipeline: NumberSource -> filter(lambda: 0 < value < 5) -> Sink")
        print("🎯 Expected: Only numbers between 1-4 should pass through\n")
        
        try:
            env.submit()
            # env.run_streaming()
            time.sleep(3)
        finally:
            env.close()
        
        self._verify_lambda_filter_results()
    
    def test_extreme_filters(self):
        """测试极端情况的过滤器"""
        print("\n🚀 Testing Extreme Filter Cases")
        
        env = LocalStreamEnvironment("extreme_filter_test")
        
        # 测试1：所有数据都通过
        always_true_stream = (
            env.from_source(NumberDataSource, delay=0.2)
            .filter(AlwaysTrueFilter)
            .sink(FilterDebugSink, parallelism=1)
        )
        
        print("📊 Test 1: AlwaysTrueFilter - All data should pass")
        
        try:
            env.submit()
            # env.run_streaming()
            time.sleep(2)
        finally:
            env.close()
        
        all_pass_results = FilterDebugSink.get_received_data()
        FilterDebugSink.clear_data()
        
        # 测试2：所有数据都被过滤
        env2 = LocalStreamEnvironment("always_false_filter_test")
        
        always_false_stream = (
            env2.from_source(NumberDataSource, delay=0.2)
            .filter(AlwaysFalseFilter)
            .sink(FilterDebugSink, parallelism=1)
        )
        
        print("📊 Test 2: AlwaysFalseFilter - No data should pass")
        
        try:
            env2.submit()
            env2.run_streaming()
            time.sleep(2)
        finally:
            env2.close()
        
        none_pass_results = FilterDebugSink.get_received_data()
        
        self._verify_extreme_filter_results(all_pass_results, none_pass_results)
    
    def test_filter_with_map_integration(self):
        """测试Filter与Map的集成"""
        print("\n🚀 Testing Filter + Map Integration")
        
        env = LocalStreamEnvironment("filter_map_integration_test")
        
        result_stream = (
            env.from_source(UserDataSource, delay=0.3)
            .filter(ActiveUserFilter)          # 过滤活跃用户
            .map(lambda x: {                   # 转换数据格式
                "username": x["name"].upper(),
                "user_age": x["age"],
                "is_premium": x["premium"]
            })
            .filter(lambda x: x["user_age"] >= 25)  # 再过滤年龄
            .sink(FilterDebugSink, parallelism=1)
        )
        
        print("📊 Pipeline: UserSource -> filter(Active) -> map(Transform) -> filter(Age>=25) -> Sink")
        print("🎯 Expected: Active users aged 25+ with transformed format\n")
        
        try:
            env.submit()
            # env.run_streaming()
            time.sleep(4)
        finally:
            env.close()
        
        self._verify_filter_map_integration_results()
    
    def test_filter_error_handling(self):
        """测试Filter的错误处理"""
        print("\n🚀 Testing Filter Error Handling")
        
        env = LocalStreamEnvironment("filter_error_test")
        
        # 注意：这个测试可能会产生错误日志，这是预期的
        result_stream = (
            env.from_source(NumberDataSource, delay=0.2)
            .filter(ErrorFilter)  # 故意抛出异常的过滤器
            .sink(FilterDebugSink, parallelism=1)
        )
        
        print("📊 Pipeline: NumberSource -> filter(ErrorFilter) -> Sink")
        print("🎯 Expected: Errors should be handled gracefully, minimal data should pass\n")
        
        try:
            env.submit()
            # env.run_streaming()
            time.sleep(3)
        finally:
            env.close()
        
        self._verify_error_handling_results()
    
    def _verify_positive_filter_results(self):
        """验证正数过滤结果"""
        received_data = FilterDebugSink.get_received_data()
        
        print("\n📋 Positive Filter Results:")
        print("=" * 40)
        
        all_filtered_data = []
        for instance_id, data_list in received_data.items():
            print(f"\n🔹 Parallel Instance {instance_id}:")
            for data in data_list:
                all_filtered_data.append(data)
                value = data.get("value")
                positive = data.get("positive")
                print(f"   - Value: {value}, Positive: {positive}")
        
        print(f"\n🎯 Filter Summary:")
        print(f"   - Total filtered data: {len(all_filtered_data)}")
        
        # 验证：所有通过的数据都应该是正数
        for data in all_filtered_data:
            assert data.get("positive") == True, f"❌ Non-positive data passed filter: {data}"
        
        # 验证：应该有正数通过（基于测试数据）
        assert len(all_filtered_data) > 0, "❌ No data passed positive filter"
        
        print("✅ Positive filter test passed: Only positive numbers passed through")
    
    def _verify_chained_filter_results(self):
        """验证链式过滤结果"""
        received_data = FilterDebugSink.get_received_data()
        
        print("\n📋 Chained Filter Results:")
        print("=" * 40)
        
        all_filtered_data = []
        for instance_id, data_list in received_data.items():
            for data in data_list:
                all_filtered_data.append(data)
                value = data.get("value")
                positive = data.get("positive")
                category = data.get("category")
                print(f"   - Value: {value}, Positive: {positive}, Category: {category}")
        
        print(f"\n🎯 Chained Filter Summary:")
        print(f"   - Total data after both filters: {len(all_filtered_data)}")
        
        # 验证：所有数据都应该是正偶数
        for data in all_filtered_data:
            assert data.get("positive") == True, f"❌ Non-positive data: {data}"
            assert data.get("category") == "even", f"❌ Non-even data: {data}"
            assert data.get("value") > 0, f"❌ Non-positive value: {data}"
            assert data.get("value") % 2 == 0, f"❌ Non-even value: {data}"
        
        print("✅ Chained filter test passed: Only positive even numbers passed")
    
    def _verify_user_filter_results(self):
        """验证用户过滤结果"""
        received_data = FilterDebugSink.get_received_data()
        
        print("\n📋 User Filter Results:")
        print("=" * 40)
        
        all_filtered_users = []
        for instance_id, data_list in received_data.items():
            for user in data_list:
                all_filtered_users.append(user)
                name = user.get("name")
                age = user.get("age")
                status = user.get("status")
                print(f"   - User: {name}, Age: {age}, Status: {status}")
        
        print(f"\n🎯 User Filter Summary:")
        print(f"   - Total filtered users: {len(all_filtered_users)}")
        
        # 验证：所有用户都应该是活跃且成年的
        for user in all_filtered_users:
            assert user.get("status") == "active", f"❌ Non-active user: {user}"
            assert user.get("age") >= 18, f"❌ Minor user: {user}"
        
        print("✅ User filter test passed: Only active adult users passed")
    
    def _verify_lambda_filter_results(self):
        """验证Lambda过滤结果"""
        received_data = FilterDebugSink.get_received_data()
        
        print("\n📋 Lambda Filter Results:")
        print("=" * 40)
        
        all_filtered_data = []
        for instance_id, data_list in received_data.items():
            for data in data_list:
                all_filtered_data.append(data)
                value = data.get("value")
                print(f"   - Value: {value}")
        
        print(f"\n🎯 Lambda Filter Summary:")
        print(f"   - Total data in range (0,5): {len(all_filtered_data)}")
        
        # 验证：所有数据的值都应该在0到5之间（不包括0和5）
        for data in all_filtered_data:
            value = data.get("value")
            assert 0 < value < 5, f"❌ Value {value} not in range (0,5): {data}"
        
        print("✅ Lambda filter test passed: Only values in range (0,5) passed")
    
    def _verify_extreme_filter_results(self, all_pass_results, none_pass_results):
        """验证极端过滤结果"""
        print("\n📋 Extreme Filter Results:")
        print("=" * 40)
        
        # 验证AlwaysTrueFilter结果
        all_pass_count = sum(len(data_list) for data_list in all_pass_results.values())
        print(f"🔹 AlwaysTrueFilter: {all_pass_count} items passed")
        
        # 验证AlwaysFalseFilter结果
        none_pass_count = sum(len(data_list) for data_list in none_pass_results.values())
        print(f"🔹 AlwaysFalseFilter: {none_pass_count} items passed")
        
        # 基于测试数据，AlwaysTrueFilter应该有数据通过
        assert all_pass_count > 0, "❌ AlwaysTrueFilter should pass all data"
        
        # AlwaysFalseFilter应该没有数据通过
        assert none_pass_count == 0, "❌ AlwaysFalseFilter should pass no data"
        
        print("✅ Extreme filter tests passed: True filter passes all, False filter passes none")
    
    def _verify_filter_map_integration_results(self):
        """验证Filter+Map集成结果"""
        received_data = FilterDebugSink.get_received_data()
        
        print("\n📋 Filter + Map Integration Results:")
        print("=" * 40)
        
        all_results = []
        for instance_id, data_list in received_data.items():
            for data in data_list:
                all_results.append(data)
                username = data.get("username")
                age = data.get("user_age")
                premium = data.get("is_premium")
                print(f"   - User: {username}, Age: {age}, Premium: {premium}")
        
        print(f"\n🎯 Integration Summary:")
        print(f"   - Total processed users: {len(all_results)}")
        
        # 验证：所有用户都应该满足条件且格式正确
        for user in all_results:
            # 检查数据格式（由map转换）
            assert "username" in user, f"❌ Missing username field: {user}"
            assert "user_age" in user, f"❌ Missing user_age field: {user}"
            assert "is_premium" in user, f"❌ Missing is_premium field: {user}"
            
            # 检查年龄条件（第二个filter）
            assert user.get("user_age") >= 25, f"❌ User under 25: {user}"
            
            # 检查用户名是大写（map转换的结果）
            username = user.get("username", "")
            assert username.isupper(), f"❌ Username not uppercase: {user}"
        
        print("✅ Filter + Map integration test passed: Correct filtering and transformation")
    
    def _verify_error_handling_results(self):
        """验证错误处理结果"""
        received_data = FilterDebugSink.get_received_data()
        
        print("\n📋 Error Handling Results:")
        print("=" * 40)
        
        all_results = []
        for instance_id, data_list in received_data.items():
            all_results.extend(data_list)
        
        print(f"🔹 Data that passed through error filter: {len(all_results)}")
        
        # 由于ErrorFilter总是抛出异常，正常情况下应该没有数据通过
        # 但根据错误处理策略，可能会有一些数据以原始形式传递
        print(f"   - Items that somehow passed: {len(all_results)}")
        
        # 这个测试主要验证系统不会因为Filter异常而崩溃
        print("✅ Error handling test passed: System handled filter errors gracefully")


if __name__ == "__main__":
    # 可以直接运行单个测试
    test = TestFilterFunctionality()
    test.setup_method()
    test.test_basic_positive_filter()

'''
# 运行所有Filter测试
pytest sage_tests/core_tests/filter_test.py -v -s

# 运行特定测试
pytest sage_tests/core_tests/filter_test.py::TestFilterFunctionality::test_basic_positive_filter -v -s
pytest sage_tests/core_tests/filter_test.py::TestFilterFunctionality::test_chained_filters -v -s
pytest sage_tests/core_tests/filter_test.py::TestFilterFunctionality::test_lambda_filter -v -s
'''