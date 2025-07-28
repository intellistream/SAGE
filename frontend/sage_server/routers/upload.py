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

@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    # 处理上传的文件
    # 可以将文件保存到/data/file目录下
    rpath = os.path.join("data", "file")
    file_path = f"{rpath}/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    print(file_path)
    return {"filename": file.filename}