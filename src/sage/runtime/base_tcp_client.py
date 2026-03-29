from __future__ import annotations

import json
import socket
import time
import uuid
from typing import Any


class BaseTcpClient:
    """Minimal runtime-local TCP client base used by JobManager clients."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 19001,
        timeout: float = 30.0,
        client_name: str = "TcpClient",
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.client_name = client_name
        self.connected = False
        self._socket: socket.socket | None = None
        self.logger = self._create_default_logger()

    def _create_default_logger(self):
        import logging

        logger = logging.getLogger(self.client_name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def connect(self) -> bool:
        if self.connected:
            return True

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect((self.host, self.port))
            self.connected = True
            self.logger.debug("%s connected to %s:%s", self.client_name, self.host, self.port)
            return True
        except Exception as exc:
            self.logger.error("Failed to connect to %s:%s: %s", self.host, self.port, exc)
            if "JobManager" in self.client_name:
                self._log_jobmanager_connection_help()
            self.connected = False
            if self._socket:
                try:
                    self._socket.close()
                except Exception:
                    pass
                self._socket = None
            return False

    def disconnect(self):
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        self.connected = False
        self.logger.debug("%s disconnected", self.client_name)

    def _log_jobmanager_connection_help(self):
        self.logger.error("❌ 无法连接到JobManager服务")
        self.logger.error("📋 请检查以下步骤：")
        self.logger.error("   1. JobManager是否已启动？")
        self.logger.error("      当前主仓未提供独立的 JobManager 守护进程子命令")
        self.logger.error(
            "      请确认目标主机上的 JobManager 兼容服务已监听 %s:%s", self.host, self.port
        )
        self.logger.error("   2. 主机地址是否正确？ (当前: %s:%s)", self.host, self.port)
        self.logger.error("   3. 防火墙是否阻止了连接？")
        self.logger.error("💡 提示：如果是第一次尝试远程执行，请先启动JobManager服务")

    def _create_jobmanager_error_response(self) -> dict[str, Any]:
        return {
            "status": "error",
            "error_code": "ERR_JOBMANAGER_CONNECTION_FAILED",
            "message": f"Cannot connect to JobManager at {self.host}:{self.port}",
            "details": {
                "host": self.host,
                "port": self.port,
                "client_type": "JobManager",
                "suggestions": [
                    f"Ensure a JobManager-compatible service is listening on {self.host}:{self.port}",
                    "Check if the host and port are correct",
                    "Verify that firewall allows the connection",
                    "Ensure JobManager service is running and healthy",
                ],
            },
            "timestamp": time.time(),
        }

    def _create_error_response(self, error_code: str, message: str) -> dict[str, Any]:
        return {
            "status": "error",
            "error_code": error_code,
            "message": message,
            "timestamp": time.time(),
            "request_id": str(uuid.uuid4()),
        }

    def send_request(self, request_data: dict[str, Any]) -> dict[str, Any]:
        if not self.connected:
            if not self.connect():
                if "JobManager" in self.client_name:
                    return self._create_jobmanager_error_response()
                return self._create_error_response(
                    "ERR_CONNECTION_FAILED", "Failed to connect to server"
                )

        try:
            serialized_request = self._serialize_request(request_data)
            self._send_data(serialized_request)
            response_data = self._receive_response()
            if response_data is None:
                return self._create_error_response(
                    "ERR_NO_RESPONSE", "No response received from server"
                )
            return self._deserialize_response(response_data)
        except Exception as exc:
            self.logger.error("Error sending request: %s", exc)
            self.connected = False
            return self._create_error_response(
                "ERR_COMMUNICATION_FAILED", f"Communication error: {exc}"
            )

    def _send_data(self, data: bytes):
        if not self._socket:
            raise RuntimeError("Socket not connected")

        self._socket.sendall(len(data).to_bytes(4, byteorder="big"))
        self._socket.sendall(data)

    def _receive_response(self) -> bytes | None:
        if not self._socket:
            raise RuntimeError("Socket not connected")

        try:
            response_length_data = self._receive_full_data(4)
            if not response_length_data:
                return None
            response_length = int.from_bytes(response_length_data, byteorder="big")
            if response_length <= 0 or response_length > 100 * 1024 * 1024:
                self.logger.warning("Invalid response length: %s", response_length)
                return None
            return self._receive_full_data(response_length)
        except Exception as exc:
            self.logger.error("Error receiving response: %s", exc)
            return None

    def _receive_full_data(self, size: int) -> bytes | None:
        if not self._socket:
            return None

        data = b""
        while len(data) < size:
            try:
                chunk = self._socket.recv(min(size - len(data), 8192))
                if not chunk:
                    self.logger.warning("Connection closed while receiving data")
                    return None
                data += chunk
            except TimeoutError:
                self.logger.error("Timeout while receiving data")
                return None
            except Exception as exc:
                self.logger.error("Error receiving data: %s", exc)
                return None
        return data

    def _serialize_request(self, request_data: dict[str, Any]) -> bytes:
        return json.dumps(request_data, ensure_ascii=False).encode("utf-8")

    def _deserialize_response(self, response_data: bytes) -> dict[str, Any]:
        return json.loads(response_data.decode("utf-8"))
