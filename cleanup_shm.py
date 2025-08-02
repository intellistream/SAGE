#!/usr/bin/env python3
"""
清理SAGE队列相关的共享内存段
"""

import subprocess
import re
import os

def cleanup_sage_shared_memory():
    """清理SAGE相关的共享内存段"""
    print("清理SAGE队列共享内存段...")
    
    try:
        # 列出所有共享内存段
        result = subprocess.run(['ipcs', '-m'], capture_output=True, text=True)
        if result.returncode != 0:
            print("无法获取共享内存段信息")
            return
        
        lines = result.stdout.strip().split('\n')
        cleaned_count = 0
        
        for line in lines:
            # 跳过标题行
            if 'shmid' in line or 'key' in line or line.startswith('--'):
                continue
                
            # 解析共享内存段信息
            fields = line.split()
            if len(fields) >= 2:
                shmid = fields[1]
                
                # 尝试删除共享内存段
                try:
                    del_result = subprocess.run(['ipcrm', '-m', shmid], 
                                              capture_output=True, text=True)
                    if del_result.returncode == 0:
                        print(f"删除共享内存段: {shmid}")
                        cleaned_count += 1
                    else:
                        print(f"无法删除共享内存段 {shmid}: {del_result.stderr.strip()}")
                except Exception as e:
                    print(f"删除共享内存段 {shmid} 时出错: {e}")
        
        print(f"清理完成，删除了 {cleaned_count} 个共享内存段")
        
        # 清理 /dev/shm 中的 SAGE 相关文件
        shm_dir = '/dev/shm'
        if os.path.exists(shm_dir):
            sage_files = []
            try:
                for filename in os.listdir(shm_dir):
                    if ('sage' in filename.lower() or 
                        'ringbuf' in filename.lower() or
                        filename.startswith('boost_interprocess')):
                        sage_files.append(filename)
                
                for filename in sage_files:
                    filepath = os.path.join(shm_dir, filename)
                    try:
                        os.remove(filepath)
                        print(f"删除共享内存文件: {filepath}")
                    except PermissionError:
                        print(f"权限不足，无法删除: {filepath}")
                    except Exception as e:
                        print(f"删除文件 {filepath} 时出错: {e}")
                        
            except PermissionError:
                print("权限不足，无法访问 /dev/shm 目录")
            except Exception as e:
                print(f"清理 /dev/shm 时出错: {e}")
        
    except Exception as e:
        print(f"清理过程中出错: {e}")

if __name__ == "__main__":
    cleanup_sage_shared_memory()
