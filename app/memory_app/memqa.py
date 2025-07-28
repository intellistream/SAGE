import torch
import time

print("PyTorch 版本:", torch.__version__)

# 检查 CUDA 是否可用
if torch.cuda.is_available():
    print("CUDA is available. GPU数量:", torch.cuda.device_count())
    print("当前GPU:", torch.cuda.get_device_name(0))

    # 做个简单的矩阵运算测性能
    x = torch.randn(10000, 10000, device="cuda")
    y = torch.randn(10000, 10000, device="cuda")
    torch.cuda.synchronize()
    start = time.time()
    z = torch.mm(x, y)
    torch.cuda.synchronize()
    print("10000x10000矩阵乘法耗时: {:.3f} 秒".format(time.time() - start))
else:
    print("CUDA 不可用，当前只用CPU")


# log 配置# TODO: 增加一个log功能，讲locomo数据集的情况打印出来（log请保存到sage_example同级目录data/output/locomo/memprompt下）
# Issue URL: https://github.com/intellistream/SAGE/issues/303
# 以下是具体要求，要输出sample_id数量（表明一共有多少个大任务）
# 每个sample_id下有多少个QA以及其对应5个种类问题的统计数目（即category的统计），多少个session
# 输出格式请美观一点，终端和log文件都需要有这些内容

    # def iter_qa(self, sample_id):
    #     """迭代指定 sample_id 下所有 qa，自动兼容 answer/adversarial_answer 字段
    #     Iterate all qa in given sample_id, normalize answer/adversarial_answer to 'answer' field
    #     """
    #     sample = self.get_sample(sample_id)
    #     for qa in sample.get('qa', []):
    #         answer = qa.get('answer', qa.get('adversarial_answer', None))
    #         yield {
    #             'question': qa.get('question'),
    #             'answer': answer,
    #             'evidence': qa.get('evidence'),
    #             'category': qa.get('category')
    #         }
# if __name__ == "__main__":
#     loader = LocomoDataLoader()

#     print("所有 sample_id:")
#     print(loader.get_sample_id())

#     sid = loader.get_sample_id()[0]
    
#     print(f"\nsample_id={sid} 下的两个 speaker:")
#     print(loader.get_speaker(sid))
    
#     print(f"\n遍历 sample_id={sid} 下所有 QA:")
#     for qa in loader.iter_qa(sid):
#         print(qa)

#     print(f"\n遍历 sample_id={sid} 下所有 session:")
#     for session in loader.iter_session(sid):
#         print(f"Session {session['session_id']} | 时间: {session['date_time']} | 条数: {len(session['session_content'])}")
#         # 打印前2条session_content做示例
#         for i, entry in enumerate(session['session_content'][:2]):
#             print(f"  [{i}] speaker: {entry.get('speaker')}, text: {entry.get('text')}, session_type: {entry.get('session_type')}")
#         if len(session['session_content']) > 2:
#             print("  ...")