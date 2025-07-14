# Python
import io
import json
import sys
import unittest
import subprocess
import time
import requests
from contextlib import redirect_stdout
from dotenv import load_dotenv
import os

class TestSageServerAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """启动后端服务器"""
        cls.server_process = subprocess.Popen(
            ["python", "main.py", "--host", "127.0.0.1", "--port", "8080", "--log-level", "debug"],
            cwd="sage_frontend/sage_server",
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        time.sleep(8)  # 等待服务器启动
        cls.base_url = "http://127.0.0.1:8080"  # 根据实际服务器地址调整

    @classmethod
    def tearDownClass(cls):
        """关闭后端服务器"""
        cls.server_process.terminate()
        cls.server_process.wait()

    def test_signal_api(self):
        """测试 /start/{jobId} 接口"""
        job_id = "c0755891-5744-49a1-9ca7-372cb32c5eee"
        try:
            #  确保服务器已启动
            time1 = time.time()


            response = requests.post(f"{self.base_url}/api/signal/start/{job_id}", json={})


            self.assertEqual(response.status_code, 200, "API请求失败")
            self.assertEqual(response.json().get('status'), 'success', "API返回结果不正确")
            duration = response.json().get('duration')
            assert duration is not None, "API返回结果中缺少duration字段"
            assert isinstance(duration, (int, float)), "duration字段类型不正确"
            time.sleep(1)  # 等待1秒钟，确保服务器处理完请求
            time2 = time.time()
            duration2 =str(int(duration + time2 - time1))+'s'
            # response2 = requests.post(f"{self.base_url}/api/signal/stop/{job_id}/{duration}s", json={})
            response2 = requests.post(f"{self.base_url}/api/signal/stop/{job_id}/{duration2}", json={})
            self.assertEqual(response2.status_code, 200, "API请求失败")
            with open(f"sage_frontend/sage_server/data/jobinfo/{job_id}.json", "r") as jobinfo:
                jobinfo_content = json.load(jobinfo)
            file_duration = jobinfo_content['duration']
            assert file_duration == duration2, "文件中的duration与API返回的duration不一致"

        except Exception as e:
            self.fail(f"测试过程中发生异常: {e}")




if __name__ == "__main__":
    unittest.main()