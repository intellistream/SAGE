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
# class TPGEdge(BaseModel):
#     srcOperatorID: str
#     dstOperatorID: str
#     dependencyType: str
#
# class TPGNode(BaseModel):
#     operatorID: str
#     txnType: str
#     targetTable: str
#     targetKey: str
#     edges: List[TPGEdge]
# class OverallTimeBreakdown(BaseModel):
#     overheadTime: int
#     streamTime: int
#     totalTime: int
#     txnTime: int
#
# class SchedulerTimeBreakdown(BaseModel):
#     exploreTime: int
#     usefulTime: int
#     abortTime: int
#     constructTime: int
#     trackingTime: int
#
# class Batch(BaseModel):
#     batchId: int
#     jobId: str
#     operatorID: str
#     throughput: float
#     minLatency: float
#     maxLatency: float
#     avgLatency: float
#     batchSize: int
#     batchDuration: float
#     latestBatchId: int
#     overallTimeBreakdown: OverallTimeBreakdown
#     schedulerTimeBreakdown: SchedulerTimeBreakdown
#     accumulativeLatency: float
#     accumulativeThroughput: float
#     scheduler: str
#     tpg: List[TPGNode]
#
#
# @router.get("/get/all/{job_id}/{operator_id}", response_model=List[Batch])
# async def find_all_batches(job_id: str, operator_id: str):
#     # 定义存储路径
#     PATH = "data"  # 请根据实际情况修改路径
#     directory = os.path.join(PATH, job_id, operator_id)
#
#     batches = []
#     if os.path.exists(directory) and os.path.isdir(directory):
#         # 获取所有JSON文件
#         json_files = [f for f in os.listdir(directory) if f.endswith('.json')]
#
#         for json_file in json_files:
#             file_path = os.path.join(directory, json_file)
#             try:
#                 with open(file_path, 'r') as f:
#                     batch_data = json.load(f)
#                     batch = Batch(**batch_data)
#                     batches.append(batch)
#             except Exception as e:
#                 # 记录错误但继续处理其他文件
#                 logging.error(f"Error processing {file_path}: {str(e)}")
#
#     return batches
#
# @router.get("/get/{job_id}/{batch_id}/{operator_id}", response_model=Optional[Batch])
# async def find_batch(job_id: str, batch_id: int, operator_id: str):
#     # 定义存储路径
#     PATH = "data"  # 请根据实际情况修改路径
#     directory = os.path.join(PATH, job_id, operator_id)
#
#     if os.path.exists(directory) and os.path.isdir(directory):
#         file_path = os.path.join(directory, f"{batch_id}.json")
#
#         if os.path.exists(file_path) and os.path.isfile(file_path):
#             try:
#                 with open(file_path, 'r') as f:
#                     batch_data = json.load(f)
#                     return Batch(**batch_data)
#             except Exception as e:
#                 logging.error(f"Error processing {file_path}: {str(e)}")
#                 raise HTTPException(status_code=500, detail=f"Error processing batch file: {str(e)}")
#
#     # 如果找不到文件或目录不存在，返回None
#     return None
#