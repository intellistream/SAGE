#!/usr/bin/env python3
"""
SAGE CodeServer - 源代码服务器原型
集成现有的脚本工具，提供统一的Web界面和API

快速原型实现，专注于核心功能验证
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import subprocess

# FastAPI相关导入
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

# 导入现有的工具模块
sys.path.append(str(Path(__file__).parent.parent / "scripts"))

try:
    from test_runner import SAGETestRunner
    from advanced_dependency_analyzer_with_sage_mapping import SAGEDependencyAnalyzer
    from sage_package_manager import SagePackageManager
    from check_package_dependencies import DependencyAnalyzer
except ImportError as e:
    print(f"Warning: Could not import some tools: {e}")
    print("Make sure all required scripts are available in the scripts directory")

# 数据模型
class TestRunRequest(BaseModel):
    test_type: str = "all"  # all, diff, package
    target: Optional[str] = None
    base_branch: str = "main"
    workers: int = 4

class AnalysisRequest(BaseModel):
    scope: str = "all"  # all, package
    package: Optional[str] = None
    include_external: bool = True

class PackageOperationRequest(BaseModel):
    packages: List[str]
    operation: str  # install, build, clean
    mode: str = "development"

# 全局状态管理
class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Dict] = {}
        self.results: Dict[str, Any] = {}
    
    def create_task(self, task_type: str, params: Dict) -> str:
        task_id = f"{task_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.tasks[task_id] = {
            "id": task_id,
            "type": task_type,
            "status": "pending",
            "params": params,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "progress": 0
        }
        return task_id
    
    def update_task(self, task_id: str, **kwargs):
        if task_id in self.tasks:
            self.tasks[task_id].update(kwargs)
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        return self.tasks.get(task_id)
    
    def set_result(self, task_id: str, result: Any):
        self.results[task_id] = result

# 初始化
app = FastAPI(
    title="SAGE CodeServer",
    description="SAGE框架源代码服务器 - 集成测试、分析、包管理工具",
    version="1.0.0"
)

task_manager = TaskManager()
project_root = Path(__file__).parent.parent

# 静态文件服务
app.mount("/static", StaticFiles(directory=project_root / "static"), name="static")

# ==================== API路由 ====================

@app.get("/", response_class=HTMLResponse)
async def root():
    """主页面"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SAGE CodeServer</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { 
                font-family: Arial, sans-serif; 
                margin: 0; 
                padding: 20px; 
                background-color: #f5f5f5; 
            }
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
                background-color: white; 
                padding: 20px; 
                border-radius: 8px; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
            }
            .header { 
                text-align: center; 
                margin-bottom: 30px; 
                padding-bottom: 20px; 
                border-bottom: 2px solid #eee; 
            }
            .feature-grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                gap: 20px; 
                margin-bottom: 30px; 
            }
            .feature-card { 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                padding: 20px; 
                background-color: #fafafa; 
            }
            .feature-card h3 { 
                margin-top: 0; 
                color: #333; 
            }
            .btn { 
                background-color: #007bff; 
                color: white; 
                padding: 8px 16px; 
                border: none; 
                border-radius: 4px; 
                cursor: pointer; 
                text-decoration: none; 
                display: inline-block; 
                margin-right: 10px; 
                margin-top: 10px; 
            }
            .btn:hover { 
                background-color: #0056b3; 
            }
            .status-section { 
                margin-top: 30px; 
                padding: 20px; 
                background-color: #f8f9fa; 
                border-radius: 8px; 
            }
            .api-links { 
                margin-top: 20px; 
            }
            .api-links a { 
                display: inline-block; 
                margin-right: 15px; 
                color: #007bff; 
                text-decoration: none; 
            }
            .api-links a:hover { 
                text-decoration: underline; 
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 SAGE CodeServer</h1>
                <p>SAGE框架源代码服务器 - 集成开发工具平台</p>
            </div>
            
            <div class="feature-grid">
                <div class="feature-card">
                    <h3>🧪 测试中心</h3>
                    <p>运行智能测试，支持全量测试和差异测试，实时查看测试结果和报告。</p>
                    <button class="btn" onclick="runAllTests()">运行全部测试</button>
                    <button class="btn" onclick="runDiffTests()">运行差异测试</button>
                </div>
                
                <div class="feature-card">
                    <h3>📊 依赖分析</h3>
                    <p>分析包依赖关系，检测循环依赖，生成依赖关系图和优化建议。</p>
                    <button class="btn" onclick="runDependencyAnalysis()">分析依赖关系</button>
                    <button class="btn" onclick="checkCircularDeps()">检查循环依赖</button>
                </div>
                
                <div class="feature-card">
                    <h3>📦 包管理</h3>
                    <p>管理SAGE包的安装、构建和依赖关系，监控包状态和版本信息。</p>
                    <button class="btn" onclick="listPackages()">查看包状态</button>
                    <button class="btn" onclick="buildAllPackages()">构建所有包</button>
                </div>
                
                <div class="feature-card">
                    <h3>📈 系统状态</h3>
                    <p>监控系统资源使用情况，查看任务执行历史和性能统计。</p>
                    <button class="btn" onclick="getSystemStatus()">系统状态</button>
                    <button class="btn" onclick="getTaskHistory()">任务历史</button>
                </div>
            </div>
            
            <div class="status-section">
                <h3>📋 实时状态</h3>
                <div id="status-content">
                    <p>等待操作...</p>
                </div>
            </div>
            
            <div class="api-links">
                <h4>🔗 API文档和链接:</h4>
                <a href="/docs" target="_blank">Swagger API文档</a>
                <a href="/redoc" target="_blank">ReDoc API文档</a>
                <a href="/api/system/status">系统状态API</a>
                <a href="/api/packages/list">包列表API</a>
            </div>
        </div>
        
        <script>
            const statusDiv = document.getElementById('status-content');
            
            async function updateStatus(message) {
                statusDiv.innerHTML = `<p>⏳ ${message}</p>`;
            }
            
            async function showResult(result) {
                statusDiv.innerHTML = `<pre>${JSON.stringify(result, null, 2)}</pre>`;
            }
            
            async function runAllTests() {
                await updateStatus('启动全量测试...');
                try {
                    const response = await fetch('/api/test/run', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({test_type: 'all', workers: 4})
                    });
                    const result = await response.json();
                    await showResult(result);
                } catch (error) {
                    statusDiv.innerHTML = `<p style="color: red;">❌ 错误: ${error.message}</p>`;
                }
            }
            
            async function runDiffTests() {
                await updateStatus('启动差异测试...');
                try {
                    const response = await fetch('/api/test/run', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({test_type: 'diff', base_branch: 'main'})
                    });
                    const result = await response.json();
                    await showResult(result);
                } catch (error) {
                    statusDiv.innerHTML = `<p style="color: red;">❌ 错误: ${error.message}</p>`;
                }
            }
            
            async function runDependencyAnalysis() {
                await updateStatus('分析依赖关系...');
                try {
                    const response = await fetch('/api/analysis/dependencies', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({scope: 'all', include_external: true})
                    });
                    const result = await response.json();
                    await showResult(result);
                } catch (error) {
                    statusDiv.innerHTML = `<p style="color: red;">❌ 错误: ${error.message}</p>`;
                }
            }
            
            async function checkCircularDeps() {
                await updateStatus('检查循环依赖...');
                try {
                    const response = await fetch('/api/analysis/circular-deps');
                    const result = await response.json();
                    await showResult(result);
                } catch (error) {
                    statusDiv.innerHTML = `<p style="color: red;">❌ 错误: ${error.message}</p>`;
                }
            }
            
            async function listPackages() {
                await updateStatus('获取包列表...');
                try {
                    const response = await fetch('/api/packages/list');
                    const result = await response.json();
                    await showResult(result);
                } catch (error) {
                    statusDiv.innerHTML = `<p style="color: red;">❌ 错误: ${error.message}</p>`;
                }
            }
            
            async function buildAllPackages() {
                await updateStatus('构建所有包...');
                try {
                    const response = await fetch('/api/packages/build-all', {method: 'POST'});
                    const result = await response.json();
                    await showResult(result);
                } catch (error) {
                    statusDiv.innerHTML = `<p style="color: red;">❌ 错误: ${error.message}</p>`;
                }
            }
            
            async function getSystemStatus() {
                await updateStatus('获取系统状态...');
                try {
                    const response = await fetch('/api/system/status');
                    const result = await response.json();
                    await showResult(result);
                } catch (error) {
                    statusDiv.innerHTML = `<p style="color: red;">❌ 错误: ${error.message}</p>`;
                }
            }
            
            async function getTaskHistory() {
                await updateStatus('获取任务历史...');
                try {
                    const response = await fetch('/api/tasks/history');
                    const result = await response.json();
                    await showResult(result);
                } catch (error) {
                    statusDiv.innerHTML = `<p style="color: red;">❌ 错误: ${error.message}</p>`;
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# ==================== 测试相关API ====================

@app.post("/api/test/run")
async def run_tests(request: TestRunRequest, background_tasks: BackgroundTasks):
    """运行测试"""
    task_id = task_manager.create_task("test", request.dict())
    
    # 后台执行测试任务
    background_tasks.add_task(execute_test_task, task_id, request)
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": f"测试任务已启动: {request.test_type}"
    }

@app.get("/api/test/status/{task_id}")
async def get_test_status(task_id: str):
    """获取测试状态"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    result = task_manager.results.get(task_id)
    return {
        "task": task,
        "result": result
    }

async def execute_test_task(task_id: str, request: TestRunRequest):
    """执行测试任务"""
    task_manager.update_task(task_id, status="running", started_at=datetime.now().isoformat())
    
    try:
        # 使用现有的test_runner
        test_runner = SAGETestRunner(str(project_root))
        
        if request.test_type == "all":
            result = test_runner.run_all_tests(workers=request.workers)
        elif request.test_type == "diff":
            result = test_runner.run_smart_tests(base_branch=request.base_branch, workers=request.workers)
        elif request.test_type == "package" and request.target:
            result = test_runner.run_package_tests(request.target, workers=request.workers)
        else:
            raise ValueError(f"Unsupported test type: {request.test_type}")
        
        task_manager.set_result(task_id, result)
        task_manager.update_task(task_id, status="completed", completed_at=datetime.now().isoformat(), progress=100)
        
    except Exception as e:
        error_result = {"error": str(e), "type": type(e).__name__}
        task_manager.set_result(task_id, error_result)
        task_manager.update_task(task_id, status="failed", completed_at=datetime.now().isoformat())

# ==================== 依赖分析API ====================

@app.post("/api/analysis/dependencies")
async def analyze_dependencies(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """分析依赖关系"""
    task_id = task_manager.create_task("analysis", request.dict())
    
    background_tasks.add_task(execute_analysis_task, task_id, request)
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": "依赖分析任务已启动"
    }

@app.get("/api/analysis/circular-deps")
async def get_circular_dependencies():
    """获取循环依赖信息"""
    try:
        analyzer = SAGEDependencyAnalyzer(str(project_root / "packages"))
        results = analyzer.analyze()
        
        return {
            "circular_dependencies": results.get("circular_dependencies", []),
            "total_found": len(results.get("circular_dependencies", [])),
            "summary": {
                "files_analyzed": results.get("files_analyzed", 0),
                "total_imports": results.get("total_imports", 0),
                "invalid_imports": results.get("invalid_imports", 0)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def execute_analysis_task(task_id: str, request: AnalysisRequest):
    """执行依赖分析任务"""
    task_manager.update_task(task_id, status="running", started_at=datetime.now().isoformat())
    
    try:
        analyzer = SAGEDependencyAnalyzer(str(project_root / "packages"))
        result = analyzer.analyze()
        
        task_manager.set_result(task_id, result)
        task_manager.update_task(task_id, status="completed", completed_at=datetime.now().isoformat(), progress=100)
        
    except Exception as e:
        error_result = {"error": str(e), "type": type(e).__name__}
        task_manager.set_result(task_id, error_result)
        task_manager.update_task(task_id, status="failed", completed_at=datetime.now().isoformat())

# ==================== 包管理API ====================

@app.get("/api/packages/list")
async def list_packages():
    """获取包列表"""
    try:
        packages_dir = project_root / "packages"
        packages_info = []
        
        for package_dir in packages_dir.iterdir():
            if package_dir.is_dir() and (package_dir / "pyproject.toml").exists():
                # 读取包信息
                package_info = {
                    "name": package_dir.name,
                    "path": str(package_dir),
                    "has_pyproject": True,
                    "has_tests": (package_dir / "tests").exists(),
                    "installed": False  # 这里可以检查包是否已安装
                }
                
                # 尝试读取pyproject.toml获取更多信息
                try:
                    import toml
                    pyproject_path = package_dir / "pyproject.toml"
                    with open(pyproject_path, 'r', encoding='utf-8') as f:
                        pyproject_data = toml.load(f)
                        if 'project' in pyproject_data:
                            package_info.update({
                                "version": pyproject_data['project'].get('version', 'unknown'),
                                "description": pyproject_data['project'].get('description', ''),
                                "dependencies": pyproject_data['project'].get('dependencies', [])
                            })
                except Exception as e:
                    package_info["error"] = f"Failed to read pyproject.toml: {str(e)}"
                
                packages_info.append(package_info)
        
        return {
            "packages": packages_info,
            "total_count": len(packages_info)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/packages/build-all")
async def build_all_packages(background_tasks: BackgroundTasks):
    """构建所有包"""
    task_id = task_manager.create_task("build_all", {})
    
    background_tasks.add_task(execute_build_all_task, task_id)
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": "开始构建所有包"
    }

async def execute_build_all_task(task_id: str):
    """执行构建所有包的任务"""
    task_manager.update_task(task_id, status="running", started_at=datetime.now().isoformat())
    
    try:
        packages_dir = project_root / "packages"
        results = []
        
        for package_dir in packages_dir.iterdir():
            if package_dir.is_dir() and (package_dir / "pyproject.toml").exists():
                try:
                    # 使用pip install -e安装包
                    result = subprocess.run(
                        ["pip", "install", "-e", str(package_dir)],
                        capture_output=True,
                        text=True,
                        timeout=300  # 5分钟超时
                    )
                    
                    results.append({
                        "package": package_dir.name,
                        "success": result.returncode == 0,
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    })
                except Exception as e:
                    results.append({
                        "package": package_dir.name,
                        "success": False,
                        "error": str(e)
                    })
        
        task_manager.set_result(task_id, {"build_results": results})
        task_manager.update_task(task_id, status="completed", completed_at=datetime.now().isoformat(), progress=100)
        
    except Exception as e:
        error_result = {"error": str(e), "type": type(e).__name__}
        task_manager.set_result(task_id, error_result)
        task_manager.update_task(task_id, status="failed", completed_at=datetime.now().isoformat())

# ==================== 系统状态API ====================

@app.get("/api/system/status")
async def get_system_status():
    """获取系统状态"""
    try:
        import psutil
        
        # 系统资源信息
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(str(project_root))
        
        # 任务统计
        total_tasks = len(task_manager.tasks)
        running_tasks = len([t for t in task_manager.tasks.values() if t["status"] == "running"])
        completed_tasks = len([t for t in task_manager.tasks.values() if t["status"] == "completed"])
        failed_tasks = len([t for t in task_manager.tasks.values() if t["status"] == "failed"])
        
        return {
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                }
            },
            "tasks": {
                "total": total_tasks,
                "running": running_tasks,
                "completed": completed_tasks,
                "failed": failed_tasks
            },
            "project": {
                "root": str(project_root),
                "packages_dir": str(project_root / "packages")
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks/history")
async def get_task_history():
    """获取任务历史"""
    tasks = list(task_manager.tasks.values())
    tasks.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "tasks": tasks[:50],  # 返回最近50个任务
        "total_count": len(task_manager.tasks)
    }

@app.get("/api/tasks/{task_id}")
async def get_task_detail(task_id: str):
    """获取任务详情"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    result = task_manager.results.get(task_id)
    return {
        "task": task,
        "result": result
    }

# ==================== 启动服务器 ====================

def main():
    """启动SAGE CodeServer"""
    print("🚀 启动SAGE CodeServer...")
    print(f"📁 项目根目录: {project_root}")
    print(f"📦 包目录: {project_root / 'packages'}")
    print(f"🌐 Web界面: http://localhost:8888")
    print(f"📚 API文档: http://localhost:8888/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8888,
        reload=False,  # 生产环境建议关闭
        log_level="info"
    )

if __name__ == "__main__":
    main()
