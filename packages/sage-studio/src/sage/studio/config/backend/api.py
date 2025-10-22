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
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


def _convert_pipeline_to_job(pipeline_data: dict, pipeline_id: str, file_path: Path = None) -> dict:
    """将拓扑图数据转换为 Job 格式"""
    from datetime import datetime

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

    # 从文件名或文件元数据中提取创建时间
    create_time = None
    
    # 方法1: 从文件名解析时间戳 (pipeline_1759908680.json)
    if pipeline_id.startswith("pipeline_"):
        try:
            timestamp_str = pipeline_id.replace("pipeline_", "")
            timestamp = int(timestamp_str)
            create_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError) as e:
            print(f"Failed to parse timestamp from pipeline_id {pipeline_id}: {e}")
    
    # 方法2: 如果解析失败,使用文件的修改时间
    if create_time is None and file_path and file_path.exists():
        try:
            mtime = file_path.stat().st_mtime
            create_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"Failed to get file mtime for {file_path}: {e}")
    
    # 方法3: 兜底使用当前时间
    if create_time is None:
        create_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    job = {
        "jobId": pipeline_id,
        "name": name,
        "description": description,  # 添加描述字段
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
        # 添加 config 字段，保留原始的 React Flow 格式数据
        "config": {
            "name": name,
            "description": description,
            "nodes": nodes,
            "edges": edges,
        },
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
    description: Optional[str] = ""  # 添加描述字段
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
    config: Optional[dict] = None  # 添加 config 字段，用于存储 React Flow 格式的节点和边数据


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
                        # 将拓扑图转换为 Job 格式，传递文件路径以提取真实创建时间
                        job_from_pipeline = _convert_pipeline_to_job(
                            pipeline_data, pipeline_file.stem, pipeline_file
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

        timestamp = int(time.time())
        pipeline_file = pipelines_dir / f"pipeline_{timestamp}.json"

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


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "SAGE Studio Backend"}


# ==================== 管道详情相关端点 ====================
# 用于支持前端 View Details 功能的占位符端点

# 全局状态存储（生产环境应使用数据库）
job_runtime_status = {}  # {job_id: {status, use_ray, isRunning, ...}}
job_logs = {}  # {job_id: [log_lines]}
job_configs_cache = {}  # {pipeline_id: yaml_config}
user_queries = {}  # {job_id: [(query, answer), ...]}


@app.get("/jobInfo/get/{job_id}")
async def get_job_detail(job_id: str):
    """获取作业详细信息 - 包含操作符拓扑结构"""
    try:
        # 首先尝试从已保存的数据中查找
        sage_data = _read_sage_data_from_files()
        jobs = sage_data.get("jobs", [])
        
        # 查找匹配的作业
        job = next((j for j in jobs if j.get("jobId") == job_id), None)
        
        if job:
            return job
        
        # 如果没有找到实际数据，返回占位符数据（用于开发）
        print(f"Job {job_id} not found in saved data, returning placeholder")
        return {
            "jobId": job_id,
            "name": f"管道 {job_id}",
            "isRunning": False,
            "nthreads": "4",
            "cpu": "0%",
            "ram": "0GB",
            "startTime": "2025-10-10 15:00:00",
            "duration": "00:00:00",
            "nevents": 0,
            "minProcessTime": 0,
            "maxProcessTime": 0,
            "meanProcessTime": 0,
            "latency": 0,
            "throughput": 0,
            "ncore": 4,
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
            "operators": [
                {
                    "id": 1,
                    "name": "FileSource",
                    "numOfInstances": 1,
                    "throughput": 0,
                    "latency": 0,
                    "explorationStrategy": "greedy",
                    "schedulingGranularity": "batch",
                    "abortHandling": "rollback",
                    "numOfTD": 0,
                    "numOfLD": 0,
                    "numOfPD": 0,
                    "lastBatch": 0,
                    "downstream": [2],
                },
                {
                    "id": 2,
                    "name": "TerminalSink",
                    "numOfInstances": 1,
                    "throughput": 0,
                    "latency": 0,
                    "explorationStrategy": "greedy",
                    "schedulingGranularity": "batch",
                    "abortHandling": "rollback",
                    "numOfTD": 0,
                    "numOfLD": 0,
                    "numOfPD": 0,
                    "lastBatch": 0,
                    "downstream": [],
                },
            ],
        }
    except Exception as e:
        print(f"Error getting job detail: {e}")
        raise HTTPException(status_code=500, detail=f"获取作业详情失败: {str(e)}")


@app.get("/api/signal/status/{job_id}")
async def get_job_status(job_id: str):
    """获取作业运行状态"""
    try:
        # 从内存中获取状态
        status = job_runtime_status.get(
            job_id,
            {
                "job_id": job_id,
                "status": "idle",
                "use_ray": False,
                "isRunning": False,
            },
        )
        return status
    except Exception as e:
        print(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=f"获取作业状态失败: {str(e)}")


@app.post("/api/signal/start/{job_id}")
async def start_job(job_id: str):
    """启动作业"""
    try:
        # 更新运行状态
        job_runtime_status[job_id] = {
            "job_id": job_id,
            "status": "running",
            "use_ray": False,
            "isRunning": True,
        }
        
        # 初始化日志
        if job_id not in job_logs:
            job_logs[job_id] = []
        
        job_logs[job_id].append(f"[SYSTEM] Job {job_id} started at 2025-10-10 15:30:00")
        
        return {"status": "success", "message": f"作业 {job_id} 已启动"}
    except Exception as e:
        print(f"Error starting job: {e}")
        raise HTTPException(status_code=500, detail=f"启动作业失败: {str(e)}")


@app.post("/api/signal/stop/{job_id}/{duration}")
async def stop_job(job_id: str, duration: str):
    """停止作业"""
    try:
        # 更新运行状态
        job_runtime_status[job_id] = {
            "job_id": job_id,
            "status": "stopped",
            "use_ray": False,
            "isRunning": False,
        }
        
        # 添加停止日志
        if job_id in job_logs:
            job_logs[job_id].append(
                f"[SYSTEM] Job {job_id} stopped after {duration}"
            )
        
        return {"status": "success", "message": f"作业 {job_id} 已停止"}
    except Exception as e:
        print(f"Error stopping job: {e}")
        raise HTTPException(status_code=500, detail=f"停止作业失败: {str(e)}")


@app.get("/api/signal/sink/{job_id}")
async def get_job_logs(job_id: str, offset: int = 0):
    """获取作业日志（增量）"""
    try:
        # 获取该作业的日志
        logs = job_logs.get(job_id, [])
        
        # 如果是第一次请求（offset=0）且没有日志，返回种子消息
        if offset == 0 and len(logs) == 0:
            seed_line = f"[SYSTEM] Console ready for {job_id}. Click Start or submit a FileSource query."
            job_logs[job_id] = [seed_line]
            return {"offset": 1, "lines": [seed_line]}
        
        # 返回从 offset 开始的新日志
        new_logs = logs[offset:]
        new_offset = len(logs)
        
        return {"offset": new_offset, "lines": new_logs}
    except Exception as e:
        print(f"Error getting job logs: {e}")
        raise HTTPException(status_code=500, detail=f"获取作业日志失败: {str(e)}")


@app.get("/batchInfo/get/all/{job_id}/{operator_id}")
async def get_all_batches(job_id: str, operator_id: str):
    """获取操作符的所有批次信息"""
    try:
        # operator_id 可以是字符串（如 "s1", "r1"）或数字
        # 返回空数组作为占位符
        # 实际实现需要从 SAGE 运行时获取批次统计数据
        print(f"Getting batches for job={job_id}, operator={operator_id}")
        return []
    except Exception as e:
        print(f"Error getting batches: {e}")
        raise HTTPException(status_code=500, detail=f"获取批次信息失败: {str(e)}")


@app.get("/batchInfo/get/{job_id}/{batch_id}/{operator_id}")
async def get_batch_detail(job_id: str, batch_id: int, operator_id: str):
    """获取单个批次的详细信息"""
    try:
        # operator_id 可以是字符串（如 "s1", "r1"）或数字
        # 返回占位符批次数据
        return {
            "batchId": batch_id,
            "operatorId": operator_id,
            "processTime": 0,
            "tupleCount": 0,
            "timestamp": "2025-10-10 15:30:00",
        }
    except Exception as e:
        print(f"Error getting batch detail: {e}")
        raise HTTPException(status_code=500, detail=f"获取批次详情失败: {str(e)}")


@app.get("/jobInfo/config/{pipeline_id}")
async def get_pipeline_config(pipeline_id: str):
    """获取管道配置（YAML格式）"""
    try:
        # 尝试从缓存获取
        if pipeline_id in job_configs_cache:
            return {"config": job_configs_cache[pipeline_id]}
        
        # 返回默认配置模板
        default_config = """# SAGE Pipeline Configuration
name: Example RAG Pipeline
version: 1.0.0

operators:
  - name: FileSource
    type: source
    config:
      file_path: /data/documents.txt
  
  - name: SimpleRetriever
    type: retriever
    config:
      top_k: 5
  
  - name: TerminalSink
    type: sink
    config:
      output_path: /tmp/output.txt
"""
        return {"config": default_config}
    except Exception as e:
        print(f"Error getting pipeline config: {e}")
        raise HTTPException(status_code=500, detail=f"获取管道配置失败: {str(e)}")


@app.put("/jobInfo/config/update/{pipeline_id}")
async def update_pipeline_config(pipeline_id: str, config: dict):
    """更新管道配置"""
    try:
        # 保存配置到缓存
        config_yaml = config.get("config", "")
        job_configs_cache[pipeline_id] = config_yaml
        
        # 可选：保存到文件
        sage_dir = _get_sage_dir()
        config_dir = sage_dir / "configs"
        config_dir.mkdir(exist_ok=True)
        
        config_file = config_dir / f"{pipeline_id}.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            f.write(config_yaml)
        
        return {
            "status": "success",
            "message": "配置更新成功",
            "file_path": str(config_file),
        }
    except Exception as e:
        print(f"Error updating pipeline config: {e}")
        raise HTTPException(status_code=500, detail=f"更新管道配置失败: {str(e)}")


# ==================== Playground API ====================

def _load_flow_data(flow_id: str) -> Optional[dict]:
    """加载 Flow 数据"""
    sage_dir = _get_sage_dir()
    pipelines_dir = sage_dir / "pipelines"
    
    print(f"🔍 Looking for flow: {flow_id}")
    print(f"📁 Sage dir: {sage_dir}")
    print(f"📁 Pipelines dir: {pipelines_dir}")
    print(f"📁 Pipelines dir exists: {pipelines_dir.exists()}")
    
    # 尝试加载 pipeline 文件
    flow_file = pipelines_dir / f"{flow_id}.json"
    print(f"📄 Flow file path: {flow_file}")
    print(f"📄 Flow file exists: {flow_file.exists()}")
    
    if flow_file.exists():
        with open(flow_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"✅ Loaded flow: {data.get('name', 'Unnamed')}")
            return data
    
    print(f"❌ Flow file not found")
    return None


def _convert_to_flow_definition(flow_data: dict, flow_id: str):
    """将前端 Flow 数据转换为 FlowDefinition"""
    import sys
    from pathlib import Path
    
    # 添加 sage-studio 到 Python 路径
    studio_path = Path(__file__).parent.parent.parent.parent
    if str(studio_path) not in sys.path:
        sys.path.insert(0, str(studio_path))
    
    from sage.studio.models import VisualPipeline, VisualNode, VisualConnection
    
    name = flow_data.get("name", "Unnamed Flow")
    description = flow_data.get("description", "")
    nodes_data = flow_data.get("nodes", [])
    edges_data = flow_data.get("edges", [])
    
    # 转换节点
    nodes = []
    for node_data in nodes_data:
        node = VisualNode(
            id=node_data.get("id", ""),
            type=node_data.get("data", {}).get("nodeId", "unknown"),
            label=node_data.get("data", {}).get("label", "Unnamed Node"),
            position=node_data.get("position", {"x": 0, "y": 0}),
            config=node_data.get("data", {}).get("properties", {})
        )
        nodes.append(node)
    
    # 转换连接
    connections = []
    for edge_data in edges_data:
        connection = VisualConnection(
            id=edge_data.get("id", f"{edge_data.get('source')}-{edge_data.get('target')}"),
            source_node_id=edge_data.get("source", ""),
            source_port="output",  # 默认输出端口
            target_node_id=edge_data.get("target", ""),
            target_port="input"  # 默认输入端口
        )
        connections.append(connection)
    
    return VisualPipeline(
        id=flow_id,
        name=name,
        description=description,
        nodes=nodes,
        connections=connections
    )


class PlaygroundExecuteRequest(BaseModel):
    """Playground 执行请求"""
    flowId: str
    input: str
    sessionId: str = "default"
    stream: bool = False


class AgentStep(BaseModel):
    """Agent 执行步骤"""
    step: int
    type: str  # reasoning, tool_call, response
    content: str
    timestamp: str
    duration: Optional[int] = None
    toolName: Optional[str] = None
    toolInput: Optional[dict] = None
    toolOutput: Optional[dict] = None


class PlaygroundExecuteResponse(BaseModel):
    """Playground 执行响应"""
    output: str
    status: str
    agentSteps: Optional[List[AgentStep]] = None


@app.post("/api/playground/execute", response_model=PlaygroundExecuteResponse)
async def execute_playground(request: PlaygroundExecuteRequest):
    """执行 Playground Flow - 使用 SAGE 引擎"""
    try:
        from datetime import datetime
        import sys
        from pathlib import Path
        import time
        
        # 添加 sage-studio 到 Python 路径
        studio_path = Path(__file__).parent.parent.parent.parent
        if str(studio_path) not in sys.path:
            sys.path.insert(0, str(studio_path))
        
        from sage.studio.models import PipelineStatus, NodeStatus
        from sage.studio.services import get_pipeline_builder
        
        print(f"🎯 Executing playground - flowId: {request.flowId}, sessionId: {request.sessionId}")
        print(f"📝 Input: {request.input}")
        
        # 1. 加载 Flow 定义
        flow_data = _load_flow_data(request.flowId)
        if not flow_data:
            raise HTTPException(status_code=404, detail=f"Flow not found: {request.flowId}")
        
        # 2. 转换为 VisualPipeline
        visual_pipeline = _convert_to_flow_definition(flow_data, request.flowId)
        
        # 3. 使用 PipelineBuilder 构建 SAGE Pipeline
        builder = get_pipeline_builder()
        sage_env = builder.build(visual_pipeline)
        
        # 4. 执行 Pipeline
        start_time = time.time()
        job = sage_env.execute()
        
        # 等待执行完成（简化版本，实际应该异步处理）
        # TODO: 实现真正的异步执行和状态轮询
        import asyncio
        await asyncio.sleep(0.1)  # 让出控制权
        
        execution_time = time.time() - start_time
        
        # 5. 生成执行步骤（简化版本）
        agent_steps = []
        for idx, node in enumerate(visual_pipeline.nodes, start=1):
            agent_steps.append(AgentStep(
                step=idx,
                type="tool_call",
                content=f"执行节点: {node.label}",
                timestamp=datetime.now().isoformat(),
                duration=int(execution_time * 1000 / len(visual_pipeline.nodes)),
                toolName=node.label,
                toolInput=node.config,
                toolOutput={"status": "completed"}
            ))
        
        # 6. 生成输出
        output_text = f"Pipeline 执行成功！总耗时: {execution_time:.2f}秒"
        
        print(f"✅ Playground execution completed: {PipelineStatus.COMPLETED.value}")
        
        return PlaygroundExecuteResponse(
            output=output_text,
            status=PipelineStatus.COMPLETED.value,
            agentSteps=agent_steps if agent_steps else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Error executing playground: {e}")
        print(traceback.format_exc())
        
        # 返回友好的错误信息
        return PlaygroundExecuteResponse(
            output=f"执行出错: {str(e)}",
            status="failed",
            agentSteps=None
        )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
