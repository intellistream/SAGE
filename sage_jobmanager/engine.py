from typing import TYPE_CHECKING, Dict, Any, Optional
import time, uuid
from sage_utils.custom_logger import CustomLogger
from sage_runtime.local_thread_pool import LocalThreadPool
from sage_jobmanager.mixed_dag import MixedDAG
from sage_utils.local_tcp_server import LocalTcpServer
import threading
from sage_utils.dill_serializer import serialize_object, deserialize_object
if TYPE_CHECKING:
    from sage_jobmanager.compiler import Compiler
    from sage_core.api.env import BaseEnvironment


class JobManager: #Job Manager
    _instance = None
    _lock = threading.Lock()

    def __init__(self, host: str = "127.0.0.1", port: int = 19000):

        # 确保只初始化一次
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.graphs: dict[str, 'Compiler'] = {}  # 存储 pipeline 名称到 SageGraph 的映射
        self.env_to_dag: dict[str, 'MixedDAG'] = {}  # 存储name到dag的映射，其中dag的类型为DAG或RayDAG

        # 新增：UUID 到环境信息的映射
        self.environments: Dict[str, Dict[str, Any]] = {}  # uuid -> environment_info
        self._env_lock = threading.RLock()


        # print("Engine initialized")
        self.logger = CustomLogger(
            filename=f"Jobmanager",
            console_output="WARNING",
            file_output=True,
            global_output="WARNING",
            name="Jobmanager"
        )
                # 创建 TCP 服务器
        self.tcp_server = LocalTcpServer(
            host=host, 
            port=port,
            default_handler=self._handle_unknown_message
        )

        # 注册消息处理器
        self._register_message_handlers()
        
        # 启动 TCP 服务器
        self.tcp_server.start()
        server_info = self.tcp_server.get_server_info()
        self.logger.info(f"Engine TCP server started at {server_info['address']}")

    ########################################################
    #                internal  methods                     #
    ########################################################


    def _register_message_handlers(self):
        """注册所有消息处理器"""
        self.tcp_server.register_handler("env_submit", self._handle_env_submit)
        self.tcp_server.register_handler("env_run_once", self._handle_env_run_once)
        self.tcp_server.register_handler("env_run_streaming", self._handle_env_run_streaming)
        self.tcp_server.register_handler("env_stop", self._handle_env_stop)
        self.tcp_server.register_handler("env_close", self._handle_env_close)
        self.tcp_server.register_handler("env_status", self._handle_env_status)




    def _handle_env_submit(self, message: Dict[str, Any], client_address: tuple) -> Dict[str, Any]:
        """处理环境提交消息，返回响应字典"""
        try:
            env_name = message.get("env_name")
            payload = message.get("payload", {})
            serialized_env = payload.get("serialized_env")
            request_id = message.get("request_id")
            
            if not env_name or not serialized_env:
                return self._create_error_response(message, "ERR_MISSING_DATA", 
                                                "Missing env_name or serialized_env")
            
            # 反序列化环境
            env = deserialize_object(serialized_env)
            
            # 生成 UUID
            env_uuid = str(uuid.uuid4())
            
            # 编译环境
            from sage_jobmanager.compiler import Compiler
            graph = Compiler(env)
            mixed_dag = MixedDAG(graph, env)
            
            # 存储环境信息
            with self._env_lock:
                self.environments[env_uuid] = {
                    "env": env,
                    "graph": graph, 
                    "dag": mixed_dag,
                    "status": "submitted",
                    "created_at": time.time()
                }
                
                # 保持向后兼容
                self.graphs[env_name] = graph
                self.env_to_dag[env_name] = mixed_dag
            
            # 提交 DAG
            mixed_dag.submit() # 提交到本地线程池 or Ray 集群
            
            self.logger.info(f"Environment '{env_name}' submitted with UUID {env_uuid}")
            
            # 返回成功响应
            return {
                "type": "env_submit_response",
                "request_id": request_id,
                "env_name": env_name,
                "env_uuid": env_uuid,
                "timestamp": int(time.time()),
                "status": "success",
                "message": "Environment submitted and compiled successfully",
                "payload": {
                    "nodes_count": len(graph.nodes)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error handling env_submit: {e}", exc_info=True)
            return self._create_error_response(message, "ERR_SUBMIT_FAILED", str(e))

    def _handle_env_run_once(self, message: Dict[str, Any], client_address: tuple) -> Dict[str, Any]:
        """处理运行一次消息"""
        try:
            env_uuid = message.get("env_uuid")
            env_name = message.get("env_name")
            request_id = message.get("request_id")
            
            env_info = self._get_environment_by_uuid(env_uuid)
            if not env_info:
                return self._create_error_response(message, "ERR_ENV_NOT_FOUND", 
                                                f"Environment with UUID {env_uuid} not found")
            
            # 执行一次
            dag = env_info["dag"]
            dag.execute_once()
            
            # 更新状态
            with self._env_lock:
                env_info["status"] = "executed_once"
                env_info["last_run"] = time.time()
            
            self.logger.info(f"Environment {env_uuid} executed once")
            
            # 返回成功响应
            return {
                "type": "env_run_once_response",
                "request_id": request_id,
                "env_name": env_name,
                "env_uuid": env_uuid,
                "timestamp": int(time.time()),
                "status": "success",
                "message": "Environment executed once successfully",
                "payload": {}
            }
            
        except Exception as e:
            self.logger.error(f"Error handling env_run_once: {e}", exc_info=True)
            return self._create_error_response(message, "ERR_RUN_FAILED", str(e))

    def _handle_env_run_streaming(self, message: Dict[str, Any], client_address: tuple) -> Dict[str, Any]:
        """处理流式运行消息"""
        try:
            env_uuid = message.get("env_uuid")
            env_name = message.get("env_name")
            request_id = message.get("request_id")
            
            env_info = self._get_environment_by_uuid(env_uuid)
            if not env_info:
                return self._create_error_response(message, "ERR_ENV_NOT_FOUND", 
                                                f"Environment with UUID {env_uuid} not found")
            
            # 流式执行
            dag = env_info["dag"]
            dag.execute_streaming()
            
            # 更新状态
            with self._env_lock:
                env_info["status"] = "streaming"
                env_info["streaming_started"] = time.time()
            
            self.logger.info(f"Environment {env_uuid} started streaming")
            
            return {
                "type": "env_run_streaming_response",
                "request_id": request_id,
                "env_name": env_name,
                "env_uuid": env_uuid,
                "timestamp": int(time.time()),
                "status": "success",
                "message": "Environment streaming started successfully",
                "payload": {}
            }
            
        except Exception as e:
            self.logger.error(f"Error handling env_run_streaming: {e}", exc_info=True)
            return self._create_error_response(message, "ERR_STREAMING_FAILED", str(e))

    def _handle_env_stop(self, message: Dict[str, Any], client_address: tuple) -> Dict[str, Any]:
        """处理停止消息"""
        try:
            env_uuid = message.get("env_uuid")
            env_name = message.get("env_name")
            request_id = message.get("request_id")
            
            env_info = self._get_environment_by_uuid(env_uuid)
            if not env_info:
                return self._create_error_response(message, "ERR_ENV_NOT_FOUND", 
                                                f"Environment with UUID {env_uuid} not found")
            
            # 停止 DAG
            dag = env_info["dag"]
            dag.stop()
            
            # 更新状态
            with self._env_lock:
                env_info["status"] = "stopped"
                env_info["stopped_at"] = time.time()
            
            self.logger.info(f"Environment {env_uuid} stopped")
            
            return {
                "type": "env_stop_response",
                "request_id": request_id,
                "env_name": env_name,
                "env_uuid": env_uuid,
                "timestamp": int(time.time()),
                "status": "success",
                "message": "Environment stopped successfully",
                "payload": {}
            }
            
        except Exception as e:
            self.logger.error(f"Error handling env_stop: {e}", exc_info=True)
            return self._create_error_response(message, "ERR_STOP_FAILED", str(e))

    def _handle_env_close(self, message: Dict[str, Any], client_address: tuple) -> Dict[str, Any]:
        """处理关闭消息"""
        try:
            env_uuid = message.get("env_uuid")
            env_name = message.get("env_name")
            request_id = message.get("request_id")
            
            env_info = self._get_environment_by_uuid(env_uuid)
            if not env_info:
                return self._create_error_response(message, "ERR_ENV_NOT_FOUND", 
                                                f"Environment with UUID {env_uuid} not found")
            
            # 关闭 DAG
            dag = env_info["dag"]
            dag.close()
            
            # 清理资源
            with self._env_lock:
                del self.environments[env_uuid]
                
                # 保持向后兼容
                if env_name in self.graphs:
                    del self.graphs[env_name]
                if env_name in self.env_to_dag:
                    del self.env_to_dag[env_name]
            
            self.logger.info(f"Environment {env_uuid} closed")
            
            return {
                "type": "env_close_response",
                "request_id": request_id,
                "env_name": env_name,
                "env_uuid": env_uuid,
                "timestamp": int(time.time()),
                "status": "success",
                "message": "Environment closed successfully",
                "payload": {}
            }
            
        except Exception as e:
            self.logger.error(f"Error handling env_close: {e}", exc_info=True)
            return self._create_error_response(message, "ERR_CLOSE_FAILED", str(e))

    def _handle_env_status(self, message: Dict[str, Any], client_address: tuple) -> Dict[str, Any]:
        """处理状态查询消息"""
        try:
            env_uuid = message.get("env_uuid")
            env_name = message.get("env_name")
            request_id = message.get("request_id")
            
            env_info = self._get_environment_by_uuid(env_uuid)
            if not env_info:
                return self._create_error_response(message, "ERR_ENV_NOT_FOUND", 
                                                f"Environment with UUID {env_uuid} not found")
            
            return {
                "type": "env_status_response",
                "request_id": request_id,
                "env_name": env_name,
                "env_uuid": env_uuid,
                "timestamp": int(time.time()),
                "status": "success",
                "message": "Environment status retrieved successfully",
                "payload": {
                    "env_status": env_info["status"],
                    "created_at": env_info["created_at"],
                    "last_run": env_info.get("last_run"),
                    "streaming_started": env_info.get("streaming_started"),
                    "stopped_at": env_info.get("stopped_at")
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error handling env_status: {e}", exc_info=True)
            return self._create_error_response(message, "ERR_STATUS_FAILED", str(e))

    def _handle_unknown_message(self, message: Dict[str, Any], client_address: tuple) -> Dict[str, Any]:
        """处理未知消息类型"""
        message_type = message.get("type", "unknown")
        self.logger.warning(f"Received unknown message type '{message_type}' from {client_address}")
        return self._create_error_response(message, "ERR_UNKNOWN_MESSAGE_TYPE", 
                                        f"Unknown message type: {message_type}")
    
    def _get_environment_by_uuid(self, env_uuid: str) -> Optional[Dict[str, Any]]:
        """根据 UUID 获取环境信息"""
        with self._env_lock:
            return self.environments.get(env_uuid)

    def _create_error_response(self, original_message: Dict[str, Any], error_code: str, error_message: str) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "type": f"{original_message.get('type', 'unknown')}_response",
            "request_id": original_message.get("request_id"),
            "env_name": original_message.get("env_name"),
            "env_uuid": original_message.get("env_uuid"),
            "timestamp": int(time.time()),
            "status": "error",
            "message": error_message,
            "payload": {
                "error_code": error_code,
                "details": {}
            }
        }

    def get_server_info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        server_info = self.tcp_server.get_server_info()
        with self._env_lock:
            server_info["environments_count"] = len(self.environments)
            server_info["environment_uuids"] = list(self.environments.keys())
        return server_info
    
    def shutdown(self):
        """
        完整释放 Engine 持有的所有资源：
        - 停掉 RuntimeManager（线程、Ray actor 等）
        - 停掉可能的 TCP/HTTP server
        - 清空 DAG 映射与缓存
        - 重置 Engine 单例
        """
        self.logger.info("Shutting down Engine and releasing resources")
        try:
            local_runtime = LocalThreadPool.get_instance()
            local_runtime.shutdown()
        except Exception:
            self.logger.exception("Error shutting down RuntimeManager:{e}")
            raise

        self.env_to_dag.clear()
        self.graphs.clear()

        JobManager._instance = None
        self.logger.info("Engine shutdown complete")