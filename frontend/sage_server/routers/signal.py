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
from regex import F
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
from pydantic import BaseModel, ConfigDict, FilePath, validator, Field
from starlette.background import BackgroundTask


router = APIRouter()

# @router.post("/start/{jobId}")
# async def start_job(jobId: str):
#     # createJobInfoJson()
#
#     return True
import asyncio
from start_a_pipeline import  init_memory_and_pipeline
# 用于存储正在运行的任务，键为job_id，值为任务对象
running_tasks = {}
running_pipelines = {}

import json
import os
import tempfile
import shutil

def update_json_field(file_path: str, field: str, value):
    """
    安全地更新 JSON 顶层字段，支持任意类型的值。
    
    - 支持覆盖原字段值
    - 会创建临时文件，避免写入中途失败导致文件损坏
    """
    # 确保文件存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # 读取 JSON 内容
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 格式错误: {e}")
    
    # 更新字段
    data[field] = value
    # 写入到临时文件，再替换原文件（原子操作）
    dir_name = os.path.dirname(file_path)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=dir_name, encoding="utf-8") as tmpfile:
        json.dump(data, tmpfile, indent=4, ensure_ascii=False)
        tmpfile.flush()
        os.fsync(tmpfile.fileno())
        temp_path = tmpfile.name


    shutil.move(temp_path, file_path)

    


    


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

        # # 读取作业信息
        # with open(file_path, "r", encoding="utf-8") as f:
        #     job_info = json.load(f)

        # # 更新运行状态
        # job_info["isRunning"] = False

        # # 保存更新后的作业信息
        # with open(file_path, "w", encoding="utf-8") as f:
        #     json.dump(job_info, f, indent=4, ensure_ascii=False)
        update_json_field(file_path, "isRunning", False)

        # 取消正在运行的任务
        if jobId in running_tasks and not running_tasks[jobId].done():
            running_tasks[jobId].cancel()
            logging.info(f"已取消作业 {jobId} 的运行任务")
        if jobId in running_pipelines :
            running_pipelines[jobId].stop()
            del running_pipelines[jobId]
            logging.info(f"已取消作业 {jobId} 的管道任务")

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

        # # 读取作业信息
        # with open(file_path, "r", encoding="utf-8") as f:
        #     job_info = json.load(f)

        # # 更新运行状态
        # job_info["isRunning"] = True
        

        # with open(file_path, "w", encoding="utf-8") as f:
        #     json.dump(job_info, f, indent=4, ensure_ascii=False)

        update_json_field(file_path, "isRunning", True)
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
        if not hasattr(current_app.state, "retriver_collection"):
            logging.error("应用状态中不存在retriver_collection")
            return
        retriver_collection = current_app.state.retriver_collection
        config_path = os.path.join("data", "config", f"{job_id}.yaml")
        if not os.path.exists(config_path):
            config_path = os.path.join("data", "config", "default.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        config["retriever"]["ltm_collection"] = retriver_collection
        # 获取作业信息
        job_data_dir = os.path.join("data", "jobinfo")
        file_path = os.path.join(job_data_dir, f"{job_id}.json")

        if not os.path.exists(file_path):
            logging.error(f"作业 {job_id} 的文件不存在")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            job_info = json.load(f)

        operators_config = build_operators_config_from_job(job_info)
        pipeline = await  init_memory_and_pipeline(job_id, config,operators_config)
        logging.info(f"作业 {job_id} 已开始处理")
        running_pipelines[job_id] = pipeline


        # await asyncio.to_thread(init_memory_and_pipeline,job_id)
        # await init_memory_and_pipeline(job_id)
        # logging.info(f"作业 {job_id} 已完成处理")


        # 任务完成后更新作业状态
    #     job_data_dir = os.path.join("data", "jobinfo")
    #     file_path = os.path.join(job_data_dir, f"{job_id}.json")

    #     if os.path.exists(file_path):
    #         try:
    #             with open(file_path, "r", encoding="utf-8") as f:
    #                 job_info = json.load(f)
    #             if not isinstance(job_info, dict):
    #                 raise ValueError(f"{file_path} 内容不是合法 JSON 对象")
    #             job_info["isRunning"] = False

    #             with open(file_path, "w", encoding="utf-8") as f:
    #                 json.dump(job_info, f, indent=4, ensure_ascii=False)
    #         except Exception as e:
    #             logging.error(f"更新作业状态时出错: {str(e)}")
    except Exception as e:
        logging.error(f"处理作业 {job_id} 时出错: {str(e)}")
    finally:
        # 从运行任务字典中移除
        logging.info(f"作业 {job_id} 处理任务")


def build_operators_config_from_job(job_info):
    """
    从作业信息构建operators配置，用于传递给init_memory_and_pipeline函数
    """
    operators_config = {
        "source": None,
        "steps": [],
        "sink": None
    }

    # 从operators目录加载所有操作符信息
    operators_dir = os.path.join("data", "operators")
    operator_type_map = {}

    # 加载所有操作符
    if os.path.exists(operators_dir):
        for filename in os.listdir(operators_dir):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(operators_dir, filename), "r", encoding="utf-8") as f:
                        op_data = json.load(f)
                        # 将ID映射到类型名称
                        if "id" in op_data and "name" in op_data:
                            operator_type_map[str(op_data["id"])] = op_data["name"]
                except Exception as e:
                    logging.warning(f"读取操作符配置文件 {filename} 时出错: {str(e)}")

    # 获取所有操作符节点
    all_operators = job_info.get("operators", [])

    # 确保所有ID都是字符串类型
    for op in all_operators:
        op["id"] = str(op["id"]) if not isinstance(op["id"], str) else op["id"]

    # 找到源节点和汇节点
    source_op = None
    sink_op = None
    intermediate_ops = []

    for op in all_operators:
        if op.get("isSource"):
            source_op = op
        elif op.get("isSink"):
            sink_op = op
        else:
            intermediate_ops.append(op)

    # 设置源节点配置
    if source_op:
        # 查找操作符类型，如果找不到则使用默认值
        source_type = operator_type_map.get(source_op["id"], "FileSource")
        operators_config["source"] = {
            "type": source_type,
            "params": {}
        }

    # 设置汇节点配置
    if sink_op:
        sink_type = operator_type_map.get(sink_op["id"], "FileSink")
        operators_config["sink"] = {
            "type": sink_type,
            "params": {}
        }

    # 创建operatorId到操作符信息的映射
    op_map = {op["id"]: op for op in all_operators}

    # 从源节点开始逐层构建步骤
    sorted_ops = []
    if source_op:
        current_layer = source_op.get("downstream", [])
        # 确保下游ID也是字符串类型
        current_layer = [str(d) for d in current_layer]

        while current_layer:
            next_layer = []
            for op_id in current_layer:
                op = op_map.get(op_id)
                if op and not op.get("isSink") and op not in sorted_ops:
                    sorted_ops.append(op)
                    # 确保下游ID是字符串
                    downstream = [str(d) for d in op.get("downstream", [])]
                    next_layer.extend(downstream)
            current_layer = next_layer

    # 将排序好的中间节点添加到steps中
    # 默认方法名映射
    default_method_names = {
        "SimpleRetriever": "retrieve",
        "QAPromptor": "construct_prompt",
        "OpenAIGenerator": "generate_response",
        "TerminalSink": "sink",
    }

    print(operator_type_map)

    for op in sorted_ops:
        op_type = operator_type_map.get(op["id"], "SimpleRetriever")
        # 根据操作符类型选择默认方法名，如果没有则使用操作符名称的小写
        method_name = default_method_names.get(op_type, op["name"].lower().replace(" ", "_"))

        step_config = {
            "name": method_name,
            "type": op_type,
            "params": {}
        }
        operators_config["steps"].append(step_config)

    logging.info(f"构建的operators配置: {operators_config}")
    return operators_config