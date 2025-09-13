# 注入数据并建立一个全局索引以供 RAG 使用
from sage.middleware.components.neuromem import NeuroMemVDB

if __name__ == "__main__":
    # 创建NeuroMemVDB实例（用于载入数据）
    vdb = NeuroMemVDB()

    # 创建一个collection
    vdb.register_collection("demo_collection")

    # 插入数据（50条示例）
    dataset = [
        ("Python是一种流行的编程语言", {"type": "tech", "priority": "high"}),
        ("Java常用于企业级应用开发", {"type": "tech", "priority": "medium"}),
        ("C语言是操作系统开发的基础", {"type": "tech", "priority": "high"}),
        ("Go语言适合并发编程", {"type": "tech", "priority": "low"}),
        ("机器学习是人工智能的重要分支", {"type": "ai", "priority": "high"}),
        ("深度学习常用于图像识别和自然语言处理", {"type": "ai", "priority": "high"}),
        ("强化学习应用在自动驾驶和游戏AI中", {"type": "ai", "priority": "medium"}),
        ("向量数据库用于存储和检索高维向量", {"type": "db", "priority": "high"}),
        ("传统关系数据库使用SQL进行查询", {"type": "db", "priority": "medium"}),
        ("NoSQL数据库适合处理非结构化数据", {"type": "db", "priority": "low"}),
        (
            "自然语言处理涉及分词、命名实体识别等任务",
            {"type": "nlp", "priority": "high"},
        ),
        ("文本分类可以应用在垃圾邮件检测中", {"type": "nlp", "priority": "medium"}),
        ("情感分析帮助理解用户态度", {"type": "nlp", "priority": "medium"}),
        ("知识图谱用于语义搜索和推荐系统", {"type": "nlp", "priority": "low"}),
        ("数学是人工智能的基础", {"type": "edu", "priority": "high"}),
        ("概率论在机器学习中广泛应用", {"type": "edu", "priority": "medium"}),
        ("线性代数是深度学习的核心数学工具", {"type": "edu", "priority": "high"}),
        ("微积分帮助理解梯度下降算法", {"type": "edu", "priority": "medium"}),
        ("大数据技术推动了人工智能的发展", {"type": "tech", "priority": "high"}),
        ("云计算提供可扩展的算力资源", {"type": "tech", "priority": "medium"}),
        ("边缘计算适用于低延迟场景", {"type": "tech", "priority": "low"}),
        ("推荐系统常用于电商平台", {"type": "app", "priority": "high"}),
        ("搜索引擎依赖于信息检索算法", {"type": "app", "priority": "high"}),
        ("语音识别用于智能助手", {"type": "app", "priority": "medium"}),
        ("图像识别应用于安防监控", {"type": "app", "priority": "medium"}),
        ("时间序列预测在金融领域有应用", {"type": "app", "priority": "medium"}),
        ("大语言模型可以生成自然文本", {"type": "ai", "priority": "high"}),
        ("ChatGPT是基于大语言模型的应用", {"type": "ai", "priority": "high"}),
        ("人脸识别涉及计算机视觉技术", {"type": "ai", "priority": "medium"}),
        ("自动驾驶汽车依赖多传感器融合", {"type": "ai", "priority": "medium"}),
        ("数据清洗是机器学习前的重要步骤", {"type": "data", "priority": "high"}),
        ("特征工程能提升模型性能", {"type": "data", "priority": "medium"}),
        ("数据可视化帮助分析结果", {"type": "data", "priority": "low"}),
        ("分布式计算提高大规模数据处理效率", {"type": "tech", "priority": "medium"}),
        ("MapReduce是大数据处理的重要框架", {"type": "tech", "priority": "medium"}),
        ("Spark支持内存计算以提升速度", {"type": "tech", "priority": "high"}),
        ("Kafka常用于实时数据流处理", {"type": "tech", "priority": "medium"}),
        ("区块链是一种去中心化的分布式账本", {"type": "tech", "priority": "medium"}),
        ("智能合约基于区块链执行", {"type": "tech", "priority": "low"}),
        ("量子计算可能颠覆现有计算模式", {"type": "tech", "priority": "medium"}),
        ("人工智能可能引发伦理争议", {"type": "society", "priority": "low"}),
        ("虚拟现实提供沉浸式体验", {"type": "app", "priority": "medium"}),
        ("增强现实用于教育和培训", {"type": "app", "priority": "medium"}),
        ("5G网络提升了移动设备的带宽和低延迟", {"type": "tech", "priority": "high"}),
        ("物联网连接各种智能设备", {"type": "tech", "priority": "high"}),
        ("智能家居基于物联网技术", {"type": "app", "priority": "medium"}),
        ("医疗AI帮助医生诊断疾病", {"type": "app", "priority": "high"}),
        ("金融风控依赖机器学习算法", {"type": "app", "priority": "medium"}),
        ("供应链优化借助大数据分析", {"type": "app", "priority": "low"}),
        ("教育推荐系统个性化学习路径", {"type": "edu", "priority": "medium"}),
    ]

    for text, meta in dataset:
        vdb.insert(text, meta)

    # 创建索引（默认是全局索引）
    vdb.build_index()

    # 检索数据-测试会直接输出全部内容
    vdb.retrieve("人工智能应用", topk=5)
    vdb.retrieve("数据库技术", topk=5)
    vdb.retrieve("教育相关", topk=5)

    # 保存到磁盘 ！！！最重要的一步，否则无法调用
    vdb.store_to_disk()
