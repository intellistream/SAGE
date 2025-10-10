"""
SAGE Studio Backend API

A simple FastAPI backend service that provides real SAGE data to the Studio frontend.
"""

import importlib
import inspect
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime

try:
    from .query_storage import FileSourceQueryStorage
except ImportError:  # pragma: no cover - fallback when running as script
    from query_storage import FileSourceQueryStorage  # type: ignore


def _convert_pipeline_to_job(pipeline_data: dict, pipeline_id: str) -> dict:
    """将拓扑图数据转换为 Job 格式"""
    from datetime import datetime
    import os

    # 从拓扑图数据中提取信息
    name = pipeline_data.get("name", f"拓扑图 {pipeline_id}")
    description = pipeline_data.get("description", "")
    nodes = pipeline_data.get("nodes", [])
    edges = pipeline_data.get("edges", [])

    # 创建操作符列表
    operators = []
    for i, node in enumerate(nodes):
        # 构建下游连接
        downstream = []
        for edge in edges:
            if edge.get("source") == node.get("id"):
                # 找到目标节点的索引
                target_node = next(
                    (n for n in nodes if n.get("id") == edge.get("target")), None
                )
                if target_node:
                    target_index = next(
                        (
                            j
                            for j, n in enumerate(nodes)
                            if n.get("id") == edge.get("target")
                        ),
                        None,
                    )
                    if target_index is not None:
                        downstream.append(target_index)

        operator = {
            "id": i,
            "name": node.get("name", f"Operator_{i}"),
            "numOfInstances": 1,
            "downstream": downstream,
        }
        operators.append(operator)

    # 创建 Job 对象
    # 尝试从拓扑图数据中获取创建时间，如果没有则使用文件创建时间或当前时间
    create_time = pipeline_data.get("createTime")
    if not create_time:
        # 尝试从pipeline_id中提取时间戳（如果是timestamp格式）
        try:
            if pipeline_id.startswith("pipeline_"):
                timestamp_str = pipeline_id.replace("pipeline_", "")
                if timestamp_str.isdigit():
                    timestamp = int(timestamp_str)
                    create_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    create_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                create_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            create_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    job = {
        "jobId": pipeline_id,
        "name": name,
        "isRunning": False,  # 拓扑图默认不在运行
        "nthreads": "1",
        "cpu": "0%",
        "ram": "0GB",
        "startTime": create_time,
        "duration": "00:00:00",
        "nevents": 0,
        "minProcessTime": 0,
        "maxProcessTime": 0,
        "meanProcessTime": 0,
        "latency": 0,
        "throughput": 0,
        "ncore": 1,
        "periodicalThroughput": [0],
        "periodicalLatency": [0],
        "totalTimeBreakdown": {
            "totalTime": 0,
            "serializeTime": 0,
            "persistTime": 0,
            "streamProcessTime": 0,
            "overheadTime": 0,
        },
        "schedulerTimeBreakdown": {
            "overheadTime": 0,
            "streamTime": 0,
            "totalTime": 0,
            "txnTime": 0,
        },
        "operators": operators,
    }

    return job


def _get_sage_dir() -> Path:
    """获取 SAGE 目录路径"""
    # 首先检查环境变量
    env_dir = os.environ.get("SAGE_OUTPUT_DIR")
    if env_dir:
        sage_dir = Path(env_dir)
    else:
        # 检查是否在开发环境中
        current_dir = Path.cwd()
        if (current_dir / "packages" / "sage-common").exists():
            sage_dir = current_dir / ".sage"
        else:
            sage_dir = Path.home() / ".sage"

    sage_dir.mkdir(parents=True, exist_ok=True)
    return sage_dir


# Pydantic 模型定义
class Job(BaseModel):
    jobId: str
    name: str
    isRunning: bool
    nthreads: str
    cpu: str
    ram: str
    startTime: str
    duration: str
    nevents: int
    minProcessTime: int
    maxProcessTime: int
    meanProcessTime: int
    latency: int
    throughput: int
    ncore: int
    periodicalThroughput: List[int]
    periodicalLatency: List[int]
    totalTimeBreakdown: dict
    schedulerTimeBreakdown: dict
    operators: List[dict]


class OperatorInfo(BaseModel):
    id: int
    name: str
    description: str
    code: str
    isCustom: bool


# 创建 FastAPI 应用
app = FastAPI(
    title="SAGE Studio Backend",
    description="Backend API service for SAGE Studio frontend",
    version="1.0.0",
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # Studio 默认端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加验证错误处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"Validation error on {request.method} {request.url}: {exc.errors()}")
    print(f"Request body: {await request.body()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(await request.body())}
    )


def _read_sage_data_from_files():
    """从 .sage 目录的文件中读取实际的 SAGE 数据"""
    sage_dir = _get_sage_dir()
    data = {"jobs": [], "operators": [], "pipelines": []}

    try:
        # 读取作业信息
        states_dir = sage_dir / "states"
        if states_dir.exists():
            for job_file in states_dir.glob("*.json"):
                try:
                    with open(job_file, "r", encoding="utf-8") as f:
                        job_data = json.load(f)
                        data["jobs"].append(job_data)
                except Exception as e:
                    print(f"Error reading job file {job_file}: {e}")

        # 读取保存的拓扑图并转换为 Job 格式
        pipelines_dir = sage_dir / "pipelines"
        if pipelines_dir.exists():
            for pipeline_file in pipelines_dir.glob("pipeline_*.json"):
                try:
                    with open(pipeline_file, "r", encoding="utf-8") as f:
                        pipeline_data = json.load(f)
                        
                        # 如果拓扑图数据中没有createTime，尝试使用文件的创建时间
                        if "createTime" not in pipeline_data:
                            try:
                                # 获取文件的修改时间作为创建时间
                                file_mtime = pipeline_file.stat().st_mtime
                                from datetime import datetime
                                pipeline_data["createTime"] = datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d %H:%M:%S")
                            except Exception as e:
                                print(f"Error getting file time for {pipeline_file}: {e}")
                        
                        # 将拓扑图转换为 Job 格式
                        job_from_pipeline = _convert_pipeline_to_job(
                            pipeline_data, pipeline_file.stem
                        )
                        data["jobs"].append(job_from_pipeline)
                except Exception as e:
                    print(f"Error reading pipeline file {pipeline_file}: {e}")

        # 读取操作符信息
        operators_file = sage_dir / "output" / "operators.json"
        if operators_file.exists():
            try:
                with open(operators_file, "r", encoding="utf-8") as f:
                    operators_data = json.load(f)
                    data["operators"] = operators_data
            except Exception as e:
                print(f"Error reading operators file: {e}")

        # 读取管道信息
        pipelines_file = sage_dir / "output" / "pipelines.json"
        if pipelines_file.exists():
            try:
                with open(pipelines_file, "r") as f:
                    pipelines_data = json.load(f)
                    data["pipelines"] = pipelines_data
            except Exception as e:
                print(f"Error reading pipelines file: {e}")

    except Exception as e:
        print(f"Error reading SAGE data: {e}")

    return data


@app.get("/")
async def root():
    """根路径"""
    return {"message": "SAGE Studio Backend API", "status": "running"}


@app.get("/api/jobs/all", response_model=List[Job])
async def get_all_jobs():
    """获取所有作业信息"""
    try:
        sage_data = _read_sage_data_from_files()
        jobs = sage_data.get("jobs", [])

        print(f"DEBUG: Read {len(jobs)} jobs from files")
        print(f"DEBUG: sage_data = {sage_data}")

        # 如果没有实际数据，返回一些示例数据（用于开发）
        if not jobs:
            print("DEBUG: No real jobs found, using fallback data")
            jobs = [
                {
                    "jobId": "job_001",
                    "name": "RAG问答管道示例",
                    "isRunning": False,
                    "nthreads": "4",
                    "cpu": "0%",
                    "ram": "0GB",
                    "startTime": "2025-08-18 10:30:00",
                    "duration": "00:45:12",
                    "nevents": 1000,
                    "minProcessTime": 10,
                    "maxProcessTime": 500,
                    "meanProcessTime": 150,
                    "latency": 200,
                    "throughput": 800,
                    "ncore": 4,
                    "periodicalThroughput": [750, 800, 820, 785, 810],
                    "periodicalLatency": [180, 200, 190, 210, 195],
                    "totalTimeBreakdown": {
                        "totalTime": 2712000,
                        "serializeTime": 50000,
                        "persistTime": 100000,
                        "streamProcessTime": 2500000,
                        "overheadTime": 62000,
                    },
                    "schedulerTimeBreakdown": {
                        "overheadTime": 50000,
                        "streamTime": 2600000,
                        "totalTime": 2712000,
                        "txnTime": 62000,
                    },
                    "operators": [
                        {
                            "id": 1,
                            "name": "FileSource",
                            "numOfInstances": 1,
                            "throughput": 800,
                            "latency": 50,
                            "explorationStrategy": "greedy",
                            "schedulingGranularity": "batch",
                            "abortHandling": "rollback",
                            "numOfTD": 10,
                            "numOfLD": 5,
                            "numOfPD": 2,
                            "lastBatch": 999,
                            "downstream": [2],
                        }
                    ],
                }
            ]

        return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取作业信息失败: {str(e)}")


def _get_studio_operators_dir() -> Path:
    """获取 Studio operators 数据目录路径"""
    current_file = Path(__file__)
    # 从 api.py 文件路径找到 studio 根目录:
    # ../../../ 从 backend/ 到 studio/
    studio_root = current_file.parent.parent.parent
    operators_dir = studio_root / "data" / "operators"
    return operators_dir


def _load_operator_class_source(module_path: str, class_name: str) -> str:
    """动态加载operator类并获取其源代码"""
    try:
        # 添加SAGE项目路径到sys.path
        sage_root = Path(__file__).parent.parent.parent.parent.parent.parent
        if str(sage_root) not in sys.path:
            sys.path.insert(0, str(sage_root))

        # 动态导入模块
        module = importlib.import_module(module_path)

        # 获取类
        operator_class = getattr(module, class_name)

        # 获取源代码
        source_code = inspect.getsource(operator_class)

        return source_code

    except Exception as e:
        print(f"Error loading operator class {module_path}.{class_name}: {e}")
        return f"# Error loading source code for {class_name}\n# {str(e)}"


def _read_real_operators():
    """从 studio data 目录读取真实的操作符数据并动态加载源代码"""
    operators = []
    operators_dir = _get_studio_operators_dir()

    if not operators_dir.exists():
        print(f"Operators directory not found: {operators_dir}")
        return []

    try:
        # 读取所有 JSON 文件
        for json_file in operators_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    operator_data = json.load(f)

                    # 检查是否有module_path和class_name字段
                    if "module_path" in operator_data and "class_name" in operator_data:
                        # 动态加载源代码
                        source_code = _load_operator_class_source(
                            operator_data["module_path"], operator_data["class_name"]
                        )
                        operator_data["code"] = source_code
                    else:
                        # 如果没有模块路径信息，使用空代码
                        operator_data["code"] = ""

                    # 确保数据格式正确
                    required_fields = ["id", "name", "description", "isCustom"]
                    if all(key in operator_data for key in required_fields):
                        # 清理不需要的字段
                        clean_data = {
                            "id": operator_data["id"],
                            "name": operator_data["name"],
                            "description": operator_data["description"],
                            "code": operator_data.get("code", ""),
                            "isCustom": operator_data["isCustom"],
                        }
                        operators.append(clean_data)
                        print(f"Loaded operator: {operator_data['name']}")
                    else:
                        print(f"Invalid operator data in {json_file}")

            except Exception as e:
                print(f"Error reading operator file {json_file}: {e}")

    except Exception as e:
        print(f"Error reading operators directory: {e}")

    return operators


@app.get("/api/operators", response_model=List[OperatorInfo])
async def get_operators():
    """获取所有操作符信息"""
    try:
        # 首先尝试读取真实的操作符数据
        operators = _read_real_operators()

        # 如果没有找到真实数据，使用后备数据
        if not operators:
            print("No real operator data found, using fallback data")
            operators = [
                {
                    "id": 1,
                    "name": "FileSource",
                    "description": "从文件读取数据的源操作符",
                    "code": "class FileSource:\n    def __init__(self, file_path):\n        self.file_path = file_path\n    \n    def read_data(self):\n        with open(self.file_path, 'r') as f:\n            return f.read()",
                    "isCustom": True,
                },
                {
                    "id": 2,
                    "name": "SimpleRetriever",
                    "description": "简单的检索操作符",
                    "code": "class SimpleRetriever:\n    def __init__(self, top_k=5):\n        self.top_k = top_k\n    \n    def retrieve(self, query):\n        return query[:self.top_k]",
                    "isCustom": True,
                },
            ]

        print(f"Returning {len(operators)} operators")
        return operators
    except Exception as e:
        print(f"Error in get_operators: {e}")
        raise HTTPException(status_code=500, detail=f"获取操作符信息失败: {str(e)}")


@app.get("/api/operators/list")
async def get_operators_list(page: int = 1, size: int = 10, search: str = ""):
    """获取操作符列表 - 支持分页和搜索"""
    try:
        # 获取所有操作符
        all_operators = _read_real_operators()

        # 如果没有找到真实数据，使用后备数据
        if not all_operators:
            print("No real operator data found, using fallback data")
            all_operators = [
                {
                    "id": 1,
                    "name": "FileSource",
                    "description": "从文件读取数据的源操作符",
                    "code": "class FileSource:\n    def __init__(self, file_path):\n        self.file_path = file_path\n    \n    def read_data(self):\n        with open(self.file_path, 'r') as f:\n            return f.read()",
                    "isCustom": True,
                },
                {
                    "id": 2,
                    "name": "SimpleRetriever",
                    "description": "简单的检索操作符",
                    "code": "class SimpleRetriever:\n    def __init__(self, top_k=5):\n        self.top_k = top_k\n    \n    def retrieve(self, query):\n        return query[:self.top_k]",
                    "isCustom": True,
                },
            ]

        # 搜索过滤
        if search:
            filtered_operators = [
                op
                for op in all_operators
                if search.lower() in op["name"].lower()
                or search.lower() in op["description"].lower()
            ]
        else:
            filtered_operators = all_operators

        # 分页计算
        total = len(filtered_operators)
        start = (page - 1) * size
        end = start + size
        items = filtered_operators[start:end]

        result = {"items": items, "total": total}

        print(f"Returning page {page} with {len(items)} operators (total: {total})")
        return result

    except Exception as e:
        print(f"Error in get_operators_list: {e}")
        raise HTTPException(status_code=500, detail=f"获取操作符列表失败: {str(e)}")


@app.get("/api/pipelines")
async def get_pipelines():
    """获取所有管道信息"""
    try:
        sage_data = _read_sage_data_from_files()
        pipelines = sage_data.get("pipelines", [])

        # 如果没有实际数据，返回一些示例数据
        if not pipelines:
            pipelines = [
                {
                    "id": "pipeline_001",
                    "name": "示例RAG管道",
                    "description": "演示RAG问答系统的数据处理管道",
                    "status": "running",
                    "operators": [
                        {
                            "id": "source1",
                            "type": "FileSource",
                            "config": {"file_path": "/data/documents.txt"},
                        },
                        {
                            "id": "retriever1",
                            "type": "SimpleRetriever",
                            "config": {"top_k": 5},
                        },
                        {
                            "id": "sink1",
                            "type": "TerminalSink",
                            "config": {"format": "json"},
                        },
                    ],
                    "connections": [
                        {"from": "source1", "to": "retriever1"},
                        {"from": "retriever1", "to": "sink1"},
                    ],
                }
            ]

        return {"pipelines": pipelines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取管道信息失败: {str(e)}")


@app.post("/api/pipeline/submit")
async def submit_pipeline(topology_data: dict):
    """提交拓扑图/管道配置"""
    try:
        print(f"Received pipeline submission: {topology_data}")

        # 这里可以添加保存到文件或数据库的逻辑
        sage_dir = _get_sage_dir()
        pipelines_dir = sage_dir / "pipelines"
        pipelines_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名（使用时间戳）
        import time
        from datetime import datetime

        timestamp = int(time.time())
        pipeline_file = pipelines_dir / f"pipeline_{timestamp}.json"

        # 添加创建时间到拓扑数据中
        if "createTime" not in topology_data:
            topology_data["createTime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 保存拓扑数据到文件
        with open(pipeline_file, "w", encoding="utf-8") as f:
            json.dump(topology_data, f, indent=2, ensure_ascii=False)

        return {
            "status": "success",
            "message": "拓扑图提交成功",
            "pipeline_id": f"pipeline_{timestamp}",
            "file_path": str(pipeline_file),
        }
    except Exception as e:
        print(f"Error submitting pipeline: {e}")
        raise HTTPException(status_code=500, detail=f"提交拓扑图失败: {str(e)}")


# FileSource 用户输入处理相关的数据模型
class FileSourceInputRequest(BaseModel):
    nodeId: str
    jobId: str  
    query: str

class FileSourceInputResponse(BaseModel):
    status: str
    message: str
    nodeId: str
    jobId: str
    queryId: Optional[str] = None
    storage: Optional[dict] = None

# 全局存储用户输入的查询（在生产环境中应该使用数据库）
user_queries = {}
query_storage = FileSourceQueryStorage()

# ---------------------------------------------------------------------------
# In-memory runtime state (placeholder for real engine integration)
# ---------------------------------------------------------------------------
job_runtime_status = {}  # job_id -> {"isRunning": bool, "startTime": str}
job_logs = {}            # job_id -> list[str] (incremental log lines like Q/A or system)
job_configs_cache = {}   # pipeline_id -> config content string

@app.post("/api/filesource/input", response_model=FileSourceInputResponse)
async def submit_filesource_input(request: FileSourceInputRequest):
    """接收FileSource节点的用户输入查询"""
    try:
        print(f"Received FileSource input - NodeId: {request.nodeId}, JobId: {request.jobId}")
        print(f"Query content: {request.query}")
        
        # 生成查询ID
        import time
        query_id = f"query_{int(time.time())}"
        
        storage_info = query_storage.save_query(
            request.jobId, request.nodeId, request.query, query_id
        )

        # 存储查询数据
        user_queries[query_id] = {
            "nodeId": request.nodeId,
            "jobId": request.jobId, 
            "query": request.query,
            "timestamp": time.time(),
            "processed": True,
            "storage": storage_info
        }
        
        print(f"Stored query with ID: {query_id}")
        
        # 这里可以添加触发管道执行的逻辑
        # 比如通知SAGE系统使用这个用户输入而不是文件输入
        
        return FileSourceInputResponse(
            status="success",
            message="查询已写入文件，等待管道消费",
            nodeId=request.nodeId,
            jobId=request.jobId,
            queryId=query_id,
            storage=storage_info
        )
        
    except Exception as e:
        print(f"Error processing FileSource input: {e}")
        raise HTTPException(status_code=500, detail=f"处理FileSource输入失败: {str(e)}")

@app.get("/api/filesource/queries")
async def get_filesource_queries():
    """获取所有FileSource用户查询"""
    try:
        return {"queries": user_queries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取查询失败: {str(e)}")

@app.get("/api/filesource/queries/{query_id}")
async def get_filesource_query(query_id: str):
    """获取特定的FileSource查询"""
    try:
        if query_id not in user_queries:
            raise HTTPException(status_code=404, detail="查询未找到")
        return {"query": user_queries[query_id]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取查询失败: {str(e)}")

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "SAGE Studio Backend"}


# ---------------------------------------------------------------------------
# Placeholder endpoints required by frontend (job detail / status / logs)
# NOTE: Must be defined BEFORE uvicorn.run to work when running as script
# ---------------------------------------------------------------------------

@app.get("/jobInfo/get/{job_id}")
async def get_job(job_id: str):
    """Return job (pipeline) detail. Tries to map pipeline_* file to Job format.
    If not found, returns a minimal placeholder so the UI won't 404.
    """
    sage_data = _read_sage_data_from_files()
    for job in sage_data.get("jobs", []):
        if job.get("jobId") == job_id:
            # merge runtime isRunning flag if we have started it
            runtime = job_runtime_status.get(job_id)
            if runtime:
                job["isRunning"] = runtime.get("isRunning", job.get("isRunning", False))
                # Optionally update duration
                if runtime.get("isRunning") and runtime.get("startTime"):
                    try:
                        start_dt = datetime.strptime(runtime["startTime"], "%Y-%m-%d %H:%M:%S")
                        delta = datetime.now() - start_dt
                        job["duration"] = str(delta).split(".")[0]
                    except Exception:
                        pass
            return job

    # Not found -> fabricate minimal structure expected by UI
    fabricated = {
        "jobId": job_id,
        "name": job_id,
        "isRunning": False,
        "nthreads": "1",
        "cpu": "0%",
        "ram": "0GB",
        "startTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "duration": "00:00:00",
        "nevents": 0,
        "minProcessTime": 0,
        "maxProcessTime": 0,
        "meanProcessTime": 0,
        "latency": 0,
        "throughput": 0,
        "ncore": 1,
        "periodicalThroughput": [0],
        "periodicalLatency": [0],
        "totalTimeBreakdown": {"totalTime": 0, "serializeTime": 0, "persistTime": 0, "streamProcessTime": 0, "overheadTime": 0},
        "schedulerTimeBreakdown": {"overheadTime": 0, "streamTime": 0, "totalTime": 0, "txnTime": 0},
        "operators": [
            {"id": 0, "name": "FileSource", "numOfInstances": 1, "downstream": [1]},
            {"id": 1, "name": "TerminalSink", "numOfInstances": 1, "downstream": []},
        ],
    }
    return fabricated


@app.get("/api/signal/status/{job_id}")
async def get_job_status(job_id: str):
    """Return runtime status used by frontend (expects use_ray field)."""
    runtime = job_runtime_status.get(job_id, {"isRunning": False})
    return {
        "job_id": job_id,
        "status": "running" if runtime.get("isRunning") else "stopped",
        "use_ray": False,  # placeholder
        "isRunning": runtime.get("isRunning", False),
    }


@app.post("/api/signal/start/{job_id}")
async def start_job(job_id: str):
    """Mark a job as started and append a system log line."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    job_runtime_status[job_id] = {"isRunning": True, "startTime": now}
    logs = job_logs.setdefault(job_id, [])
    logs.append(f"[SYSTEM] Job {job_id} started at {now}")
    return {"status": "success", "job_id": job_id, "use_ray": False, "duration": 0}


@app.post("/api/signal/stop/{job_id}/{duration}")
async def stop_job(job_id: str, duration: str):
    runtime = job_runtime_status.get(job_id)
    if runtime:
        runtime["isRunning"] = False
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logs = job_logs.setdefault(job_id, [])
    logs.append(f"[SYSTEM] Job {job_id} stopped at {now} after {duration}")
    return True


@app.get("/api/signal/sink/{job_id}")
async def get_sink_lines(job_id: str, offset: int = 0):
    """Return incremental log/Q&A lines with offset semantics."""
    lines = job_logs.setdefault(job_id, [])
    # Seed a friendly placeholder once so the UI sees something and advances offset
    if not lines and offset == 0:
        lines.append(f"[SYSTEM] Console ready for {job_id}. Click Start or submit a FileSource query.")
    # If there are stored FileSource queries, optionally surface them as Q lines
    # (Simple heuristic: for newly seen queries, add Q/A placeholder once.)
    existing_q_prefixes = {l for l in lines if l.startswith('[Q]')}
    for qid, qdata in list(user_queries.items()):
        if qdata.get("jobId") == job_id:
            q_line = f"[Q] {qdata['query']}"
            if q_line not in existing_q_prefixes:
                lines.append(q_line)
                # placeholder answer
                lines.append(f"[A] (placeholder answer for {qid})")
    slice_lines = lines[offset:]
    new_offset = len(lines)
    return {"offset": new_offset, "lines": slice_lines}


# ------------------------------
# batchInfo placeholders to satisfy UI calls
# ------------------------------
@app.get("/batchInfo/get/all/{job_id}/{operator_id}")
async def get_all_batches(job_id: str, operator_id: str):
    """Return an empty list as placeholder for historical batches."""
    return []


@app.get("/batchInfo/get/{job_id}/{batch_id}/{operator_id}")
async def get_batch_by_id(job_id: str, batch_id: int, operator_id: str):
    """Return a minimal placeholder batch object for charts to render safely."""
    return {
        "batchId": batch_id,
        "jobId": job_id,
        "operatorID": operator_id,
        "throughput": 0,
        "minLatency": 0,
        "maxLatency": 0,
        "avgLatency": 0,
        "batchSize": 0,
        "batchDuration": 0,
        "latestBatchId": batch_id,
        "overallTimeBreakdown": {"serializeTime": 0, "persistTime": 0, "streamProcessTime": 0, "overheadTime": 0, "totalTime": 0},
        "schedulerTimeBreakdown": {"constructTime": 0, "exploreTime": 0, "usefulTime": 0, "abortTime": 0},
        "accumulativeLatency": 0,
        "accumulativeThroughput": 0,
        "scheduler": "",
        "tpg": []
    }


class ConfigUpdateRequest(BaseModel):
    config: str


@app.get("/jobInfo/config/{pipeline_id}")
async def get_pipeline_config(pipeline_id: str):
    """Return stored config content or a default template."""
    # Memory cache first
    if pipeline_id in job_configs_cache:
        return {"data": job_configs_cache[pipeline_id]}
    sage_dir = _get_sage_dir()
    cfg_dir = sage_dir / "configs"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_file = cfg_dir / f"{pipeline_id}.yaml"
    if cfg_file.exists():
        content = cfg_file.read_text(encoding="utf-8")
        job_configs_cache[pipeline_id] = content
        return {"data": content}
    # default template
    default_cfg = (
        "# Auto-generated placeholder config for " + pipeline_id + "\n"
        "source:\n"
        "  type: FileSource\n"
        "  data_path: '~/.sage/studio/queries/" + pipeline_id + "/filesource_input.txt'\n"
        "retriever:\n"
        "  top_k: 5\n"
        "llm:\n"
        "  model_name: gpt-4o-mini\n"
        "pipeline:\n"
        "  name: '" + pipeline_id + "'\n"
    )
    job_configs_cache[pipeline_id] = default_cfg
    cfg_file.write_text(default_cfg, encoding="utf-8")
    return {"data": default_cfg}


@app.put("/jobInfo/config/update/{pipeline_id}")
async def update_pipeline_config(pipeline_id: str, req: ConfigUpdateRequest):
    sage_dir = _get_sage_dir()
    cfg_dir = sage_dir / "configs"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_file = cfg_dir / f"{pipeline_id}.yaml"
    cfg_file.write_text(req.config, encoding="utf-8")
    job_configs_cache[pipeline_id] = req.config
    return {"status": "success"}



if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
