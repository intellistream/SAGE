# import os

# def get_default_data_dir():
#     this_file = os.path.abspath(__file__)
#     cur_dir = os.path.dirname(this_file)
#     # 一直向上，直到找到 sage.service.memory. 目录
#     while True:
#         if os.path.basename(cur_dir) == "sage":
#             project_root = os.path.dirname(cur_dir)
#             data_dir = os.path.join(project_root, "data", "neuromem_data")
#             os.makedirs(data_dir, exist_ok=True)
#             return data_dir
#         parent = os.path.dirname(cur_dir)
#         if parent == cur_dir:
#             raise FileNotFoundError("Could not find 'sage' directory in parent folders.")
#         cur_dir = parent
        
import os

def get_default_data_dir():
    # 获取当前执行程序的工作目录
    cur_dir = os.getcwd()
    data_dir = os.path.join(cur_dir, "data", "neuromem_data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir
