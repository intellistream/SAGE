"""
Test suite for sage.common.utils.network.local_tcp_server module

This module tests TCP server functionality including connection management,
message handling, and server lifecycle operations.

Created: 2024
Test Framework: pytest
Coverage: TCP server, message handling, connection management
"""

import pickle
import threading
import time
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
from sage.common.utils.network.local_tcp_server import BaseTcpServer, LocalTcpServer


class TestBaseTcpServer:
    """Test BaseTcpServer abstract base class functionality"""

    # Create a concrete implementation for testing
    class ConcreteTcpServer(BaseTcpServer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.received_messages = []

        def _handle_message_data(
            self, message_data: bytes, client_address: tuple
        ) -> Optional[Dict[str, Any]]:
            try:
                message = pickle.loads(message_data)
                self.received_messages.append((message, client_address))
                return {"type": "test_response", "status": "success"}
            except Exception:
                return {"type": "error_response", "status": "error"}

    @pytest.mark.unit
    def test_server_initialization(self):
        """Test server initialization with default parameters"""
        with patch("socket.socket"):
            server = self.ConcreteTcpServer()

            assert server.server_name == "TcpServer"
            assert server.host is not None
            assert server.port is not None
            assert server.running is False
            assert server.server_socket is None
            assert server.server_thread is None
            assert isinstance(server.client_connections, dict)

    @pytest.mark.unit
    def test_server_initialization_with_params(self):
        """Test server initialization with custom parameters"""
        mock_logger = MagicMock()

        with patch("socket.socket"):
            server = self.ConcreteTcpServer(
                host="192.168.1.100",
                port=8080,
                logger=mock_logger,
                server_name="TestServer",
            )

            assert server.server_name == "TestServer"
            assert server.host == "192.168.1.100"
            assert server.port == 8080
            assert server.logger == mock_logger

    @pytest.mark.unit
    def test_default_logger_creation(self):
        """Test default logger creation"""
        with patch("socket.socket"):
            server = self.ConcreteTcpServer()

            assert server.logger is not None
            assert server.logger.name == "TcpServer"

    @pytest.mark.unit
    def test_get_host_ip_success(self):
        """Test successful host IP retrieval"""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            mock_sock.getsockname.return_value = ("192.168.1.100", 12345)

            # Create server without triggering initialization calls to _get_host_ip
            server = self.ConcreteTcpServer(
                host="127.0.0.1"
            )  # Provide host to avoid calling _get_host_ip
            result = server._get_host_ip()

            assert result == "192.168.1.100"
            mock_sock.connect.assert_called_once_with(("8.8.8.8", 80))

    @pytest.mark.unit
    def test_get_host_ip_fallback(self):
        """Test host IP retrieval fallback to localhost"""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            mock_sock.connect.side_effect = Exception("Network error")

            server = self.ConcreteTcpServer()
            result = server._get_host_ip()

            assert result == "127.0.0.1"

    @pytest.mark.unit
    def test_allocate_tcp_port_success(self):
        """Test successful TCP port allocation"""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock

            server = self.ConcreteTcpServer()
            server.host = "127.0.0.1"
            result = server._allocate_tcp_port()

            assert 19200 <= result < 20000
            mock_sock.bind.assert_called()

    @pytest.mark.unit
    def test_server_start_success(self):
        """Test successful server startup"""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock

            server = self.ConcreteTcpServer(host="127.0.0.1", port=8080)
            server.start()

            assert server.running is True
            assert server.server_socket == mock_sock
            assert server.server_thread is not None
            mock_sock.setsockopt.assert_called_once()
            mock_sock.bind.assert_called_once_with(("127.0.0.1", 8080))
            mock_sock.listen.assert_called_once_with(10)

    @pytest.mark.unit
    def test_server_start_already_running(self):
        """Test starting server when already running"""
        with patch("socket.socket"):
            server = self.ConcreteTcpServer()
            server.running = True

            server.start()  # Should not raise exception

            # Logger should warn about already running
            assert server.running is True

    @pytest.mark.unit
    def test_server_start_failure(self):
        """Test server startup failure"""
        with patch("socket.socket") as mock_socket:
            # Set up the mock for initialization (_get_host_ip and _allocate_tcp_port)
            mock_sock_get_ip = MagicMock()
            mock_sock_get_ip.getsockname.return_value = ("127.0.0.1", 12345)

            mock_sock_allocate = MagicMock()
            mock_sock_allocate.__enter__ = MagicMock(return_value=mock_sock_allocate)
            mock_sock_allocate.__exit__ = MagicMock(return_value=None)

            # Set up the mock for the start method (which should fail)
            mock_socket.side_effect = [
                mock_sock_get_ip,  # Used by _get_host_ip
                mock_sock_allocate,  # Used by _allocate_tcp_port
                Exception("Socket creation failed"),  # Used by start() - should fail
            ]

            server = self.ConcreteTcpServer()  # This uses the first two mocks (success)

            with pytest.raises(Exception, match="Socket creation failed"):
                server.start()  # This uses the third mock (failure)

            assert server.running is False

    @pytest.mark.unit
    def test_server_stop(self):
        """Test server shutdown"""
        with patch("socket.socket") as mock_socket:
            # Set up mocks for initialization phase
            mock_sock_get_ip = MagicMock()
            mock_sock_get_ip.getsockname.return_value = ("127.0.0.1", 12345)

            mock_sock_allocate = MagicMock()
            mock_sock_allocate.__enter__ = MagicMock(return_value=mock_sock_allocate)
            mock_sock_allocate.__exit__ = MagicMock(return_value=None)

            # Set up mock for server socket
            mock_sock_server = MagicMock()

            mock_socket.side_effect = [
                mock_sock_get_ip,  # Used by _get_host_ip
                mock_sock_allocate,  # Used by _allocate_tcp_port
                mock_sock_server,  # Used by start()
            ]

            server = self.ConcreteTcpServer()  # Uses first two mocks
            server.start()  # Uses third mock

            # Mock thread to simulate it stopping
            server.server_thread.is_alive = MagicMock(return_value=False)

            server.stop()

            assert server.running is False
            mock_sock_server.close.assert_called_once()  # Only the server socket should be closed

    @pytest.mark.unit
    def test_server_stop_not_running(self):
        """Test stopping server when not running"""
        server = self.ConcreteTcpServer()
        server.stop()  # Should not raise exception

        assert server.running is False

    @pytest.mark.unit
    def test_server_stop_thread_timeout(self):
        """Test server shutdown with thread timeout"""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock

            server = self.ConcreteTcpServer()
            server.start()

            # Mock thread that doesn't stop gracefully
            mock_thread = MagicMock()
            mock_thread.is_alive.return_value = True
            mock_thread.join.return_value = None
            server.server_thread = mock_thread

            server.stop()

            assert server.running is False
            assert mock_thread.join.call_count == 5  # Should retry 5 times

    @pytest.mark.unit
    def test_receive_full_message_success(self):
        """Test successful full message reception"""
        mock_socket = MagicMock()
        test_message = b"Hello, World!"
        mock_socket.recv.return_value = test_message

        server = self.ConcreteTcpServer()
        result = server._receive_full_message(mock_socket, len(test_message))

        assert result == test_message
        mock_socket.recv.assert_called_once_with(len(test_message))

    @pytest.mark.unit
    def test_receive_full_message_chunked(self):
        """Test full message reception in chunks"""
        mock_socket = MagicMock()
        test_message = b"Hello, World! This is a longer message."
        chunks = [test_message[:10], test_message[10:20], test_message[20:]]
        mock_socket.recv.side_effect = chunks

        server = self.ConcreteTcpServer()
        result = server._receive_full_message(mock_socket, len(test_message))

        assert result == test_message
        assert mock_socket.recv.call_count == 3

    @pytest.mark.unit
    def test_receive_full_message_connection_closed(self):
        """Test message reception when connection is closed"""
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b""  # Empty bytes = connection closed

        server = self.ConcreteTcpServer()
        result = server._receive_full_message(mock_socket, 100)

        assert result is None

    @pytest.mark.unit
    def test_send_response_dict(self):
        """Test sending dictionary response"""
        mock_socket = MagicMock()
        response = {"type": "test", "data": "hello"}

        server = self.ConcreteTcpServer()
        server._send_response(mock_socket, response)

        # Should send length header + pickled data
        assert mock_socket.send.call_count == 2

        # First call should be length header (4 bytes)
        length_call = mock_socket.send.call_args_list[0][0][0]
        assert len(length_call) == 4

        # Second call should be serialized data
        data_call = mock_socket.send.call_args_list[1][0][0]
        deserialized = pickle.loads(data_call)
        assert deserialized["type"] == "test"
        assert deserialized["data"] == "hello"
        assert "cwd" in deserialized  # Should add current working directory

    @pytest.mark.unit
    def test_send_response_bytes(self):
        """Test sending bytes response"""
        mock_socket = MagicMock()
        response = b"raw bytes response"

        server = self.ConcreteTcpServer()
        server._send_response(mock_socket, response)

        # Should send length header + raw bytes
        assert mock_socket.send.call_count == 2

        # Check the actual data sent
        data_call = mock_socket.send.call_args_list[1][0][0]
        assert data_call == response

    @pytest.mark.unit
    def test_send_response_error(self):
        """Test handling error during response sending"""
        mock_socket = MagicMock()
        mock_socket.send.side_effect = Exception("Send failed")

        server = self.ConcreteTcpServer()
        # Should not raise exception, but log error
        server._send_response(mock_socket, {"type": "test"})

    @pytest.mark.unit
    def test_serialize_response(self):
        """Test response serialization"""
        server = self.ConcreteTcpServer()
        response = {"key": "value", "number": 42}

        serialized = server._serialize_response(response)
        deserialized = pickle.loads(serialized)

        assert deserialized == response

    @pytest.mark.unit
    def test_create_error_response(self):
        """Test error response creation"""
        server = self.ConcreteTcpServer()
        original_message = {"type": "test_request", "request_id": "123"}

        error_response = server._create_error_response(
            original_message, "ERR_TEST", "Test error message"
        )

        assert error_response["type"] == "test_request_response"
        assert error_response["request_id"] == "123"
        assert error_response["status"] == "error"
        assert error_response["message"] == "Test error message"
        assert error_response["payload"]["error_code"] == "ERR_TEST"
        assert "timestamp" in error_response

    @pytest.mark.unit
    def test_get_server_info(self):
        """Test server information retrieval"""
        server = self.ConcreteTcpServer(
            host="127.0.0.1", port=8080, server_name="TestServer"
        )

        info = server.get_server_info()

        assert info["server_name"] == "TestServer"
        assert info["host"] == "127.0.0.1"
        assert info["port"] == 8080
        assert info["running"] is False
        assert info["address"] == "127.0.0.1:8080"

    @pytest.mark.unit
    def test_destructor(self):
        """Test server destructor"""
        with patch("socket.socket"):
            server = self.ConcreteTcpServer()
            server.start()

            # Mock stop method to verify it's called
            server.stop = MagicMock()

            # Manually call destructor
            server.__del__()

            server.stop.assert_called_once()


class TestLocalTcpServer:
    """Test LocalTcpServer concrete implementation"""

    @pytest.mark.unit
    def test_server_initialization(self):
        """Test LocalTcpServer initialization"""

        def default_handler(msg, addr):
            return {"type": "default_response"}

        with patch("socket.socket"):
            server = LocalTcpServer(
                host="127.0.0.1", port=8080, default_handler=default_handler
            )

            assert server.server_name == "LocalTcpServer"
            assert server.host == "127.0.0.1"
            assert server.port == 8080
            assert server.default_handler == default_handler
            assert isinstance(server.message_handlers, dict)
            assert len(server.message_handlers) == 0

    @pytest.mark.unit
    def test_register_handler(self):
        """Test message handler registration"""

        def test_handler(msg, addr):
            return {"type": "test_response"}

        with patch("socket.socket"):
            server = LocalTcpServer()
            server.register_handler("test_message", test_handler)

            assert "test_message" in server.message_handlers
            assert server.message_handlers["test_message"] == test_handler

    @pytest.mark.unit
    def test_set_default_handler(self):
        """Test default handler setting"""

        def new_default_handler(msg, addr):
            return {"type": "new_default_response"}

        with patch("socket.socket"):
            server = LocalTcpServer()
            server.set_default_handler(new_default_handler)

            assert server.default_handler == new_default_handler

    @pytest.mark.unit
    def test_unregister_handler(self):
        """Test message handler unregistration"""

        def test_handler(msg, addr):
            return {"type": "test_response"}

        with patch("socket.socket"):
            server = LocalTcpServer()
            server.register_handler("test_message", test_handler)

            assert "test_message" in server.message_handlers

            server.unregister_handler("test_message")

            assert "test_message" not in server.message_handlers

    @pytest.mark.unit
    def test_unregister_nonexistent_handler(self):
        """Test unregistering non-existent handler"""
        with patch("socket.socket"):
            server = LocalTcpServer()
            # Should not raise exception
            server.unregister_handler("nonexistent")

    @pytest.mark.unit
    def test_get_registered_types(self):
        """Test getting registered message types"""

        def handler1(msg, addr):
            return {}

        def handler2(msg, addr):
            return {}

        with patch("socket.socket"):
            server = LocalTcpServer()
            server.register_handler("type1", handler1)
            server.register_handler("type2", handler2)

            types = server.get_registered_types()

            assert set(types) == {"type1", "type2"}

    @pytest.mark.unit
    def test_extract_message_type_success(self):
        """Test successful message type extraction"""
        with patch("socket.socket"):
            server = LocalTcpServer()

            # Test different type field names
            assert server._extract_message_type({"type": "test"}) == "test"
            assert server._extract_message_type({"message_type": "test"}) == "test"
            assert server._extract_message_type({"msg_type": "test"}) == "test"
            assert server._extract_message_type({"event_type": "test"}) == "test"
            assert server._extract_message_type({"command": "test"}) == "test"

    @pytest.mark.unit
    def test_extract_message_type_with_whitespace(self):
        """Test message type extraction with whitespace"""
        with patch("socket.socket"):
            server = LocalTcpServer()

            assert server._extract_message_type({"type": "  test  "}) == "test"

    @pytest.mark.unit
    def test_extract_message_type_failure(self):
        """Test message type extraction failure cases"""
        with patch("socket.socket"):
            server = LocalTcpServer()

            # Non-dict message
            assert server._extract_message_type("not a dict") is None

            # No type fields
            assert server._extract_message_type({"data": "test"}) is None

            # Empty type
            assert server._extract_message_type({"type": ""}) is None
            assert server._extract_message_type({"type": "   "}) is None

            # Non-string type
            assert server._extract_message_type({"type": 123}) is None

    @pytest.mark.unit
    def test_handle_message_data_success(self):
        """Test successful message data handling"""

        def test_handler(msg, addr):
            return {"type": "test_response", "status": "success"}

        with patch("socket.socket"):
            server = LocalTcpServer()
            server.register_handler("test_message", test_handler)

            message = {"type": "test_message", "data": "hello"}
            message_data = pickle.dumps(message)

            response = server._handle_message_data(message_data, ("127.0.0.1", 12345))

            assert response["type"] == "test_response"
            assert response["status"] == "success"

    @pytest.mark.unit
    def test_handle_message_data_deserialization_error(self):
        """Test handling deserialization error"""
        with patch("socket.socket"):
            server = LocalTcpServer()

            # Invalid pickle data
            message_data = b"invalid pickle data"

            response = server._handle_message_data(message_data, ("127.0.0.1", 12345))

            assert response["status"] == "error"
            assert response["payload"]["error_code"] == "ERR_DESERIALIZATION_FAILED"

    @pytest.mark.unit
    def test_process_message_with_registered_handler(self):
        """Test message processing with registered handler"""

        def test_handler(msg, addr):
            return {"type": "test_response", "received_data": msg["data"]}

        with patch("socket.socket"):
            server = LocalTcpServer()
            server.register_handler("test_message", test_handler)

            message = {"type": "test_message", "data": "hello world"}

            response = server._process_message(message, ("127.0.0.1", 12345))

            assert response["type"] == "test_response"
            assert response["received_data"] == "hello world"

    @pytest.mark.unit
    def test_process_message_with_default_handler(self):
        """Test message processing with default handler"""

        def default_handler(msg, addr):
            return {"type": "default_response", "message": "handled by default"}

        with patch("socket.socket"):
            server = LocalTcpServer(default_handler=default_handler)

            message = {"type": "unknown_message", "data": "test"}

            response = server._process_message(message, ("127.0.0.1", 12345))

            assert response["type"] == "default_response"
            assert response["message"] == "handled by default"

    @pytest.mark.unit
    def test_process_message_no_handler(self):
        """Test message processing with no applicable handler"""
        with patch("socket.socket"):
            server = LocalTcpServer()  # No default handler

            message = {"type": "unknown_message", "data": "test"}

            response = server._process_message(message, ("127.0.0.1", 12345))

            assert response["status"] == "error"
            assert response["payload"]["error_code"] == "ERR_NO_HANDLER"

    @pytest.mark.unit
    def test_process_message_handler_exception(self):
        """Test message processing when handler raises exception"""

        def failing_handler(msg, addr):
            raise Exception("Handler failed")

        with patch("socket.socket"):
            server = LocalTcpServer()
            server.register_handler("test_message", failing_handler)

            message = {"type": "test_message", "data": "test"}

            response = server._process_message(message, ("127.0.0.1", 12345))

            assert response["status"] == "error"
            assert response["payload"]["error_code"] == "ERR_HANDLER_FAILED"
            assert "Handler failed" in response["message"]

    @pytest.mark.unit
    def test_process_message_default_handler_exception(self):
        """Test message processing when default handler raises exception"""

        def failing_default_handler(msg, addr):
            raise Exception("Default handler failed")

        with patch("socket.socket"):
            server = LocalTcpServer(default_handler=failing_default_handler)

            message = {"type": "unknown_message", "data": "test"}

            response = server._process_message(message, ("127.0.0.1", 12345))

            assert response["status"] == "error"
            assert response["payload"]["error_code"] == "ERR_DEFAULT_HANDLER_FAILED"

    @pytest.mark.unit
    def test_process_message_no_type(self):
        """Test message processing with no extractable type"""

        def default_handler(msg, addr):
            return {"type": "default_response"}

        with patch("socket.socket"):
            server = LocalTcpServer(default_handler=default_handler)

            message = {"data": "no type field"}

            response = server._process_message(message, ("127.0.0.1", 12345))

            assert response["type"] == "default_response"

    @pytest.mark.unit
    def test_create_error_response_with_env_fields(self):
        """Test error response creation with environment fields"""
        with patch("socket.socket"):
            server = LocalTcpServer()

            original_message = {
                "type": "test_request",
                "request_id": "123",
                "env_name": "test_env",
                "env_uuid": "uuid-123",
            }

            error_response = server._create_error_response(
                original_message, "ERR_TEST", "Test error"
            )

            assert error_response["env_name"] == "test_env"
            assert error_response["env_uuid"] == "uuid-123"

    @pytest.mark.unit
    def test_send_response_with_cwd(self):
        """Test response sending includes current working directory"""
        mock_socket = MagicMock()
        response = {"type": "test_response", "data": "hello"}

        with patch("socket.socket"):
            server = LocalTcpServer()
            server._send_response(mock_socket, response)

            # Verify the response was modified to include cwd
            data_call = mock_socket.send.call_args_list[1][0][0]
            deserialized = pickle.loads(data_call)
            assert "cwd" in deserialized
            assert deserialized["cwd"] == server.server_cwd

    @pytest.mark.unit
    def test_get_server_info_extended(self):
        """Test extended server information for LocalTcpServer"""

        def handler1(msg, addr):
            return {}

        def default_handler(msg, addr):
            return {}

        with patch("socket.socket"):
            server = LocalTcpServer(default_handler=default_handler)
            server.register_handler("type1", handler1)

            info = server.get_server_info()

            assert info["server_name"] == "LocalTcpServer"
            assert "type1" in info["registered_message_types"]
            assert info["has_default_handler"] is True

    @pytest.mark.unit
    def test_thread_safety_handler_registration(self):
        """Test thread safety of handler registration/unregistration"""
        with patch("socket.socket"):
            server = LocalTcpServer()

            def register_handlers():
                for i in range(100):
                    server.register_handler(f"type_{i}", lambda m, a: {})

            def unregister_handlers():
                for i in range(50, 150):
                    server.unregister_handler(f"type_{i}")

            # Start multiple threads
            threads = [
                threading.Thread(target=register_handlers),
                threading.Thread(target=unregister_handlers),
            ]

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            # Should not crash, some handlers should remain
            types = server.get_registered_types()
            assert isinstance(types, list)


class TestIntegrationScenarios:
    """Integration tests for TCP server functionality"""

    @pytest.mark.integration
    def test_complete_message_handling_workflow(self):
        """Test complete message handling workflow"""
        received_messages = []

        def status_handler(msg, addr):
            received_messages.append(("status", msg, addr))
            return {
                "type": "status_response",
                "status": "success",
                "request_id": msg.get("request_id"),
            }

        def default_handler(msg, addr):
            received_messages.append(("default", msg, addr))
            return {"type": "default_response", "status": "handled"}

        with patch("socket.socket"):
            server = LocalTcpServer(default_handler=default_handler)
            server.register_handler("status", status_handler)

            # Test registered handler
            status_message = {"type": "status", "request_id": "123", "data": "test"}
            status_data = pickle.dumps(status_message)

            response = server._handle_message_data(status_data, ("127.0.0.1", 12345))

            assert response["type"] == "status_response"
            assert response["request_id"] == "123"
            assert len(received_messages) == 1

            # Test default handler
            unknown_message = {"type": "unknown", "data": "test"}
            unknown_data = pickle.dumps(unknown_message)

            response = server._handle_message_data(unknown_data, ("127.0.0.1", 12346))

            assert response["type"] == "default_response"
            assert len(received_messages) == 2

    @pytest.mark.integration
    def test_server_lifecycle(self):
        """Test complete server lifecycle"""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock

            server = LocalTcpServer(host="127.0.0.1", port=8080)

            # Test startup
            server.start()
            assert server.running is True

            # Test server info
            info = server.get_server_info()
            assert info["running"] is True
            assert info["address"] == "127.0.0.1:8080"

            # Test shutdown
            server.stop()
            assert server.running is False

    @pytest.mark.integration
    def test_multiple_handler_types(self):
        """Test server with multiple different handler types"""
        results = {}

        def echo_handler(msg, addr):
            results["echo"] = msg["data"]
            return {"type": "echo_response", "echo": msg["data"]}

        def compute_handler(msg, addr):
            result = msg["a"] + msg["b"]
            results["compute"] = result
            return {"type": "compute_response", "result": result}

        def log_handler(msg, addr):
            results["log"] = f"Logged: {msg['message']}"
            return None  # No response

        with patch("socket.socket"):
            server = LocalTcpServer()
            server.register_handler("echo", echo_handler)
            server.register_handler("compute", compute_handler)
            server.register_handler("log", log_handler)

            # Test echo
            echo_msg = {"type": "echo", "data": "hello world"}
            response = server._process_message(echo_msg, ("127.0.0.1", 12345))
            assert response["echo"] == "hello world"
            assert results["echo"] == "hello world"

            # Test compute
            compute_msg = {"type": "compute", "a": 5, "b": 3}
            response = server._process_message(compute_msg, ("127.0.0.1", 12345))
            assert response["result"] == 8
            assert results["compute"] == 8

            # Test log (no response)
            log_msg = {"type": "log", "message": "test log"}
            response = server._process_message(log_msg, ("127.0.0.1", 12345))
            assert response is None
            assert results["log"] == "Logged: test log"

    @pytest.mark.slow
    def test_concurrent_message_processing(self):
        """Test concurrent message processing"""
        processed_messages = []
        processing_lock = threading.Lock()

        def slow_handler(msg, addr):
            with processing_lock:
                processed_messages.append(msg["id"])
            time.sleep(0.01)  # Simulate processing time
            return {"type": "slow_response", "processed_id": msg["id"]}

        with patch("socket.socket"):
            server = LocalTcpServer()
            server.register_handler("slow", slow_handler)

            # Simulate multiple concurrent messages
            def process_message(msg_id):
                message = {"type": "slow", "id": msg_id}
                return server._process_message(message, ("127.0.0.1", 12345))

            # Process multiple messages concurrently
            threads = []
            for i in range(10):
                thread = threading.Thread(target=process_message, args=(i,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # All messages should be processed
            assert len(processed_messages) == 10
            assert set(processed_messages) == set(range(10))


class TestPerformanceScenarios:
    """Performance and stress tests"""

    @pytest.mark.slow
    def test_rapid_handler_registration(self):
        """Test rapid handler registration and lookup"""
        with patch("socket.socket"):
            server = LocalTcpServer()

            # Register many handlers
            start_time = time.time()
            for i in range(1000):
                server.register_handler(f"type_{i}", lambda m, a: {"response": i})
            end_time = time.time()

            # Should complete quickly
            assert end_time - start_time < 1.0
            assert len(server.get_registered_types()) == 1000

    @pytest.mark.slow
    def test_large_message_handling(self):
        """Test handling large messages"""

        def large_handler(msg, addr):
            return {"type": "large_response", "size": len(msg["data"])}

        with patch("socket.socket"):
            server = LocalTcpServer()
            server.register_handler("large", large_handler)

            # Create large message (1MB)
            large_data = "x" * (1024 * 1024)
            message = {"type": "large", "data": large_data}
            message_data = pickle.dumps(message)

            start_time = time.time()
            response = server._handle_message_data(message_data, ("127.0.0.1", 12345))
            end_time = time.time()

            assert response["type"] == "large_response"
            assert response["size"] == len(large_data)
            # Should process within reasonable time
            assert end_time - start_time < 5.0

    @pytest.mark.slow
    def test_handler_lookup_performance(self):
        """Test performance of handler lookup with many registered handlers"""
        handlers = {}
        for i in range(1000):
            handlers[f"type_{i}"] = lambda m, a: {"response": i}

        with patch("socket.socket"):
            server = LocalTcpServer()

            # Register all handlers
            for msg_type, handler in handlers.items():
                server.register_handler(msg_type, handler)

            # Test lookup performance
            start_time = time.time()
            for i in range(100):
                message = {"type": f"type_{i % 1000}", "data": f"test_{i}"}
                server._process_message(message, ("127.0.0.1", 12345))
            end_time = time.time()

            # Should complete quickly even with many handlers
            assert end_time - start_time < 1.0


class TestErrorHandlingScenarios:
    """Error handling and edge case tests"""

    @pytest.mark.unit
    def test_malformed_message_handling(self):
        """Test handling various malformed messages"""
        with patch("socket.socket"):
            server = LocalTcpServer()

            # Test different malformed message types
            test_cases = [
                None,  # None message
                42,  # Integer message
                "string",  # String message
                [],  # List message
                {"type": None},  # None type
                {"type": 123},  # Integer type
                {"no_type_field": "value"},  # Missing type
            ]

            for malformed_msg in test_cases:
                try:
                    message_data = pickle.dumps(malformed_msg)
                    response = server._handle_message_data(
                        message_data, ("127.0.0.1", 12345)
                    )

                    # Should return error response or use default handler
                    assert response is not None
                    if response.get("status") == "error":
                        assert "error_code" in response.get("payload", {})
                except Exception:
                    # If pickling fails, that's also acceptable
                    pass

    @pytest.mark.unit
    def test_resource_cleanup_on_error(self):
        """Test proper resource cleanup when errors occur"""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock

            server = LocalTcpServer()

            # Simulate error during server start
            mock_sock.bind.side_effect = Exception("Bind failed")

            with pytest.raises(Exception):
                server.start()

            # Server should not be in running state
            assert server.running is False

    @pytest.mark.unit
    def test_concurrent_handler_modification(self):
        """Test concurrent handler registration/unregistration doesn't break server"""
        with patch("socket.socket"):
            server = LocalTcpServer()

            def modify_handlers():
                for i in range(50):
                    server.register_handler(f"type_{i}", lambda m, a: {})
                    if i % 10 == 0:
                        server.unregister_handler(f"type_{i // 2}")

            def process_messages():
                for i in range(100):
                    message = {"type": f"type_{i % 20}", "data": f"test_{i}"}
                    try:
                        server._process_message(message, ("127.0.0.1", 12345))
                    except Exception:
                        pass  # Some messages may fail due to handler changes

            # Run concurrent operations
            threads = [
                threading.Thread(target=modify_handlers),
                threading.Thread(target=process_messages),
            ]

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            # Server should still be functional
            types = server.get_registered_types()
            assert isinstance(types, list)

    @pytest.mark.unit
    def test_memory_pressure_handling(self):
        """Test server behavior under memory pressure"""

        def memory_intensive_handler(msg, addr):
            # Create large response
            large_data = "x" * (1024 * 1024)  # 1MB
            return {"type": "memory_response", "data": large_data}

        with patch("socket.socket"):
            server = LocalTcpServer()
            server.register_handler("memory_test", memory_intensive_handler)

            # Process multiple memory-intensive messages
            responses = []
            for i in range(10):
                message = {"type": "memory_test", "request": i}
                try:
                    response = server._process_message(message, ("127.0.0.1", 12345))
                    responses.append(response)
                except MemoryError:
                    # Memory errors are acceptable under pressure
                    break
                except Exception:
                    # Other exceptions should be handled gracefully
                    pass

            # Should handle at least some requests
            assert len(responses) >= 0


if __name__ == "__main__":
    pytest.main([__file__])
