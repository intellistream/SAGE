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

class OperatorInfo(BaseModel):
    id: int
    name:str
    code:str
    isCustom:bool
    description:str

@router.get("/get/all")
async def get_all_operators(page: int = 1, size: int = 10):
    # /data/operators/*.json
    operator_path = os.path.join("data", "operators")
    operator_list = []
    if not os.path.exists(operator_path):
        os.makedirs(operator_path, exist_ok=True)
    
    # 获取所有符合条件的文件
    try:
        json_files = [f for f in os.listdir(operator_path) if f.endswith(".json")]
    except Exception as e:
        logging.error(f"Error listing directory {operator_path}: {str(e)}")
        return {
            "items": [],
            "total": 0,
            "page": page,
            "size": size,
            "pages": 0
        }
    
    # 计算分页
    total = len(json_files)
    start_idx = (page - 1) * size
    end_idx = min(start_idx + size, total)
    
    # 只处理当前页的文件
    for operator_file in json_files[start_idx:end_idx]:
        operator_file_path = os.path.join(operator_path, operator_file)
        try:
            # 检查文件是否为空
            if os.path.getsize(operator_file_path) == 0:
                logging.warning(f"Empty file: {operator_file_path}")
                continue
                
            with open(operator_file_path, "r") as f:
                file_content = f.read().strip()
                if not file_content:  # 检查文件内容是否为空
                    logging.warning(f"Empty content in file: {operator_file_path}")
                    continue
                    
                operator_info = json.loads(file_content)
                operator_list.append(OperatorInfo(**operator_info))
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing error in {operator_file_path}: {str(e)}")
            # 可以选择修复或删除损坏的文件
            # os.remove(operator_file_path)  # 谨慎使用，这会删除损坏的文件
        except Exception as e:
            logging.error(f"Error processing {operator_file_path}: {str(e)}")
    
    # 返回分页结果和元数据
    return {
        "items": operator_list,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size if total > 0 else 0  # 计算总页数
    }

@router.get("/get/operators")
async def get_all_operators():
    # /data/operators/*.json
    operator_path = os.path.join("data", "operators")
    operator_list = []
    if not os.path.exists(operator_path):
        os.makedirs(operator_path, exist_ok=True)

    # 获取所有符合条件的文件
    try:
        json_files = [f for f in os.listdir(operator_path) if f.endswith(".json")]
    except Exception as e:
        logging.error(f"Error listing directory {operator_path}: {str(e)}")
        return {
            "items": [],
            "total": 0  ,    
        }

    # 处理所有文件
    for operator_file in json_files:
        operator_file_path = os.path.join(operator_path, operator_file)
        try:
            # 检查文件是否为空
            if os.path.getsize(operator_file_path) == 0:
                logging.warning(f"Empty file: {operator_file_path}")
                continue
            with open(operator_file_path, "r") as f:
                file_content = f.read().strip()
                if not file_content:  # 检查文件内容是否为空
                    logging.warning(f"Empty content in file: {operator_file_path}")
                    continue

                operator_info = json.loads(file_content)
                operator_list.append(OperatorInfo(**operator_info))
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing error in {operator_file_path}: {str(e)}")
            # 可以选择修复或删除损坏的文件
            # os.remove(operator_file_path)  # 谨慎使用，这会删除损坏的文件
        except Exception as e:
            logging.error(f"Error processing {operator_file_path}: {str(e)}")


    return {
        "items": operator_list,
        "total": len(operator_list)
    }
@router.post("/create")
async def create_operator(operator_info: Request):
    # Parse the request body
    try:
        operator_data = await operator_info.json()
        print(f"Received operator data: {operator_data}")
        
        # Ensure required fields are present
        required_fields = ["name", "code", "description"]
        for field in required_fields:
            if field not in operator_data or not operator_data[field]:
                raise HTTPException(
                    status_code=422, 
                    detail=f"Field '{field}' is required and cannot be empty"
                )
        
        # Create operator directory if it doesn't exist
        operator_path = os.path.join("data", "operators")
        if not os.path.exists(operator_path):
            os.makedirs(operator_path, exist_ok=True)
        
        # Generate ID (count existing files + 1)
        try:
            existing_files = [f for f in os.listdir(operator_path) if f.endswith(".json")]
            new_id = len(existing_files) + 1
        except Exception as e:
            logging.error(f"Error counting existing operators: {str(e)}")
            new_id = 1
        
        # Create complete operator object
        operator = {
            "id": new_id,
            "name": operator_data.get("name", ""),
            "code": operator_data.get("code", ""),
            "isCustom": True,
            "description": operator_data.get("description", "")
        }
        
        # Write to file
        operator_file_path = os.path.join(operator_path, f"{operator['name']}.json")
        with open(operator_file_path, "w") as f:
            json.dump(operator, f, indent=2)
        
        return operator
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logging.error(f"Error creating operator: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating operator: {str(e)}")

@router.delete("/delete/{operator_id}/{operator_name}")
async def delete_operator(operator_id: int,operator_name:str):
    operator_path = os.path.join("data", "operators")
    
    # 检查目录是否存在
    if not os.path.exists(operator_path) or not os.path.isdir(operator_path):
        raise HTTPException(status_code=404, detail="Operators directory not found")
    
    # filepath
    operator_file_path = os.path.join(operator_path, f"{operator_name}.json")
    
    try:
        with open(operator_file_path, "r") as f:
            operator_info = json.load(f)

        if operator_info["id"] != operator_id:
            raise HTTPException(status_code=400, detail="Operator ID does not match the provided operator name")
        else:
            os.remove(operator_file_path)
            return {"message": f"Operator with ID {operator_id} deleted successfully"}
    except Exception as e:
        logging.error(f"Error listing directory {operator_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing operators: {str(e)}")
    
    if not found:
        raise HTTPException(status_code=404, detail=f"Operator with ID {operator_id} not found")
        
    return {"message": f"Operator with ID {operator_id} deleted successfully"}


@router.put("/update/{id}/{old_name}")
async def update_operator(id: int,old_name:str, operator_info: Request):
    try:
        # 解析请求体
        operator_data = await operator_info.json()

        # 确保所需字段存在
        required_fields = ["name", "code", "description", "isCustom"]
        for field in required_fields:
            if field not in operator_data or not operator_data[field]:
                raise HTTPException(
                    status_code=422,
                    detail=f"Field '{field}' is required and cannot be empty"
                )
        
        # 检查 isCustom 字段的有效性
        if operator_data["isCustom"] is not True:
            raise HTTPException(
                status_code=422,
                detail=f"Field 'isCustom' should be True"
            )
        
        
        operator_path = os.path.join("data", "operators")
        old_operator_file_path = os.path.join(operator_path, f"{old_name}.json")

        # 检查该操作员文件是否存在
        if not os.path.exists(old_operator_file_path):
            raise HTTPException(status_code=404, detail="Operator not found")

        # 读取现有操作员信息
        with open(old_operator_file_path, "r") as f:
            operator_info_existing = json.load(f)
        
        # 比对ID是否匹配
        if operator_info_existing["id"] != id:
            raise HTTPException(status_code=400, detail="Operator ID mismatch")

        # 删除原操作员文件
        os.remove(old_operator_file_path)

        
        operator_info_existing["name"] = operator_data.get("name", operator_info_existing["name"])
        operator_info_existing["code"] = operator_data.get("code", operator_info_existing["code"])
        operator_info_existing["description"] = operator_data.get("description", operator_info_existing["description"])
        operator_info_existing["isCustom"] = operator_data.get("isCustom", operator_info_existing["isCustom"])
        name = operator_info_existing["name"]
       
        new_operator_file_path = os.path.join(operator_path, f"{name}.json")
        with open(new_operator_file_path, "w") as f:
            json.dump(operator_info_existing, f, indent=2)

        return {"message": f"Operator with ID {id} updated successfully", "operator": operator_info_existing}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logging.error(f"Error updating operator: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating operator: {str(e)}")
