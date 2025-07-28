import asyncio
import json
import logging
import os
import random
import re
import time
from typing import Optional, Union, List, Dict, Any
from urllib.parse import urlparse
import aiohttp
# from aiocache import cached
import requests
from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
    APIRouter,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, validator, Field
from starlette.background import BackgroundTask

router = APIRouter()

# 简化的节点结构，只包含后端需要的信息
class TopologyNode(BaseModel):
    id: str
    operatorId: Union[str, int]  # 原始操作符ID
    type: str
    name: str
    isSource: bool
    isSink: bool
    # 可以添加其他节点配置信息
    config: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(
        extra="allow"  # 允许额外字段
    )

# 简化的边结构
class TopologyEdge(BaseModel):
    id: str
    source: str  # 源节点ID
    target: str  # 目标节点ID
    # 可以添加边的配置信息
    config: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(
        extra="allow"  # 允许额外字段
    )

# 拓扑图基本信息
class TopologyData(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    
    # 节点信息
    nodes: List[TopologyNode]
    
    # 边信息
    edges: List[TopologyEdge]
    
    # 源节点和终结点
    sourceNodeId: str
    sinkNodeId: str
    
    model_config = ConfigDict(
        extra="allow"  # 允许额外字段
    )




@router.post("/submit")
async def upload_topology(topology_data: TopologyData):
    # 处理拓扑图数据
    print(topology_data)

    # 保存到data/jobinfo
    job_data_dir = os.path.join("data", "jobinfo")
    operators_dir = os.path.join("data", "operators")

    # 确保目录存在
    if not os.path.exists(job_data_dir):
        os.makedirs(job_data_dir, exist_ok=True)

    # 生成作业ID（如果未提供）
    job_id = topology_data.id or str(int(time.time()))
    job_name = topology_data.name or f"Job-{job_id}"

    # 创建节点ID到operatorId的映射
    node_id_to_operator_id = {node.id: node.operatorId for node in topology_data.nodes}

    # 收集操作符信息
    operators_info = []
    for node in topology_data.nodes:
        # 从operators目录读取操作符信息
        operator_file = os.path.join(operators_dir, f"{node.operatorId}.json")
        if not os.path.exists(operator_file):
            # 如果找不到对应的操作符文件，尝试使用名称查找
            for filename in os.listdir(operators_dir):
                if filename.endswith(".json"):
                    file_path = os.path.join(operators_dir, filename)
                    with open(file_path, "r", encoding="utf-8") as f:
                        op_data = json.load(f)
                        if op_data.get("name") == node.operatorId or op_data.get("id") == node.operatorId:
                            operator_file = file_path
                            break

        # 创建操作符信息
        operator_info = {
            "id": str(node.operatorId),
            "name": node.name,
            "isSource": node.isSource,
            "isSink": node.isSink,
            "numOfInstances": 1,  # 默认值
            "throughput": 0.0,  # 默认值
            "latency": 0.0,  # 默认值
            "explorationStrategy": "default",  # 默认值
            "schedulingGranularity": "default",  # 默认值
            "abortHandling": "default",  # 默认值
            "downstream": []  # 初始化下游操作符ID列表
        }

        # 如果有配置信息，更新操作符信息
        if node.config:
            if "numOfInstances" in node.config:
                operator_info["numOfInstances"] = node.config["numOfInstances"]
            if "explorationStrategy" in node.config:
                operator_info["explorationStrategy"] = node.config["explorationStrategy"]
            if "schedulingGranularity" in node.config:
                operator_info["schedulingGranularity"] = node.config["schedulingGranularity"]
            if "abortHandling" in node.config:
                operator_info["abortHandling"] = node.config["abortHandling"]

        operators_info.append(operator_info)

    # 创建节点ID到operators_info索引的映射
    node_id_to_index = {}
    for idx, node in enumerate(topology_data.nodes):
        node_id_to_index[node.id] = idx

    # 遍历所有边，填充下游节点信息
    for edge in topology_data.edges:
        source_id = edge.source
        target_id = edge.target

        # 如果源节点在我们的映射中，将目标节点的operatorId添加到源节点的downstream列表
        if source_id in node_id_to_index:
            source_index = node_id_to_index[source_id]
            target_operator_id = node_id_to_operator_id.get(target_id)  # 获取目标节点的operatorId
            if target_operator_id is not None:  # 确保目标操作符ID存在
                operators_info[source_index]["downstream"].append(target_operator_id)

    # 创建作业信息
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    job_info = {
        "jobId": job_id,
        "name": job_name,
        "nthreads": str(len(topology_data.nodes)),  # 默认值
        "cpu": "2",  # 默认值
        "ram": "4GB",  # 默认值
        "startTime": current_time,
        "duration": "0s",  # 初始值
        "isRunning": False,  # 初始状态为未运行
        "nevents": 0,  # 初始值
        "minProcessTime": 0.0,  # 初始值
        "maxProcessTime": 0.0,  # 初始值
        "meanProcessTime": 0.0,  # 初始值
        "latency": 0.0,  # 初始值
        "throughput": 0.0,  # 初始值
        "ncore": 2,  # 默认值
        "operators": operators_info,
        "totalTimeBreakdown": {
            "totalTime": 0.0,
            "serializeTime": 0.0,
            "persistTime": 0.0,
            "streamProcessTime": 0.0,
            "overheadTime": 0.0
        },
        "schedulerTimeBreakdown": {
            "exploreTime": 0.0,
            "usefulTime": 0.0,
            "abortTime": 0.0,
            "constructTime": 0.0,
            "trackingTime": 0.0
        },
        "periodicalThroughput": [],
        "periodicalLatency": []
    }

    # 保存作业信息到文件
    job_file_path = os.path.join(job_data_dir, f"{job_id}.json")
    try:
        with open(job_file_path, "w", encoding="utf-8") as f:
            json.dump(job_info, f, indent=4, ensure_ascii=False)
        logging.info(f"已保存作业信息到 {job_file_path}")
    except Exception as e:
        logging.error(f"保存作业信息时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存作业信息失败: {str(e)}")

    return {"message": "Topology data received and job created", "jobId": job_id}