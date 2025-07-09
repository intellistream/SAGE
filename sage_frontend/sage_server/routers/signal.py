import json
import logging
import os
# from aiocache import cached

from regex import F
import requests

import yaml
from fastapi import (
    HTTPException,
    Request,
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

from sage_frontend.sage_server.start_a_pipeline import  init_memory_and_pipeline


# 用于存储正在运行的任务，键为job_id，值为任务对象
running_tasks = {}
running_pipelines = {}

import json
import os
import tempfile
import shutil


    

def update_json_field(file_path: str, *args):
    """
    安全地更新 JSON 顶层字段，支持同时更新多个字段。

    参数:
        file_path: JSON 文件路径
        *args: 可变参数，按键值对的顺序传递字段和值
               格式: "字段名1", 值1, "字段名2", 值2, ...
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
    if len(args) % 2 != 0:
        raise ValueError("参数必须成对出现：字段名和值")
    for i in range(0, len(args), 2):
        field = args[i]
        value = args[i + 1]
        data[field] = value

    # 写入到临时文件，再替换原文件（原子操作）
    dir_name = os.path.dirname(file_path)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=dir_name, encoding="utf-8") as tmpfile:
        json.dump(data, tmpfile, indent=4, ensure_ascii=False)
        tmpfile.flush()
        os.fsync(tmpfile.fileno())
        temp_path = tmpfile.name

    shutil.move(temp_path, file_path)

    


@router.post("/stop/{jobId}/{duration}")
async def stop_job(jobId: str,duration:str ):
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


        update_json_field(file_path, "isRunning", False)
        update_json_field(file_path, "duration", duration)
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
@router.get("/status/{jobId}")
async def get_job_status(jobId:str):
    with open(os.path.join("data", "config", f"{jobId}.yaml"), "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    use_ray = False
    for key, value in config.items():
        if isinstance(value, dict) and any("remote" in str(v).lower() for v in value.values()):
            use_ray = True
            print(f"remote found in config for job {jobId}, using Ray")
            break

    return {"status": "success", "message": f"作业 {jobId} 正在运行","use_ray":use_ray}



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



        update_json_field(file_path, "isRunning", True)
        #读取duration
        with open(file_path, "r", encoding="utf-8") as f:
            job_info = json.load(f)
        duration_s = job_info.get("duration", "0")  # 默认值为0，如果没有设置
        #config 是否包含 “remote” 值
        with open(os.path.join("data", "config", f"{jobId}.yaml"), "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        use_ray = False
        for key, value in config.items():
            if isinstance(value, dict) and any("remote" in str(v).lower() for v in value.values()):
                use_ray = True
                print(f"remote found in config for job {jobId}, using Ray")
                break
        duration = eval(duration_s[:-1])
        print(f"start duration : {duration}")
        # 创建后台任务运行流处理管道
        task = asyncio.create_task(run_pipeline_task(jobId,request,use_ray=use_ray))
        running_tasks[jobId] = task

        return {"status": "success", "message": f"作业 {jobId} 已开始处理","duration":duration,"use_ray":use_ray}
    except Exception as e:
        logging.error(f"启动作业 {jobId} 时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动作业失败: {str(e)}")


async def run_pipeline_task(job_id: str,request: Request,use_ray:bool = False):
    """
    在后台运行管道处理任务
    """

    try:
        # 运行管道处理

        current_app =  request.app


        config_path = os.path.join("data", "config", f"{job_id}.yaml")
        if not os.path.exists(config_path):
            config_path = os.path.join("data", "config", "default.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 获取作业信息
        job_data_dir = os.path.join("data", "jobinfo")
        file_path = os.path.join(job_data_dir, f"{job_id}.json")

        if not os.path.exists(file_path):
            logging.error(f"作业 {job_id} 的文件不存在")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            job_info = json.load(f)

        operators_config = build_operators_config_from_job(job_info)
        if config['generator']['api_key'] is None or config['generator']['api_key'] == "":
            config['generator']['api_key'] = os.getenv("ALIBABA_API_KEY", None)
        print(f"use ray ... : {use_ray}")
        pipeline =init_memory_and_pipeline(job_id, config,operators_config,use_ray=use_ray)
        logging.info(f"作业 {job_id} 已开始处理")
        running_pipelines[job_id] = pipeline

    except Exception as e:
        logging.error(f"处理作业 {job_id} 时出错: {str(e)}")
    finally:

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
    transformation_map = {}
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
                        # 如果有transformation字段，也加入映射
                        if "transformation" in op_data:
                            transformation_map[str(op_data["id"])] = op_data["transformation"]
                except Exception as e:
                    logging.warning(f"读取操作符配置文件 {filename} 时出错: {str(e)}")

    # 获取所有操作符节点
    all_operators = job_info.get("operators", [])

    # 确保所有ID都是字符串类型 && 确保transformation字段是字符串类型
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
    for op in sorted_ops:
        op_type = operator_type_map.get(op["id"], "SimpleRetriever")

        # 从操作符配置文件中获取 transformation 字段
        transformation = transformation_map.get(op["id"], None)

        # 如果 transformation 存在，则使用它作为方法名，否则使用操作符名称的小写
        method_name = transformation if transformation else op["name"].lower().replace(" ", "_")
        print(op)
        print(method_name)
        step_config = {
            "name": method_name,
            "type": op_type,
            "params": {}
        }
        operators_config["steps"].append(step_config)




    logging.info(f"构建的operators配置: {operators_config}")
    return operators_config
