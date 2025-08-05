"""
JobManager工具模块测试
测试 sage.jobmanager.utils 中的所有工具功能，包括名称服务器等
"""
import pytest
import socket
from unittest.mock import Mock, patch

from sage.jobmanager.utils.name_server import get_name


@pytest.mark.unit
class TestNameServer:
    """测试名称服务器功能"""

    def test_get_name_basic(self):
        """测试基本名称获取"""
        with patch('socket.gethostname') as mock_hostname, \
             patch('sage.jobmanager.utils.name_server.get_available_port') as mock_port:
            
            mock_hostname.return_value = "test-host"
            mock_port.return_value = 12345
            
            name = get_name("test_service")
            
            assert "test_service" in name
            assert "test-host" in name
            assert "12345" in name

    def test_get_name_with_prefix(self):
        """测试带前缀的名称获取"""
        with patch('socket.gethostname') as mock_hostname, \
             patch('sage.jobmanager.utils.name_server.get_available_port') as mock_port:
            
            mock_hostname.return_value = "test-host"
            mock_port.return_value = 8080
            
            name = get_name("service", prefix="sage")
            
            assert name.startswith("sage")
            assert "service" in name
            assert "test-host" in name
            assert "8080" in name

    def test_get_name_uniqueness(self):
        """测试名称唯一性"""
        with patch('socket.gethostname') as mock_hostname:
            mock_hostname.return_value = "test-host"
            
            with patch('sage.jobmanager.utils.name_server.get_available_port') as mock_port:
                # 模拟不同的端口返回
                mock_port.side_effect = [8080, 8081, 8082]
                
                names = []
                for i in range(3):
                    name = get_name("service")
                    names.append(name)
                
                # 验证所有名称都不同
                assert len(set(names)) == 3

    def test_get_name_hostname_failure(self):
        """测试主机名获取失败的处理"""
        with patch('socket.gethostname') as mock_hostname, \
             patch('sage.jobmanager.utils.name_server.get_available_port') as mock_port:
            
            # 模拟gethostname失败
            mock_hostname.side_effect = socket.error("Hostname lookup failed")
            mock_port.return_value = 9090
            
            name = get_name("service")
            
            # 应该使用默认主机名或IP
            assert "service" in name
            assert "9090" in name
            # 名称中应该包含fallback主机标识
            assert any(fallback in name for fallback in ["localhost", "127.0.0.1", "unknown"])

    def test_get_available_port_basic(self):
        """测试获取可用端口"""
        from sage.jobmanager.utils.name_server import get_available_port
        
        port = get_available_port()
        
        # 验证返回的是有效端口号
        assert isinstance(port, int)
        assert 1024 <= port <= 65535

    def test_get_available_port_range(self):
        """测试指定范围的端口获取"""
        from sage.jobmanager.utils.name_server import get_available_port
        
        port = get_available_port(start_port=8000, end_port=9000)
        
        assert 8000 <= port <= 9000

    def test_get_available_port_host_binding(self):
        """测试指定主机的端口绑定"""
        from sage.jobmanager.utils.name_server import get_available_port
        
        # 测试localhost绑定
        port = get_available_port(host="localhost")
        assert isinstance(port, int)
        
        # 测试0.0.0.0绑定
        port = get_available_port(host="0.0.0.0")
        assert isinstance(port, int)

    def test_get_available_port_exhaustion(self):
        """测试端口耗尽情况"""
        from sage.jobmanager.utils.name_server import get_available_port
        
        # 模拟所有端口都被占用的情况
        with patch('socket.socket') as mock_socket:
            mock_sock_instance = Mock()
            mock_socket.return_value = mock_sock_instance
            
            # 模拟bind总是失败
            mock_sock_instance.bind.side_effect = socket.error("Address already in use")
            
            # 在非常小的端口范围内测试
            with pytest.raises(RuntimeError, match="No available ports"):
                get_available_port(start_port=8000, end_port=8002)

    def test_get_available_port_concurrent_access(self):
        """测试并发访问时的端口分配"""
        from sage.jobmanager.utils.name_server import get_available_port
        import threading
        import time
        
        ports = []
        
        def get_port():
            port = get_available_port()
            ports.append(port)
        
        # 创建多个线程同时获取端口
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=get_port)
            threads.append(thread)
        
        # 启动所有线程
        for thread in threads:
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证所有端口都不同
        assert len(ports) == 5
        assert len(set(ports)) == 5


@pytest.mark.unit
class TestNameServerConfiguration:
    """测试名称服务器配置功能"""

    def test_name_format_customization(self):
        """测试名称格式自定义"""
        with patch('socket.gethostname') as mock_hostname, \
             patch('sage.jobmanager.utils.name_server.get_available_port') as mock_port:
            
            mock_hostname.return_value = "custom-host"
            mock_port.return_value = 7777
            
            # 测试自定义分隔符
            name = get_name("service", separator="-")
            parts = name.split("-")
            assert len(parts) >= 3  # service, host, port
            
            # 测试自定义格式
            name = get_name("service", include_timestamp=True)
            assert "service" in name
            assert "custom-host" in name
            assert "7777" in name

    def test_name_with_metadata(self):
        """测试带元数据的名称生成"""
        with patch('socket.gethostname') as mock_hostname, \
             patch('sage.jobmanager.utils.name_server.get_available_port') as mock_port:
            
            mock_hostname.return_value = "meta-host"
            mock_port.return_value = 6666
            
            metadata = {
                "version": "1.0",
                "environment": "production",
                "region": "us-west"
            }
            
            name = get_name("service", metadata=metadata)
            
            assert "service" in name
            assert "meta-host" in name
            assert "6666" in name
            # 元数据应该以某种形式包含在名称中
            assert any(value in name for value in metadata.values())

    def test_name_validation(self):
        """测试名称验证"""
        from sage.jobmanager.utils.name_server import validate_name
        
        # 有效名称
        valid_names = [
            "service_host_8080",
            "ml-model-server_localhost_9090",
            "data_processor.prod.cluster_192.168.1.100_3000"
        ]
        
        for name in valid_names:
            assert validate_name(name) is True
        
        # 无效名称
        invalid_names = [
            "",  # 空名称
            "a",  # 太短
            "service with spaces",  # 包含空格
            "service@host#8080",  # 包含特殊字符
            "x" * 300  # 太长
        ]
        
        for name in invalid_names:
            assert validate_name(name) is False

    def test_name_registry_operations(self):
        """测试名称注册表操作"""
        from sage.jobmanager.utils.name_server import NameRegistry
        
        registry = NameRegistry()
        
        # 注册名称
        name1 = "service1_host_8080"
        name2 = "service2_host_8081"
        
        assert registry.register(name1, {"type": "api", "status": "active"}) is True
        assert registry.register(name2, {"type": "worker", "status": "active"}) is True
        
        # 重复注册应该失败
        assert registry.register(name1, {"type": "api"}) is False
        
        # 查询名称
        info1 = registry.lookup(name1)
        assert info1["type"] == "api"
        assert info1["status"] == "active"
        
        # 注销名称
        assert registry.unregister(name1) is True
        assert registry.lookup(name1) is None
        
        # 重复注销应该失败
        assert registry.unregister(name1) is False

    def test_name_lease_management(self):
        """测试名称租约管理"""
        from sage.jobmanager.utils.name_server import NameLease
        
        lease_duration = 60  # 60秒
        lease = NameLease("service_host_8080", lease_duration)
        
        # 新创建的租约应该是有效的
        assert lease.is_valid() is True
        
        # 续约
        lease.renew(30)  # 续约30秒
        assert lease.is_valid() is True
        
        # 模拟时间流逝
        with patch('time.time') as mock_time:
            mock_time.return_value = lease.start_time + lease_duration + 1
            assert lease.is_valid() is False
        
        # 释放租约
        lease.release()
        assert lease.is_valid() is False


@pytest.mark.unit
class TestNameServerErrorHandling:
    """测试名称服务器错误处理"""

    def test_network_error_handling(self):
        """测试网络错误处理"""
        with patch('socket.gethostname') as mock_hostname:
            # 模拟网络错误
            mock_hostname.side_effect = socket.gaierror("Name resolution failed")
            
            name = get_name("service")
            
            # 应该使用fallback机制
            assert "service" in name
            assert any(fallback in name for fallback in ["localhost", "127.0.0.1", "unknown"])

    def test_port_allocation_error_handling(self):
        """测试端口分配错误处理"""
        from sage.jobmanager.utils.name_server import get_available_port
        
        with patch('socket.socket') as mock_socket:
            mock_sock_instance = Mock()
            mock_socket.return_value = mock_sock_instance
            
            # 模拟套接字创建失败
            mock_socket.side_effect = socket.error("Socket creation failed")
            
            with pytest.raises(RuntimeError, match="Failed to create socket"):
                get_available_port()

    def test_resource_cleanup_on_error(self):
        """测试错误时的资源清理"""
        from sage.jobmanager.utils.name_server import get_available_port
        
        with patch('socket.socket') as mock_socket:
            mock_sock_instance = Mock()
            mock_socket.return_value = mock_sock_instance
            
            # 模拟bind成功但close时出错
            mock_sock_instance.bind.return_value = None
            mock_sock_instance.getsockname.return_value = ("127.0.0.1", 8080)
            mock_sock_instance.close.side_effect = socket.error("Close failed")
            
            # 应该仍然返回端口，即使close失败
            port = get_available_port()
            assert port == 8080
            
            # 验证close被调用
            mock_sock_instance.close.assert_called_once()

    def test_concurrent_access_race_condition(self):
        """测试并发访问竞争条件"""
        from sage.jobmanager.utils.name_server import get_available_port
        import threading
        import time
        
        # 模拟竞争条件：端口在检查和使用之间被占用
        original_socket = socket.socket
        call_count = 0
        
        def mock_socket_factory(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            sock = original_socket(*args, **kwargs)
            
            # 在第一次调用时模拟端口被快速占用
            if call_count == 1:
                original_bind = sock.bind
                def failing_bind(address):
                    if call_count == 1:
                        raise socket.error("Address already in use")
                    return original_bind(address)
                sock.bind = failing_bind
            
            return sock
        
        with patch('socket.socket', side_effect=mock_socket_factory):
            # 应该重试并找到可用端口
            port = get_available_port(start_port=8000, end_port=8010)
            assert isinstance(port, int)
            assert 8000 <= port <= 8010


@pytest.mark.integration
class TestNameServerIntegration:
    """名称服务器集成测试"""

    def test_real_network_port_allocation(self):
        """测试真实网络端口分配"""
        from sage.jobmanager.utils.name_server import get_available_port
        
        # 获取真实可用端口
        port1 = get_available_port()
        port2 = get_available_port()
        
        # 端口应该不同
        assert port1 != port2
        
        # 验证端口真的可用
        sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            sock1.bind(("localhost", port1))
            sock2.bind(("localhost", port2))
        finally:
            sock1.close()
            sock2.close()

    def test_name_generation_with_real_hostname(self):
        """测试使用真实主机名的名称生成"""
        import socket
        
        # 获取真实主机名
        real_hostname = socket.gethostname()
        
        name = get_name("integration_test")
        
        assert "integration_test" in name
        assert real_hostname in name or "localhost" in name  # fallback情况

    def test_service_lifecycle_simulation(self):
        """测试服务生命周期模拟"""
        from sage.jobmanager.utils.name_server import NameRegistry
        
        registry = NameRegistry()
        
        # 模拟服务启动
        service_name = get_name("test_service")
        service_info = {
            "type": "worker",
            "status": "starting",
            "pid": 12345,
            "start_time": "2023-01-01T10:00:00Z"
        }
        
        assert registry.register(service_name, service_info) is True
        
        # 模拟服务状态更新
        service_info["status"] = "running"
        registry.update(service_name, service_info)
        
        updated_info = registry.lookup(service_name)
        assert updated_info["status"] == "running"
        
        # 模拟服务停止
        service_info["status"] = "stopped"
        registry.update(service_name, service_info)
        
        # 模拟服务注销
        assert registry.unregister(service_name) is True
        assert registry.lookup(service_name) is None

    def test_distributed_name_coordination(self):
        """测试分布式名称协调"""
        from sage.jobmanager.utils.name_server import DistributedNameCoordinator
        
        # 模拟多节点环境
        coordinator = DistributedNameCoordinator(node_id="node1")
        
        # 请求全局唯一名称
        name1 = coordinator.request_global_name("service", timeout=5.0)
        name2 = coordinator.request_global_name("service", timeout=5.0)
        
        # 名称应该全局唯一
        assert name1 != name2
        assert "service" in name1
        assert "service" in name2
        
        # 释放名称
        coordinator.release_global_name(name1)
        coordinator.release_global_name(name2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
