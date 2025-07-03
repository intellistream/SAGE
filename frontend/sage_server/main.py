# cd frontend/sage_server && python main.py --host 127.0.0.1 --port 8080 --log-level debug


"""
FastAPI 应用模板
基于 LightRAG 风格创建的 FastAPI 应用模板
"""

from fastapi import FastAPI, Depends, HTTPException, status
import os
import logging
import logging.config
import uvicorn
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import configparser
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
import argparse
from routers.job_info import router as jobInfo_router
from routers.batch_info import router as batchInfo_router
from routers.signal import router as signal_router
from routers.operators import router as operator_router
from routers.pipeline import router as pipeline_router
from routers.upload import router as upload_router
# from frontend.sage_server.routers.job_info import router as jobInfo_router
# from frontend.sage_server.routers.batch_info import router as batchInfo_router
# from frontend.sage_server.routers.signal import router as signal_router
# from frontend.sage_server.routers.operators import router as operator_router
# from frontend.sage_server.routers.pipeline import router as pipeline_router
# from frontend.sage_server.routers.upload import router as upload_router


# 加载环境变量
# 使用当前文件夹中的 .env 文件
load_dotenv(".env", override=True)

# 初始化配置解析器
config = configparser.ConfigParser()
config.read("config.ini")

def get_app():
    return globals().get("sage_examples", None)


from sage_utils.embedding_methods.embedding_api import apply_embedding_model
from sage_memory.memory_manager import MemoryManager
def memory_init():
    """初始化内存管理器并创建测试集合"""
    # default_model = MockTextEmbedder(fixed_dim=128)
    manager = MemoryManager()
    embedding_model = apply_embedding_model("hf", model="sentence-transformers/all-MiniLM-L6-v2")
    col = manager.create_collection(
        name="vdb_test",
        backend_type="VDB",
        embedding_model=embedding_model,
        dim=embedding_model.get_dim(),
        description="test vdb collection",
        as_ray_actor=False
    )
    col.add_metadata_field("owner")
    col.add_metadata_field("show_type")
    texts = [
        ("hello world", {"owner": "ruicheng", "show_type": "text"}),
        ("你好，世界", {"owner": "Jun", "show_type": "text"}),
        ("こんにちは、世界", {"owner": "Lei", "show_type": "img"}),
    ]
    for text, metadata in texts:
        print(f"Inserting text: {text} with metadata: {metadata}")
        col.insert(text, metadata)
        print(f"Inserted text: {text} with metadata: {metadata}")
    col.create_index(index_name="vdb_index")
    return col

class CustomPathFilter(logging.Filter):
    """过滤器用于过滤掉频繁的路径访问日志"""

    def __init__(self):
        super().__init__()
        # 定义要过滤的路径
        self.filtered_paths = ["/health", "/static/"]

    def filter(self, record):
        try:
            # 检查记录是否具有访问日志所需的属性
            if not hasattr(record, "args") or not isinstance(record.args, tuple):
                return True
            if len(record.args) < 5:
                return True

            # 从记录参数中提取方法、路径和状态
            method = record.args[1]
            path = record.args[2]
            status = record.args[4]

            # 过滤掉对已过滤路径的成功 GET 请求
            if (
                    method == "GET"
                    and (status == 200 or status == 304)
                    and path in self.filtered_paths
            ):
                return False

            return True
        except Exception:
            # 如果出现任何错误，让消息通过
            return True


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="FastAPI 应用模板")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="服务器主机地址")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口")
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="日志级别",
    )
    parser.add_argument("--verbose", action="store_true", help="启用详细调试输出")
    parser.add_argument("--key", type=str, help="API 密钥")
    parser.add_argument(
        "--ssl", action="store_true", help="启用 SSL"
    )
    parser.add_argument(
        "--ssl-certfile", type=str, help="SSL 证书文件路径"
    )
    parser.add_argument(
        "--ssl-keyfile", type=str, help="SSL 密钥文件路径"
    )
    parser.add_argument(
        "--working-dir", type=str, default="./data", help="工作目录"
    )
    return parser.parse_args()


def get_api_key_dependency(api_key=None):
    """创建 API 密钥依赖项"""
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

    async def check_api_key(token: str = Depends(oauth2_scheme)):
        if not api_key:
            return None
        if token != api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的 API 密钥",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return token

    return check_api_key


def create_app(args):
    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

    # 检查 SSL 配置
    if args.ssl:
        if not args.ssl_certfile or not args.ssl_keyfile:
            raise Exception(
                "启用 SSL 时必须提供 SSL 证书和密钥文件"
            )
        if not os.path.exists(args.ssl_certfile):
            raise Exception(f"未找到 SSL 证书文件: {args.ssl_certfile}")
        if not os.path.exists(args.ssl_keyfile):
            raise Exception(f"未找到 SSL 密钥文件: {args.ssl_keyfile}")

    # 检查是否通过环境变量或参数提供了 API 密钥
    api_key = os.getenv("APP_API_KEY") or args.key




    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """应用程序生命周期管理器，用于启动和关闭事件"""
        # 存储后台任务
        app.state.background_tasks = set()

        try:
            

            # 获取 MemoryManagerService 的句柄
            app.state.retriver_collection =memory_init()


            # 初始化数据库连接或其他资源
            print("\n服务器已准备好接受连接! 🚀\n")

            yield

        finally:
            # 清理数据库连接或其他资源
            print("正在关闭服务器...")

    # 初始化 FastAPI
    app = FastAPI(
        title="FastAPI 模板",
        description="基于 LightRAG 风格的 FastAPI 应用模板" +
                    "(带身份验证)" if api_key else "",
        version="0.1.0",
        openapi_tags=[{"name": "api"}],
        lifespan=lifespan,
    )


    # 添加CORS中间件以允许所有源
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 允许所有源
        allow_credentials=True,
        allow_methods=["*"],  # 允许所有方法
        allow_headers=["*"],  # 允许所有头部
    )


    # sage_examples.include_router(ollama_router, tags=["ollama"])
    app.include_router(jobInfo_router, tags=["jobInfo"],prefix="/jobInfo")
    app.include_router(batchInfo_router, tags=["batchInfo"],prefix="/batchInfo")
    app.include_router(signal_router, tags=["signal"],prefix="/api/signal")
    app.include_router(operator_router, tags=["operators"],prefix="/api/operators")
    app.include_router(pipeline_router, tags=["pipeline"],prefix="/api/pipeline")
    app.include_router(upload_router, tags=["upload"],prefix="/api/upload")

    def get_cors_origins():
        """从环境变量获取允许的源
        返回允许的源列表，如果未设置则默认为 ["*"]
        """
        origins_str = os.getenv("CORS_ORIGINS", "*")
        if origins_str == "*":
            return ["*"]
        return [origin.strip() for origin in origins_str.split(",")]

    # 添加 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 创建可选的 API 密钥依赖项
    optional_api_key = get_api_key_dependency(api_key)

    # 创建工作目录（如果不存在）
    Path(args.working_dir).mkdir(parents=True, exist_ok=True)



    # @sage_examples.get("/health", dependencies=[Depends(optional_api_key)])
    # async def get_status():
    #     """获取当前系统状态"""
    #     return {
    #         "status": "healthy",
    #         "working_directory": str(args.working_dir),
    #         "configuration": {
    #             "host": args.host,
    #             "port": args.port,
    #             "log_level": args.log_level,
    #             "verbose": args.verbose,
    #         }
    #     }

    # 挂载静态文件
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount(
        "/static",
        StaticFiles(directory=static_dir, html=True, check_dir=True),
        name="static",
    )

    return app


def configure_logging():
    """配置 uvicorn 启动的日志记录"""

    # 重置任何现有的处理程序以确保干净的配置
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.filters = []

    # 从环境变量获取日志目录路径
    log_dir = os.getenv("LOG_DIR", os.getcwd())
    log_file_path = os.path.abspath(os.path.join(log_dir, "sage_examples.log"))

    print(f"\n日志文件: {log_file_path}\n")
    os.makedirs(os.path.dirname(log_dir), exist_ok=True)

    # 从环境变量获取日志文件最大大小和备份计数
    log_max_bytes = int(os.getenv("LOG_MAX_BYTES", 10485760))  # 默认 10MB
    log_backup_count = int(os.getenv("LOG_BACKUP_COUNT", 5))  # 默认 5 个备份

    # logging.config.dictConfig(
    #     {
    #         "version": 1,
    #         "disable_existing_loggers": False,
    #         "formatters": {
    #             "default": {
    #                 "format": "%(levelname)s: %(message)s",
    #             },
    #             "detailed": {
    #                 "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    #             },
    #         },
    #         "handlers": {
    #             "console": {
    #                 "formatter": "default",
    #                 "class": "logging.StreamHandler",
    #                 "stream": "ext://sys.stderr",
    #             },
    #             "file": {
    #                 "formatter": "detailed",
    #                 "class": "logging.handlers.RotatingFileHandler",
    #                 "filename": log_file_path,
    #                 "maxBytes": log_max_bytes,
    #                 "backupCount": log_backup_count,
    #                 "encoding": "utf-8",
    #             },
    #         },
    #         "loggers": {
    #             # 配置所有 uvicorn 相关的日志记录器
    #             "uvicorn": {
    #                 "handlers": ["console", "file"],
    #                 "level": "INFO",
    #                 "propagate": False,
    #             },
    #             "uvicorn.access": {
    #                 "handlers": ["console", "file"],
    #                 "level": "INFO",
    #                 "propagate": False,
    #                 "filters": ["path_filter"],
    #             },
    #             "uvicorn.error": {
    #                 "handlers": ["console", "file"],
    #                 "level": "INFO",
    #                 "propagate": False,
    #             },
    #         },
    #         "filters": {
    #             "path_filter": {
    #                 "()": "template_app.CustomPathFilter",
    #             },
    #         },
    #     }
    # )


def get_application(args=None):
    """创建 FastAPI 应用程序的工厂函数"""
    if args is None:
        args = parse_args()
    return create_app(args)


def main():
    # 检查是否在 Gunicorn 下运行
    if "GUNICORN_CMD_ARGS" in os.environ:
        # 如果使用 Gunicorn 启动，直接返回，因为 Gunicorn 将调用 get_application
        print("在 Gunicorn 下运行 - 工作进程管理由 Gunicorn 处理")
        return

    # 配置日志记录
    configure_logging()

    args = parse_args()

    # 显示启动信息
    print(f"\n启动 FastAPI 模板服务器 v0.1.0")
    print(f"主机: {args.host}")
    print(f"端口: {args.port}")
    print(f"日志级别: {args.log_level}")
    print(f"工作目录: {args.working_dir}")
    print(f"API 密钥: {'已配置' if args.key or os.getenv('APP_API_KEY') else '未配置'}")
    print(f"SSL: {'已启用' if args.ssl else '未启用'}")

    # 直接创建应用程序实例，而不是使用工厂函数
    app = create_app(args)
    globals()["sage_examples"] = app  # 将应用程序实例存储在全局变量中
    # 以单进程模式启动 Uvicorn
    uvicorn_config = {
        "sage_examples": app,  # 直接传递应用程序实例，而不是字符串路径
        "host": args.host,
        "port": args.port,
        "log_config": None,  # 禁用默认配置
    }

    if args.ssl:
        uvicorn_config.update(
            {
                "ssl_certfile": args.ssl_certfile,
                "ssl_keyfile": args.ssl_keyfile,
            }
        )

    print(f"以单进程模式在 {args.host}:{args.port} 上启动 Uvicorn 服务器")
    uvicorn.run(**uvicorn_config)


if __name__ == "__main__":
    main()