import asyncio
from calendar import c
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

# 定义操作符模型
class Operator(BaseModel):
    id: str
    name: str
    numOfInstances: int  
    throughput: float
    latency: float
    explorationStrategy: str
    schedulingGranularity: str
    abortHandling: str
    downstream: List[int]
  

# 定义时间分解模型
class TotalTimeBreakdown(BaseModel):
    totalTime: float
    serializeTime: float
    persistTime: float
    streamProcessTime: float
    overheadTime: float


# 定义调度器时间分解模型
class OverallTimeBreakdown(BaseModel):
    exploreTime: float
    usefulTime: float
    abortTime: float
    constructTime: float
    trackingTime: float

# 定义作业信息模型，匹配前端 Job 接口
class JobInfo(BaseModel):
    jobId: str
    name: str
    nthreads: str
    cpu: str
    ram: str
    startTime: str
    duration: str
    isRunning: bool
    nevents: int
    minProcessTime: float
    maxProcessTime: float
    meanProcessTime: float
    latency: float
    throughput: float
    ncore: int
    operators: List[Operator]
    totalTimeBreakdown: TotalTimeBreakdown
    schedulerTimeBreakdown: OverallTimeBreakdown
    periodicalThroughput: List[float]
    periodicalLatency: List[float]

@router.get("/get/all", response_model=List[JobInfo])
async def job_info():
    """
    获取所有作业信息
    返回前端需要的作业列表，从data/jobinfo目录下读取JSON文件
    """
    job_data_dir = os.path.join("data", "jobinfo")
    jobs = []
    
    # 确保目录存在
    if not os.path.exists(job_data_dir):
        os.makedirs(job_data_dir, exist_ok=True)
        
    
    # 读取目录中的所有JSON文件
    try:
        for filename in os.listdir(job_data_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(job_data_dir, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    job_data = json.load(f)
                    jobs.append(job_data)
    except Exception as e:
        logging.error(f"读取作业数据时出错: {str(e)}")
        # 如果读取失败，返回空列表
        return []
    
    return jobs

@router.get("/get/{id}", response_model=JobInfo)
def get_job_info(id: str):
    """
    获取指定作业信息
    """
    job_data_dir = os.path.join("data", "jobinfo")
    file_path = os.path.join(job_data_dir, f"{id}.json")
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        job_data = json.load(f)
    return job_data

@router.get("/config/{id}")
async def get_config(id: str):
    """
    获取指定作业的配置信息
    如果指定ID的配置不存在，则返回默认配置
    """
    config_dir = os.path.join("data", "config")
    file_path = os.path.join(config_dir, f"{id}.yaml")
    default_path = os.path.join(config_dir, "default.yaml")

    # 确保配置目录存在
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
        
    # 如果指定ID的配置文件不存在，使用默认配置
    if not os.path.exists(file_path):
        if not os.path.exists(default_path):
            raise HTTPException(status_code=404, detail="配置文件不存在且无默认配置")
        
        # 将默认配置复制一份作为该ID的配置
        try:
            with open(default_path, "r", encoding="utf-8") as src:
                default_content = src.read()
            
            # 保存为指定ID的配置文件
            with open(file_path, "w", encoding="utf-8") as dst:
                dst.write(default_content)
            
            logging.info(f"已为ID {id} 创建配置文件（从默认配置复制）")
        except Exception as e:
            logging.error(f"复制默认配置时出错: {str(e)}")
            # 如果复制失败，仍然使用默认配置文件
            file_path = default_path
        
    # 读取配置文件内容
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            config_content = f.read()
        return {"data": config_content}
    except Exception as e:
        logging.error(f"读取配置文件时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"读取配置文件失败: {str(e)}")
        


@router.put("/config/update/{pipeline_id}")
async def update_config(pipeline_id: str, config_data: dict):
    """
    更新指定作业的配置信息
    接收前端传来的配置内容，并保存到对应的配置文件中
    """
    config_dir = os.path.join("data", "config")
    file_path = os.path.join(config_dir, f"{pipeline_id}.yaml")
    
    # 确保配置目录存在
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
    print(config_data)
    # 获取配置内容
    config_content = config_data.get("config", "")
    print(f"Received config for pipeline {pipeline_id}: {config_content}")
    if not config_content:
        raise HTTPException(status_code=400, detail="配置内容不能为空")
    
    # 保存配置到文件
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(config_content)
            logging.info(f"已更新ID {pipeline_id} 的配置文件 {file_path}")
       
    except Exception as e:
        logging.error(f"保存配置文件时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存配置文件失败: {str(e)}")