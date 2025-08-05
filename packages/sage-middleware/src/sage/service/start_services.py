#!/usr/bin/env python3
"""
SAGE 服务化架构启动脚本
一键启动所有微服务
"""
import asyncio
import argparse
import sys
from pathlib import Path

# 添加项目路径到Python路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sage.service.launcher.service_launcher import ServiceLauncher

async def start_services(config_type: str = "standard", 
                        kv_backend: str = "memory",
                        redis_url: str = None,
                        persist_dir: str = None):
    """启动服务"""
    
    print("🚀 SAGE Microservices Launcher")
    print("=" * 50)
    print(f"Configuration: {config_type}")
    print(f"KV Backend: {kv_backend}")
    if redis_url:
        print(f"Redis URL: {redis_url}")
    if persist_dir:
        print(f"Vector Storage: {persist_dir}")
    print("=" * 50)
    
    launcher = ServiceLauncher()
    
    try:
        if config_type == "standard":
            # 标准配置：KV + VDB + Memory
            launcher.add_kv_service(
                name="kv-service",
                port=8001,
                backend_type=kv_backend,
                redis_url=redis_url
            )
            
            launcher.add_vdb_service(
                name="vdb-service",
                port=8002,
                collection_name="sage_vectors",
                persist_directory=persist_dir
            )
            
            launcher.add_memory_service(
                name="memory-service",
                port=8000
            )
            
        elif config_type == "minimal":
            # 最小配置：只有Memory编排服务
            launcher.add_memory_service(
                name="memory-service",
                port=8000
            )
            
        elif config_type == "kv-only":
            # 只启动KV服务
            launcher.add_kv_service(
                name="kv-service",
                port=8001,
                backend_type=kv_backend,
                redis_url=redis_url
            )
            
        elif config_type == "vdb-only":
            # 只启动VDB服务
            launcher.add_vdb_service(
                name="vdb-service",
                port=8002,
                collection_name="sage_vectors",
                persist_directory=persist_dir
            )
        
        else:
            print(f"❌ Unknown configuration type: {config_type}")
            return
        
        # 启动服务并等待
        await launcher.run_forever()
        
    except Exception as e:
        print(f"❌ Failed to start services: {e}")
        sys.exit(1)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="SAGE Microservices Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 启动标准配置（KV + VDB + Memory）
  python start_services.py
  
  # 使用Redis作为KV后端
  python start_services.py --kv-backend redis --redis-url redis://localhost:6379
  
  # 启用向量持久化存储
  python start_services.py --persist-dir ./vector_storage
  
  # 只启动KV服务
  python start_services.py --config kv-only
  
  # 最小配置
  python start_services.py --config minimal
        """
    )
    
    parser.add_argument(
        "--config",
        choices=["standard", "minimal", "kv-only", "vdb-only"],
        default="standard",
        help="Service configuration type (default: standard)"
    )
    
    parser.add_argument(
        "--kv-backend",
        choices=["memory", "redis"],
        default="memory",
        help="KV storage backend (default: memory)"
    )
    
    parser.add_argument(
        "--redis-url",
        default=None,
        help="Redis connection URL (e.g., redis://localhost:6379)"
    )
    
    parser.add_argument(
        "--persist-dir",
        default=None,
        help="Directory for vector storage persistence"
    )
    
    args = parser.parse_args()
    
    # 运行服务
    try:
        asyncio.run(start_services(
            config_type=args.config,
            kv_backend=args.kv_backend,
            redis_url=args.redis_url,
            persist_dir=args.persist_dir
        ))
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()
