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
import yaml
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

# @router.post("/start/{jobId}")
# async def start_job(jobId: str):
#     # createJobInfoJson()
#
#     return True
import asyncio
from app.start_pipeline import  init_memory_and_pipeline
# 用于存储正在运行的任务，键为job_id，值为任务对象
running_tasks = {}


@router.post("/stop/{jobId}")
async def stop_job(jobId: str):
    """
    停止指定ID的流处理作业
    """
    try:
        # 获取作业信息文件路径
        job_data_dir = os.path.join("data", "jobinfo")
        file_path = os.path.join(job_data_dir, f"{jobId}.json")

        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"作业 {jobId} 不存在")

        # 读取作业信息
        with open(file_path, "r", encoding="utf-8") as f:
            job_info = json.load(f)

        # 更新运行状态
        job_info["isRunning"] = False

        # 保存更新后的作业信息
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(job_info, f, indent=4, ensure_ascii=False)

        # 取消正在运行的任务
        if jobId in running_tasks and not running_tasks[jobId].done():
            running_tasks[jobId].cancel()
            logging.info(f"已取消作业 {jobId} 的运行任务")

        logging.info(f"已停止作业 {jobId}")
        return {"status": "success", "message": f"作业 {jobId} 已停止"}
    except Exception as e:
        logging.error(f"停止作业 {jobId} 时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"停止作业失败: {str(e)}")


@router.post("/start/{jobId}")
async def start_job(jobId: str, request: Request):
    """
    启动指定ID的流处理作业
    """
    try:
        # 检查任务是否已经在运行
        if jobId in running_tasks and not running_tasks[jobId].done():
            return {"status": "warning", "message": f"作业 {jobId} 已经在运行中"}

        # 获取作业信息文件路径
        job_data_dir = os.path.join("data", "jobinfo")
        file_path = os.path.join(job_data_dir, f"{jobId}.json")

        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"作业 {jobId} 不存在")

        # 读取作业信息
        with open(file_path, "r", encoding="utf-8") as f:
            job_info = json.load(f)

        # 更新运行状态
        job_info["isRunning"] = True
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(job_info, f, indent=4, ensure_ascii=False)

        # 创建后台任务运行流处理管道
        task = asyncio.create_task(run_pipeline_task(jobId,request))
        running_tasks[jobId] = task

        return {"status": "success", "message": f"作业 {jobId} 已开始处理"}
    except Exception as e:
        logging.error(f"启动作业 {jobId} 时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动作业失败: {str(e)}")


async def run_pipeline_task(job_id: str,request: Request):
    """
    在后台运行管道处理任务
    """

    try:
        # 运行管道处理

        current_app =  request.app
        if not hasattr(current_app.state, "manager_handle"):
            logging.error("应用状态中不存在manager_handle")
            return
        manager_handle = current_app.state.manager_handle
        config_path = os.path.join("data", "config", f"{job_id}.yaml")
        if not os.path.exists(config_path):
            config_path = os.path.join("data", "config", "default.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

   
        await  init_memory_and_pipeline(job_id, manager_handle, config)
        logging.info(f"作业 {job_id} 已开始处理")



        # await asyncio.to_thread(init_memory_and_pipeline,job_id)
        # await init_memory_and_pipeline(job_id)
        # logging.info(f"作业 {job_id} 已完成处理")


        # 任务完成后更新作业状态
        job_data_dir = os.path.join("data", "jobinfo")
        file_path = os.path.join(job_data_dir, f"{job_id}.json")

        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    job_info = json.load(f)
                if not isinstance(job_info, dict):
                    raise ValueError(f"{file_path} 内容不是合法 JSON 对象")
                job_info["isRunning"] = False

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(job_info, f, indent=4, ensure_ascii=False)
            except Exception as e:
                logging.error(f"更新作业状态时出错: {str(e)}")
    except Exception as e:
        logging.error(f"处理作业 {job_id} 时出错: {str(e)}")
    finally:
        # 从运行任务字典中移除
        if job_id in running_tasks:
            del running_tasks[job_id]