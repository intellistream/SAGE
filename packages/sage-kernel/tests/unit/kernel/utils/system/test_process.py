"""
Test suite for sage.common.utils.system.process module

This module tests process management utilities including process discovery,
termination, tree operations, and sudo privilege management.

Created: 2024
Test Framework: pytest
Coverage: Process management, sudo operations, system monitoring
"""

import getpass
import os
import subprocess
import time
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, call, patch

import psutil
import pytest
from sage.common.utils.system.process import (SudoManager,
                                              check_process_ownership,
                                              create_sudo_manager,
                                              find_processes_by_name,
                                              get_process_children,
                                              get_process_info,
                                              get_system_process_summary,
                                              is_process_running,
                                              kill_process_with_sudo,
                                              terminate_process,
                                              terminate_process_tree,
                                              terminate_processes_by_name,
                                              verify_sudo_password,
                                              wait_for_process_termination)


class TestFindProcessesByName:
    """Test process discovery by name functionality"""

    @pytest.mark.unit
    def test_find_by_process_name(self):
        """Test finding processes by exact name"""
        mock_processes = [
            {"pid": 1234, "name": "python", "cmdline": ["python", "script.py"]},
            {"pid": 5678, "name": "java", "cmdline": ["java", "-jar", "app.jar"]},
            {"pid": 9999, "name": "python3", "cmdline": ["python3", "test.py"]},
        ]

        def mock_proc_iter(attrs):
            mock_procs = []
            for proc_data in mock_processes:
                mock_proc = MagicMock()
                mock_proc.info = proc_data
                mock_procs.append(mock_proc)
            return mock_procs

        with patch("psutil.process_iter", side_effect=mock_proc_iter):
            result = find_processes_by_name(["python"])

            assert len(result) == 2  # python and python3
            assert all(hasattr(proc, "info") for proc in result)

    @pytest.mark.unit
    def test_find_by_cmdline_pattern(self):
        """Test finding processes by command line pattern"""
        mock_processes = [
            {"pid": 1234, "name": "java", "cmdline": ["java", "-jar", "app.jar"]},
            {"pid": 5678, "name": "python", "cmdline": ["python", "server.py"]},
        ]

        def mock_proc_iter(attrs):
            mock_procs = []
            for proc_data in mock_processes:
                mock_proc = MagicMock()
                mock_proc.info = proc_data
                mock_procs.append(mock_proc)
            return mock_procs

        with patch("psutil.process_iter", side_effect=mock_proc_iter):
            result = find_processes_by_name(["app.jar"])

            assert len(result) == 1
            assert result[0].info["pid"] == 1234

    @pytest.mark.unit
    def test_no_matching_processes(self):
        """Test when no processes match the criteria"""
        mock_processes = [
            {"pid": 1234, "name": "bash", "cmdline": ["bash"]},
        ]

        def mock_proc_iter(attrs):
            mock_procs = []
            for proc_data in mock_processes:
                mock_proc = MagicMock()
                mock_proc.info = proc_data
                mock_procs.append(mock_proc)
            return mock_procs

        with patch("psutil.process_iter", side_effect=mock_proc_iter):
            result = find_processes_by_name(["nonexistent"])

            assert len(result) == 0

    @pytest.mark.unit
    def test_handle_process_exceptions(self):
        """Test handling process access exceptions"""

        def mock_proc_iter(attrs):
            mock_proc1 = MagicMock()
            mock_proc1.info = {"pid": 1234, "name": "python", "cmdline": ["python"]}

            mock_proc2 = MagicMock()
            # When accessing info, raise AccessDenied
            mock_proc2.info = MagicMock()
            mock_proc2.info.__getitem__.side_effect = psutil.AccessDenied()

            mock_proc3 = MagicMock()
            # When accessing info, raise NoSuchProcess
            mock_proc3.info = MagicMock()
            mock_proc3.info.__getitem__.side_effect = psutil.NoSuchProcess(1234)

            return [mock_proc1, mock_proc2, mock_proc3]

        with patch("psutil.process_iter", side_effect=mock_proc_iter):
            result = find_processes_by_name(["python"])

            assert len(result) == 1  # Only the accessible process

    @pytest.mark.unit
    def test_empty_cmdline_handling(self):
        """Test handling processes with empty command lines"""
        mock_processes = [
            {"pid": 1234, "name": "kernel_process", "cmdline": None},
            {"pid": 5678, "name": "user_process", "cmdline": []},
        ]

        def mock_proc_iter(attrs):
            mock_procs = []
            for proc_data in mock_processes:
                mock_proc = MagicMock()
                mock_proc.info = proc_data
                mock_procs.append(mock_proc)
            return mock_procs

        with patch("psutil.process_iter", side_effect=mock_proc_iter):
            result = find_processes_by_name(["kernel_process"])

            assert len(result) == 1


class TestGetProcessInfo:
    """Test process information retrieval functionality"""

    @pytest.mark.unit
    def test_get_valid_process_info(self):
        """Test getting information for a valid process"""
        with patch("psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.name.return_value = "python"
            mock_proc.username.return_value = "testuser"
            mock_proc.cmdline.return_value = ["python", "script.py"]
            mock_proc.status.return_value = "running"
            mock_proc.cpu_percent.return_value = 15.5
            mock_proc.memory_percent.return_value = 2.3
            mock_proc.create_time.return_value = 1234567890
            mock_process.return_value = mock_proc

            result = get_process_info(1234)

            assert result["pid"] == 1234
            assert result["name"] == "python"
            assert result["user"] == "testuser"
            assert result["cmdline"] == "python script.py"
            assert result["status"] == "running"
            assert result["cpu_percent"] == 15.5
            assert result["memory_percent"] == 2.3
            assert result["create_time"] == 1234567890
            assert "error" not in result

    @pytest.mark.unit
    def test_process_not_found(self):
        """Test handling process not found"""
        with patch("psutil.Process", side_effect=psutil.NoSuchProcess(1234)):
            result = get_process_info(1234)

            assert result["pid"] == 1234
            assert result["status"] == "Not Found"
            assert result["error"] == "Process not found"

    @pytest.mark.unit
    def test_access_denied(self):
        """Test handling access denied"""
        with patch("psutil.Process", side_effect=psutil.AccessDenied(1234)):
            result = get_process_info(1234)

            assert result["pid"] == 1234
            assert result["status"] == "Access Denied"
            assert result["error"] == "Access denied"

    @pytest.mark.unit
    def test_unexpected_exception(self):
        """Test handling unexpected exceptions"""
        with patch("psutil.Process", side_effect=Exception("Unexpected error")):
            result = get_process_info(1234)

            assert result["pid"] == 1234
            assert "error" in result
            assert "Unexpected error" in result["error"]


class TestTerminateProcess:
    """Test process termination functionality"""

    @pytest.mark.unit
    def test_graceful_termination(self):
        """Test successful graceful termination"""
        with patch("psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_process.return_value = mock_proc

            with patch(
                "sage.common.utils.system.process.get_process_info"
            ) as mock_info:
                mock_info.return_value = {"pid": 1234, "name": "test_process"}

                result = terminate_process(1234)

                assert result["success"] is True
                assert result["method"] == "terminate"
                assert result["pid"] == 1234
                mock_proc.terminate.assert_called_once()
                mock_proc.wait.assert_called_once_with(timeout=5)

    @pytest.mark.unit
    def test_force_kill_after_timeout(self):
        """Test force kill when graceful termination times out"""
        with patch("psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.wait.side_effect = [psutil.TimeoutExpired(1234, 5), None]
            mock_process.return_value = mock_proc

            with patch(
                "sage.common.utils.system.process.get_process_info"
            ) as mock_info:
                mock_info.return_value = {"pid": 1234, "name": "test_process"}

                result = terminate_process(1234)

                assert result["success"] is True
                assert result["method"] == "kill"
                assert "killed after timeout" in result["message"]
                mock_proc.terminate.assert_called_once()
                mock_proc.kill.assert_called_once()

    @pytest.mark.unit
    def test_process_already_gone(self):
        """Test handling process that's already terminated"""
        with patch("psutil.Process", side_effect=psutil.NoSuchProcess(1234)):
            result = terminate_process(1234)

            assert result["success"] is True
            assert result["method"] == "already_gone"
            assert "already terminated" in result["message"]

    @pytest.mark.unit
    def test_access_denied_termination(self):
        """Test handling access denied during termination"""
        with patch("psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.terminate.side_effect = psutil.AccessDenied(1234)
            mock_process.return_value = mock_proc

            result = terminate_process(1234)

            assert result["success"] is False
            assert result["method"] == "access_denied"
            assert "Access denied" in result["error"]

    @pytest.mark.unit
    def test_custom_timeout(self):
        """Test termination with custom timeout"""
        with patch("psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_process.return_value = mock_proc

            with patch(
                "sage.common.utils.system.process.get_process_info"
            ) as mock_info:
                mock_info.return_value = {"pid": 1234, "name": "test_process"}

                terminate_process(1234, timeout=10)

                mock_proc.wait.assert_called_with(timeout=10)


class TestTerminateProcessesByName:
    """Test bulk process termination by name"""

    @pytest.mark.unit
    def test_terminate_multiple_processes(self):
        """Test terminating multiple processes by name"""
        mock_procs = [MagicMock(pid=1234), MagicMock(pid=5678)]

        with patch(
            "sage.common.utils.system.process.find_processes_by_name",
            return_value=mock_procs,
        ):
            with patch(
                "sage.common.utils.system.process.terminate_process"
            ) as mock_terminate:
                mock_terminate.side_effect = [
                    {"success": True, "method": "terminate", "pid": 1234},
                    {"success": True, "method": "kill", "pid": 5678},
                ]

                result = terminate_processes_by_name(["test_process"])

                assert result["total_found"] == 2
                assert len(result["terminated"]) == 2
                assert len(result["failed"]) == 0
                assert result["success"] is True

    @pytest.mark.unit
    def test_mixed_termination_results(self):
        """Test handling mixed success/failure results"""
        mock_procs = [MagicMock(pid=1234), MagicMock(pid=5678), MagicMock(pid=9999)]

        with patch(
            "sage.common.utils.system.process.find_processes_by_name",
            return_value=mock_procs,
        ):
            with patch(
                "sage.common.utils.system.process.terminate_process"
            ) as mock_terminate:
                mock_terminate.side_effect = [
                    {"success": True, "method": "terminate", "pid": 1234},
                    {"success": False, "method": "access_denied", "pid": 5678},
                    {"success": True, "method": "already_gone", "pid": 9999},
                ]

                result = terminate_processes_by_name(["test_process"])

                assert result["total_found"] == 3
                assert len(result["terminated"]) == 1
                assert len(result["failed"]) == 1
                assert len(result["already_gone"]) == 1
                assert result["success"] is False  # Due to one failure

    @pytest.mark.unit
    def test_no_processes_found(self):
        """Test when no processes are found"""
        with patch(
            "sage.common.utils.system.process.find_processes_by_name", return_value=[]
        ):
            result = terminate_processes_by_name(["nonexistent"])

            assert result["total_found"] == 0
            assert result["success"] is True  # No failures


class TestKillProcessWithSudo:
    """Test sudo-based process killing"""

    @pytest.mark.unit
    def test_successful_sudo_kill(self):
        """Test successful sudo kill"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="")

            result = kill_process_with_sudo(1234, "password123")

            assert result["success"] is True
            assert result["method"] == "sudo_kill"
            mock_run.assert_called_once_with(
                ["sudo", "-S", "kill", "-9", "1234"],
                input="password123\n",
                capture_output=True,
                text=True,
                timeout=10,
            )

    @pytest.mark.unit
    def test_sudo_kill_failed(self):
        """Test failed sudo kill"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1, stderr="kill: cannot find process"
            )

            result = kill_process_with_sudo(1234, "password123")

            assert result["success"] is False
            assert "Failed to kill process" in result["error"]

    @pytest.mark.unit
    def test_sudo_timeout(self):
        """Test sudo command timeout"""
        with patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired(["sudo"], 10)
        ):
            result = kill_process_with_sudo(1234, "password123")

            assert result["success"] is False
            assert "Timeout" in result["error"]

    @pytest.mark.unit
    def test_no_password_provided(self):
        """Test handling no password provided"""
        result = kill_process_with_sudo(1234, "")

        assert result["success"] is False
        assert "No sudo password provided" in result["error"]

    @pytest.mark.unit
    def test_prompt_for_password(self):
        """Test prompting for password when none provided"""
        with patch("getpass.getpass", return_value="prompted_password"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stderr="")

                result = kill_process_with_sudo(1234, None)

                assert result["success"] is True
                mock_run.assert_called_once()


class TestVerifySudoPassword:
    """Test sudo password verification"""

    @pytest.mark.unit
    def test_valid_password(self):
        """Test verifying valid sudo password"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = verify_sudo_password("correct_password")

            assert result is True
            mock_run.assert_called_once_with(
                ["sudo", "-S", "echo", "password_test"],
                input="correct_password\n",
                capture_output=True,
                text=True,
                timeout=10,
            )

    @pytest.mark.unit
    def test_invalid_password(self):
        """Test verifying invalid sudo password"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1)

            result = verify_sudo_password("wrong_password")

            assert result is False

    @pytest.mark.unit
    def test_verification_exception(self):
        """Test handling verification exceptions"""
        with patch("subprocess.run", side_effect=Exception("Network error")):
            result = verify_sudo_password("password")

            assert result is False


class TestGetProcessChildren:
    """Test process children discovery"""

    @pytest.mark.unit
    def test_get_children_recursive(self):
        """Test getting children recursively"""
        with patch("psutil.Process") as mock_process:
            mock_child1 = MagicMock(pid=1001)
            mock_child2 = MagicMock(pid=1002)
            mock_parent = MagicMock()
            mock_parent.children.return_value = [mock_child1, mock_child2]
            mock_process.return_value = mock_parent

            result = get_process_children(1234, recursive=True)

            assert result == [1001, 1002]
            mock_parent.children.assert_called_once_with(recursive=True)

    @pytest.mark.unit
    def test_get_children_non_recursive(self):
        """Test getting children non-recursively"""
        with patch("psutil.Process") as mock_process:
            mock_child = MagicMock(pid=1001)
            mock_parent = MagicMock()
            mock_parent.children.return_value = [mock_child]
            mock_process.return_value = mock_parent

            result = get_process_children(1234, recursive=False)

            assert result == [1001]
            mock_parent.children.assert_called_once_with(recursive=False)

    @pytest.mark.unit
    def test_process_not_found(self):
        """Test handling process not found"""
        with patch("psutil.Process", side_effect=psutil.NoSuchProcess(1234)):
            result = get_process_children(1234)

            assert result == []

    @pytest.mark.unit
    def test_no_children(self):
        """Test process with no children"""
        with patch("psutil.Process") as mock_process:
            mock_parent = MagicMock()
            mock_parent.children.return_value = []
            mock_process.return_value = mock_parent

            result = get_process_children(1234)

            assert result == []


class TestTerminateProcessTree:
    """Test process tree termination"""

    @pytest.mark.unit
    def test_terminate_tree_success(self):
        """Test successful process tree termination"""
        with patch(
            "sage.common.utils.system.process.get_process_children",
            return_value=[1001, 1002],
        ):
            with patch(
                "sage.common.utils.system.process.terminate_process"
            ) as mock_terminate:
                mock_terminate.side_effect = [
                    {"success": True, "method": "terminate", "pid": 1001},
                    {"success": True, "method": "terminate", "pid": 1002},
                    {"success": True, "method": "terminate", "pid": 1234},
                ]

                result = terminate_process_tree(1234)

                assert result["root_pid"] == 1234
                assert result["total_processes"] == 3
                assert len(result["terminated"]) == 3
                assert result["success"] is True

    @pytest.mark.unit
    def test_terminate_tree_partial_failure(self):
        """Test process tree termination with some failures"""
        with patch(
            "sage.common.utils.system.process.get_process_children", return_value=[1001]
        ):
            with patch(
                "sage.common.utils.system.process.terminate_process"
            ) as mock_terminate:
                mock_terminate.side_effect = [
                    {"success": False, "method": "access_denied", "pid": 1001},
                    {"success": True, "method": "terminate", "pid": 1234},
                ]

                result = terminate_process_tree(1234)

                assert result["total_processes"] == 2
                assert len(result["terminated"]) == 1
                assert len(result["failed"]) == 1
                assert result["success"] is False

    @pytest.mark.unit
    def test_no_children_process_tree(self):
        """Test terminating process with no children"""
        with patch(
            "sage.common.utils.system.process.get_process_children", return_value=[]
        ):
            with patch(
                "sage.common.utils.system.process.terminate_process"
            ) as mock_terminate:
                mock_terminate.return_value = {
                    "success": True,
                    "method": "terminate",
                    "pid": 1234,
                }

                result = terminate_process_tree(1234)

                assert result["total_processes"] == 1
                assert result["success"] is True


class TestWaitForProcessTermination:
    """Test process termination waiting"""

    @pytest.mark.unit
    def test_process_terminates_quickly(self):
        """Test process terminates within timeout"""
        with patch("psutil.Process", side_effect=psutil.NoSuchProcess(1234)):
            with patch("time.time", side_effect=[0, 1]):
                result = wait_for_process_termination(1234, timeout=10)

                assert result is True

    @pytest.mark.unit
    def test_process_stops_running(self):
        """Test process stops running but still exists"""
        with patch("psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.is_running.return_value = False
            mock_process.return_value = mock_proc

            with patch("time.time", side_effect=[0, 1]):
                result = wait_for_process_termination(1234, timeout=10)

                assert result is True

    @pytest.mark.unit
    def test_process_timeout(self):
        """Test timeout waiting for process termination"""
        with patch("psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.is_running.return_value = True
            mock_process.return_value = mock_proc

            with patch("time.time", side_effect=[0, 5, 11]):  # Simulate timeout
                with patch("time.sleep"):
                    result = wait_for_process_termination(1234, timeout=10)

                    assert result is False


class TestGetSystemProcessSummary:
    """Test system process summary functionality"""

    @pytest.mark.unit
    def test_process_summary_success(self):
        """Test successful process summary generation"""
        mock_processes = [
            {"pid": 1001, "name": "init", "status": "sleeping", "username": "root"},
            {"pid": 1002, "name": "python", "status": "running", "username": "user1"},
            {"pid": 1003, "name": "bash", "status": "sleeping", "username": "user1"},
        ]

        def mock_proc_iter(attrs):
            mock_procs = []
            for proc_data in mock_processes:
                mock_proc = MagicMock()
                mock_proc.info = proc_data
                mock_procs.append(mock_proc)
            return mock_procs

        with patch("psutil.process_iter", side_effect=mock_proc_iter):
            with patch("psutil.virtual_memory") as mock_memory:
                mock_memory.return_value._asdict.return_value = {
                    "total": 8000000,
                    "available": 4000000,
                }
                with patch("psutil.cpu_percent", return_value=25.5):
                    result = get_system_process_summary()

                    assert result["total_processes"] == 3
                    assert result["by_status"]["sleeping"] == 2
                    assert result["by_status"]["running"] == 1
                    assert result["by_user"]["root"] == 1
                    assert result["by_user"]["user1"] == 2
                    assert result["cpu_usage"] == 25.5
                    assert "memory_usage" in result

    @pytest.mark.unit
    def test_process_summary_with_exceptions(self):
        """Test process summary with some inaccessible processes"""
        # Create mock processes
        mock_proc1 = MagicMock()
        mock_proc1.info = {
            "pid": 1001,
            "name": "accessible",
            "status": "running",
            "username": "user",
        }

        # Create a mock process that raises AccessDenied when accessing status in the loop
        mock_proc2 = MagicMock()
        mock_proc2.info = MagicMock()

        # Configure the mock to raise AccessDenied when specific keys are accessed
        def mock_getitem(self, key):
            if key == "status":
                raise psutil.AccessDenied()
            elif key == "username":
                raise psutil.AccessDenied()
            return {"pid": 1002, "name": "restricted"}[key]

        mock_proc2.info.__getitem__ = mock_getitem

        with patch("psutil.process_iter", return_value=[mock_proc1, mock_proc2]):
            with patch("psutil.virtual_memory") as mock_memory:
                mock_memory.return_value._asdict.return_value = {}
                with patch("psutil.cpu_percent", return_value=0):
                    result = get_system_process_summary()

                    assert (
                        result["total_processes"] == 2
                    )  # Both processes counted in list
                    assert (
                        result["by_status"]["running"] == 1
                    )  # Only accessible process counted in stats
                    assert len(result["by_status"]) == 1  # Only one status counted
                    assert (
                        result["by_user"]["user"] == 1
                    )  # Only accessible user counted

    @pytest.mark.unit
    def test_process_summary_error(self):
        """Test handling errors in process summary generation"""
        with patch("psutil.process_iter", side_effect=Exception("System error")):
            result = get_system_process_summary()

            assert "error" in result
            assert "Failed to get process summary" in result["error"]


class TestIsProcessRunning:
    """Test process running check functionality"""

    @pytest.mark.unit
    def test_process_is_running(self):
        """Test checking if process is running"""
        with patch("psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.is_running.return_value = True
            mock_process.return_value = mock_proc

            result = is_process_running(1234)

            assert result is True

    @pytest.mark.unit
    def test_process_not_running(self):
        """Test checking if process is not running"""
        with patch("psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.is_running.return_value = False
            mock_process.return_value = mock_proc

            result = is_process_running(1234)

            assert result is False

    @pytest.mark.unit
    def test_process_not_found(self):
        """Test checking non-existent process"""
        with patch("psutil.Process", side_effect=psutil.NoSuchProcess(1234)):
            result = is_process_running(1234)

            assert result is False

    @pytest.mark.unit
    def test_process_check_exception(self):
        """Test handling exceptions during process check"""
        with patch("psutil.Process", side_effect=Exception("System error")):
            result = is_process_running(1234)

            assert result is False


class TestSudoManager:
    """Test SudoManager class functionality"""

    @pytest.mark.unit
    def test_sudo_manager_creation(self):
        """Test creating SudoManager instance"""
        manager = create_sudo_manager()

        assert isinstance(manager, SudoManager)
        assert not manager.has_sudo_access()
        assert manager.get_cached_password() == ""

    @pytest.mark.unit
    def test_get_sudo_password_success(self):
        """Test successful sudo password retrieval"""
        manager = SudoManager()

        with patch("getpass.getpass", return_value="test_password"):
            with patch(
                "sage.common.utils.system.process.verify_sudo_password",
                return_value=True,
            ):
                with patch("builtins.print"):
                    password = manager.get_sudo_password()

                    assert password == "test_password"
                    assert manager.has_sudo_access()
                    assert manager.get_cached_password() == "test_password"

    @pytest.mark.unit
    def test_get_sudo_password_invalid(self):
        """Test invalid sudo password handling"""
        manager = SudoManager()

        with patch("getpass.getpass", return_value="wrong_password"):
            with patch(
                "sage.common.utils.system.process.verify_sudo_password",
                return_value=False,
            ):
                with patch("builtins.print"):
                    password = manager.get_sudo_password()

                    assert password == ""
                    assert not manager.has_sudo_access()

    @pytest.mark.unit
    def test_get_sudo_password_empty(self):
        """Test empty password input"""
        manager = SudoManager()

        with patch("getpass.getpass", return_value=""):
            with patch("builtins.print"):
                password = manager.get_sudo_password()

                assert password == ""
                assert not manager.has_sudo_access()

    @pytest.mark.unit
    def test_cached_password_reuse(self):
        """Test reusing cached password"""
        manager = SudoManager()
        manager._cached_password = "cached_password"
        manager._password_verified = True

        password = manager.get_sudo_password()

        assert password == "cached_password"

    @pytest.mark.unit
    def test_ensure_sudo_access(self):
        """Test ensuring sudo access"""
        manager = SudoManager()

        with patch.object(manager, "get_sudo_password", return_value="password"):
            with patch("builtins.print"):
                result = manager.ensure_sudo_access()

                assert result is True

        # Test without password
        with patch.object(manager, "get_sudo_password", return_value=""):
            with patch("builtins.print"):
                result = manager.ensure_sudo_access()

                assert result is False

    @pytest.mark.unit
    def test_clear_cache(self):
        """Test clearing password cache"""
        manager = SudoManager()
        manager._cached_password = "password"
        manager._password_verified = True

        manager.clear_cache()

        assert manager._cached_password is None
        assert not manager._password_verified
        assert not manager.has_sudo_access()

    @pytest.mark.unit
    def test_execute_with_sudo_success(self):
        """Test successful sudo command execution"""
        manager = SudoManager()
        manager._cached_password = "password"
        manager._password_verified = True

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="Command output", stderr=""
            )

            result = manager.execute_with_sudo(["kill", "-9", "1234"])

            assert result["success"] is True
            assert result["stdout"] == "Command output"
            mock_run.assert_called_once_with(
                ["sudo", "-S", "kill", "-9", "1234"],
                input="password\n",
                capture_output=True,
                text=True,
                timeout=30,
            )

    @pytest.mark.unit
    def test_execute_with_sudo_no_password(self):
        """Test sudo execution without password"""
        manager = SudoManager()

        result = manager.execute_with_sudo(["kill", "-9", "1234"])

        assert result["success"] is False
        assert "No sudo password available" in result["error"]

    @pytest.mark.unit
    def test_execute_with_sudo_failure(self):
        """Test failed sudo command execution"""
        manager = SudoManager()
        manager._cached_password = "password"
        manager._password_verified = True

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1, stdout="", stderr="Permission denied"
            )

            result = manager.execute_with_sudo(["kill", "-9", "1234"])

            assert result["success"] is False
            assert result["returncode"] == 1
            assert "Command failed" in result["error"]

    @pytest.mark.unit
    def test_execute_with_sudo_timeout(self):
        """Test sudo command timeout"""
        manager = SudoManager()
        manager._cached_password = "password"
        manager._password_verified = True

        with patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired(["sudo"], 30)
        ):
            result = manager.execute_with_sudo(["sleep", "60"])

            assert result["success"] is False
            assert "Command timeout" in result["error"]


class TestCheckProcessOwnership:
    """Test process ownership checking"""

    @pytest.mark.unit
    def test_own_process(self):
        """Test checking ownership of own process"""
        with patch("psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.username.return_value = "testuser"
            mock_process.return_value = mock_proc

            with patch("os.getenv", return_value="testuser"):
                result = check_process_ownership(1234)

                assert result["needs_sudo"] is False
                assert result["accessible"] is True
                assert result["process_user"] == "testuser"
                assert result["current_user"] == "testuser"

    @pytest.mark.unit
    def test_other_user_process(self):
        """Test checking ownership of another user's process"""
        with patch("psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.username.return_value = "otheruser"
            mock_process.return_value = mock_proc

            with patch("os.getenv", return_value="testuser"):
                result = check_process_ownership(1234)

                assert result["needs_sudo"] is True
                assert result["accessible"] is True
                assert result["process_user"] == "otheruser"
                assert result["current_user"] == "testuser"

    @pytest.mark.unit
    def test_process_not_found_ownership(self):
        """Test checking ownership of non-existent process"""
        with patch("psutil.Process", side_effect=psutil.NoSuchProcess(1234)):
            result = check_process_ownership(1234)

            assert result["accessible"] is False
            assert "Process not found" in result["error"]

    @pytest.mark.unit
    def test_access_denied_ownership(self):
        """Test checking ownership with access denied"""
        with patch("psutil.Process", side_effect=psutil.AccessDenied(1234)):
            with patch("os.getenv", return_value="testuser"):
                result = check_process_ownership(1234)

                assert result["accessible"] is False
                assert result["needs_sudo"] is True
                assert "Access denied" in result["error"]

    @pytest.mark.unit
    def test_custom_current_user(self):
        """Test checking ownership with custom current user"""
        with patch("psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.username.return_value = "processowner"
            mock_process.return_value = mock_proc

            result = check_process_ownership(1234, current_user="customuser")

            assert result["current_user"] == "customuser"
            assert result["needs_sudo"] is True


class TestIntegrationScenarios:
    """Integration tests for process management utilities"""

    @pytest.mark.integration
    def test_complete_process_management_workflow(self):
        """Test complete process management workflow"""
        # Find processes
        mock_procs = [MagicMock(pid=1001), MagicMock(pid=1002)]

        # Since the function is imported into the current module namespace,
        # we need to patch it in the current module
        import sys

        current_module = sys.modules[__name__]
        with patch.object(
            current_module, "find_processes_by_name", return_value=mock_procs
        ):
            processes = find_processes_by_name(["test_app"])
            assert len(processes) == 2

        # Check ownership
        with patch.object(current_module, "check_process_ownership") as mock_ownership:
            mock_ownership.return_value = {
                "pid": 1001,
                "process_user": "testuser",
                "current_user": "testuser",
                "needs_sudo": False,
                "accessible": True,
            }

            ownership = check_process_ownership(1001)
            assert ownership["needs_sudo"] is False

        # Terminate processes
        with patch(
            "sage.common.utils.system.process.terminate_process"
        ) as mock_terminate:
            mock_terminate.return_value = {"success": True, "method": "terminate"}

            result = terminate_process(1001)
            assert result["success"]

    @pytest.mark.integration
    def test_sudo_workflow(self):
        """Test sudo-based process management workflow"""
        manager = SudoManager()

        # Get sudo access
        with patch("getpass.getpass", return_value="password"):
            with patch(
                "sage.common.utils.system.process.verify_sudo_password",
                return_value=True,
            ):
                with patch("builtins.print"):
                    assert manager.ensure_sudo_access()

        # Execute sudo command
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            result = manager.execute_with_sudo(["kill", "-9", "1234"])
            assert result["success"]

    @pytest.mark.slow
    def test_process_tree_management(self):
        """Test managing process trees"""
        # Mock a process tree: parent 1000 -> children [1001, 1002]
        with patch(
            "sage.common.utils.system.process.get_process_children",
            return_value=[1001, 1002],
        ):
            with patch(
                "sage.common.utils.system.process.terminate_process"
            ) as mock_terminate:
                mock_terminate.side_effect = [
                    {"success": True, "method": "terminate", "pid": 1001},
                    {"success": True, "method": "terminate", "pid": 1002},
                    {"success": True, "method": "terminate", "pid": 1000},
                ]

                result = terminate_process_tree(1000)

                assert result["success"]
                assert result["total_processes"] == 3
                assert len(result["terminated"]) == 3


class TestPerformanceScenarios:
    """Performance and stress tests"""

    @pytest.mark.slow
    def test_large_process_list_handling(self):
        """Test handling large numbers of processes"""
        # Simulate 1000 processes
        mock_processes = []
        for i in range(1000):
            mock_proc = MagicMock()
            mock_proc.info = {
                "pid": i + 1000,
                "name": f"process_{i}",
                "cmdline": [f"process_{i}", "--arg"],
                "status": "running",
                "username": "user",
            }
            mock_processes.append(mock_proc)

        def mock_proc_iter(attrs):
            return mock_processes

        with patch("psutil.process_iter", side_effect=mock_proc_iter):
            with patch("psutil.virtual_memory") as mock_memory:
                mock_memory.return_value._asdict.return_value = {}
                with patch("psutil.cpu_percent", return_value=50):
                    result = get_system_process_summary()

                    assert result["total_processes"] == 1000
                    assert result["by_status"]["running"] == 1000

    @pytest.mark.slow
    def test_rapid_process_checks(self):
        """Test rapid process status checks"""
        with patch("psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.is_running.return_value = True
            mock_process.return_value = mock_proc

            start_time = time.time()
            for pid in range(1000, 1100):  # Check 100 processes
                is_process_running(pid)
            end_time = time.time()

            # Should complete quickly (under 1 second with mocking)
            assert end_time - start_time < 1.0


class TestErrorHandlingScenarios:
    """Error handling and edge case tests"""

    @pytest.mark.unit
    def test_invalid_pid_handling(self):
        """Test handling invalid PIDs"""
        # Negative PID
        result = get_process_info(-1)
        assert "error" in result

        # Very large PID
        with patch("psutil.Process", side_effect=psutil.NoSuchProcess(999999)):
            result = get_process_info(999999)
            assert result["status"] == "Not Found"

    @pytest.mark.unit
    def test_system_resource_exhaustion(self):
        """Test behavior under resource exhaustion"""
        with patch(
            "psutil.process_iter", side_effect=OSError("Cannot access process list")
        ):
            result = get_system_process_summary()
            assert "error" in result

    @pytest.mark.unit
    def test_permission_escalation_failure(self):
        """Test handling sudo permission failures"""
        manager = SudoManager()

        with patch("getpass.getpass", return_value="wrong_password"):
            with patch(
                "sage.common.utils.system.process.verify_sudo_password",
                return_value=False,
            ):
                with patch("builtins.print"):
                    assert not manager.ensure_sudo_access()

    @pytest.mark.unit
    def test_process_state_changes(self):
        """Test handling processes that change state during operations"""
        # Process terminates between check and operation
        with patch(
            "sage.common.utils.system.process.find_processes_by_name"
        ) as mock_find:
            mock_find.return_value = [MagicMock(pid=1234)]

            with patch(
                "sage.common.utils.system.process.terminate_process"
            ) as mock_terminate:
                mock_terminate.return_value = {
                    "success": True,
                    "method": "already_gone",
                    "pid": 1234,
                }

                result = terminate_processes_by_name(["test_process"])

                assert result["success"]
                assert len(result["already_gone"]) == 1


if __name__ == "__main__":
    pytest.main([__file__])
