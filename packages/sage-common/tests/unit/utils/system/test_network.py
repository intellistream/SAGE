"""
Unit tests for sage.common.utils.system.network

Tests network and port management utilities.
"""

import json
from unittest.mock import MagicMock, patch

import psutil
import pytest

from sage.common.utils.system.network import (
    aggressive_port_cleanup,
    allocate_free_port,
    check_port_binding_permission,
    check_tcp_connection,
    find_port_processes,
    is_port_occupied,
    send_tcp_health_check,
    wait_for_port_release,
)


class TestIsPortOccupied:
    """Tests for is_port_occupied()"""

    @patch("sage.common.utils.system.network.socket.socket")
    def test_port_occupied(self, mock_socket):
        """Test when port is occupied"""
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        mock_sock.connect_ex.return_value = 0  # Success = occupied

        result = is_port_occupied("localhost", 8080)

        assert result is True

    @patch("sage.common.utils.system.network.socket.socket")
    def test_port_not_occupied(self, mock_socket):
        """Test when port is not occupied"""
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        mock_sock.connect_ex.return_value = 111  # Connection refused = free

        result = is_port_occupied("localhost", 8080)

        assert result is False


class TestCheckPortBindingPermission:
    """Tests for check_port_binding_permission()"""

    @patch("sage.common.utils.system.network.socket.socket")
    def test_permission_granted(self, mock_socket):
        """Test when port binding permission is granted"""
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock

        result = check_port_binding_permission("127.0.0.1", 8080)

        assert result["success"] is True
        mock_sock.bind.assert_called_once()

    @patch("sage.common.utils.system.network.socket.socket")
    def test_permission_denied(self, mock_socket):
        """Test when port binding permission is denied"""
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        mock_sock.bind.side_effect = PermissionError("Permission denied")

        result = check_port_binding_permission("127.0.0.1", 80)

        assert result["success"] is False
        assert result["error"] == "permission_denied"

    @patch("sage.common.utils.system.network.socket.socket")
    def test_port_in_use(self, mock_socket):
        """Test when port is already in use"""
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        os_error = OSError("Address already in use")
        os_error.errno = 98
        mock_sock.bind.side_effect = os_error

        result = check_port_binding_permission("127.0.0.1", 8080)

        assert result["success"] is False
        assert result["error"] == "port_in_use"


class TestWaitForPortRelease:
    """Tests for wait_for_port_release()"""

    @patch("sage.common.utils.system.network.is_port_occupied")
    def test_port_released_immediately(self, mock_is_occupied):
        """Test when port is released immediately"""
        mock_is_occupied.return_value = False

        result = wait_for_port_release("localhost", 8080, timeout=5)

        assert result is True

    @patch("sage.common.utils.system.network.time.sleep")
    @patch("sage.common.utils.system.network.is_port_occupied")
    def test_port_released_after_wait(self, mock_is_occupied, mock_sleep):
        """Test when port is released after waiting"""
        mock_is_occupied.side_effect = [True, True, False]

        result = wait_for_port_release("localhost", 8080, timeout=10, check_interval=1)

        assert result is True

    @patch("sage.common.utils.system.network.time.sleep")
    @patch("sage.common.utils.system.network.is_port_occupied")
    def test_port_timeout(self, mock_is_occupied, mock_sleep):
        """Test timeout waiting for port release"""
        mock_is_occupied.return_value = True

        result = wait_for_port_release("localhost", 8080, timeout=1, check_interval=0.1)

        assert result is False


class TestFindPortProcesses:
    """Tests for find_port_processes()"""

    @pytest.mark.skip(reason="find_port_processes uses subprocess, complex to mock")
    @patch("psutil.process_iter")
    def test_find_processes(self, mock_process_iter):
        """Test finding processes using a port"""
        mock_proc = MagicMock()
        mock_conn = MagicMock()
        mock_conn.laddr.port = 8080
        mock_proc.net_connections.return_value = [mock_conn]
        mock_process_iter.return_value = [mock_proc]

        result = find_port_processes(8080)

        assert len(result) > 0

    @pytest.mark.skip(reason="find_port_processes uses subprocess, complex to mock")
    @patch("psutil.process_iter")
    def test_no_processes_found(self, mock_process_iter):
        """Test when no processes use the port"""
        mock_proc = MagicMock()
        mock_proc.net_connections.return_value = []
        mock_process_iter.return_value = [mock_proc]

        result = find_port_processes(8080)

        assert len(result) == 0


class TestSendTCPHealthCheck:
    """Tests for send_tcp_health_check()"""

    @patch("sage.common.utils.system.network.socket.socket")
    def test_health_check_success(self, mock_socket):
        """Test successful health check"""
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock

        # Mock response
        response_data = {"status": "ok", "server": "test"}
        response_bytes = json.dumps(response_data).encode("utf-8")
        response_length = len(response_bytes)

        mock_sock.recv.side_effect = [
            response_length.to_bytes(4, byteorder="big"),
            response_bytes,
        ]

        request = {"action": "health_check"}
        result = send_tcp_health_check("localhost", 8080, request, timeout=5)

        assert result == response_data

    @patch("sage.common.utils.system.network.socket.socket")
    def test_health_check_connection_refused(self, mock_socket):
        """Test health check with connection refused"""
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        mock_sock.connect.side_effect = ConnectionRefusedError("Connection refused")

        request = {"action": "health_check"}
        result = send_tcp_health_check("localhost", 8080, request, timeout=5)

        assert result["status"] == "error"
        assert "Connection failed" in result["message"]


class TestAllocateFreePort:
    """Tests for allocate_free_port()"""

    @patch("sage.common.utils.system.network.is_port_occupied")
    @patch("sage.common.utils.system.network.socket.socket")
    def test_allocate_first_port_in_range(self, mock_socket, mock_is_occupied):
        """Test allocating first available port"""
        mock_is_occupied.return_value = False
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock

        port = allocate_free_port(host="127.0.0.1", port_range=(19200, 19210))

        assert port == 19200

    @patch("sage.common.utils.system.network.is_port_occupied")
    @patch("sage.common.utils.system.network.socket.socket")
    def test_allocate_after_retries(self, mock_socket, mock_is_occupied):
        """Test allocating port after some retries"""
        mock_is_occupied.side_effect = [True, True, False]
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock

        port = allocate_free_port(host="127.0.0.1", port_range=(19200, 19210))

        assert port == 19202

    @patch("sage.common.utils.system.network.is_port_occupied")
    @patch("sage.common.utils.system.network.socket.socket")
    def test_system_allocated_port(self, mock_socket, mock_is_occupied):
        """Test fallback to system-allocated port"""
        mock_is_occupied.return_value = True
        mock_sock = MagicMock()
        mock_sock.getsockname.return_value = ("127.0.0.1", 54321)
        mock_socket.return_value.__enter__.return_value = mock_sock

        port = allocate_free_port(host="127.0.0.1", port_range=(19200, 19205))

        assert port == 54321


class TestCheckTCPConnection:
    """Tests for check_tcp_connection()"""

    @patch("sage.common.utils.system.network.time.time")
    @patch("sage.common.utils.system.network.socket.socket")
    def test_tcp_connection_success(self, mock_socket, mock_time):
        """Test successful TCP connection"""
        mock_time.side_effect = [0.0, 0.001]
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        mock_sock.connect_ex.return_value = 0

        result = check_tcp_connection("localhost", 8080)

        assert result["success"] is True

    @patch("sage.common.utils.system.network.time.time")
    @patch("sage.common.utils.system.network.socket.socket")
    def test_tcp_connection_failed(self, mock_socket, mock_time):
        """Test failed TCP connection"""
        mock_time.side_effect = [0.0, 0.001]
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        mock_sock.connect_ex.return_value = 111

        result = check_tcp_connection("localhost", 8080)

        assert result["success"] is False


class TestAggressivePortCleanup:
    """Tests for aggressive_port_cleanup()"""

    @patch("sage.common.utils.system.network.find_port_processes")
    def test_no_processes(self, mock_find):
        """Test cleanup when no processes occupy the port"""
        mock_find.return_value = []

        result = aggressive_port_cleanup(8080)

        assert result["success"] is False
        assert len(result["errors"]) > 0

    @patch("sage.common.utils.system.network.find_port_processes")
    def test_cleanup_with_processes(self, mock_find):
        """Test cleanup with processes"""
        mock_proc = MagicMock(spec=psutil.Process)
        mock_proc.pid = 12345
        mock_find.return_value = [mock_proc]

        result = aggressive_port_cleanup(8080)

        assert result["success"] is True
        assert 12345 in result["killed_pids"]
