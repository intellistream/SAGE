# isage-privacy Copilot Instructions

## Package Identity

| 属性          | 值                                              |
| ------------- | ----------------------------------------------- |
| **PyPI 包名** | `isage-privacy`                                 |
| **导入名**    | `sage_libs.sage_privacy`                        |
| **SAGE 层级** | L3 (Algorithms & Libraries)                     |
| **版本格式**  | `0.1.x.y` (四段式)                              |
| **仓库**      | `https://github.com/intellistream/sage-privacy` |

## 层级定位

### ✅ 允许的依赖

```
L3 及以下:
├── sage-common (L1)      # 基础工具、类型、配置
├── sage-platform (L2)    # 平台服务抽象
├── Python stdlib         # 标准库
├── numpy, scipy          # 科学计算
├── torch                 # PyTorch (模型操作)
├── cryptography          # 加密库
└── opacus                # 差分隐私 (可选)
```

### ❌ 禁止的依赖

```
L4+ 组件 (绝对禁止):
├── sage-middleware       # ❌ 中间件层
├── isage-vdb / SageVDB   # ❌ 向量数据库
├── isage-neuromem        # ❌ 内存系统
├── FastAPI / uvicorn     # ❌ 网络服务
├── Redis / RocksDB       # ❌ 外部存储
└── vLLM / LMDeploy       # ❌ 推理引擎
```

**原则**: Privacy 库提供隐私保护算法，不涉及数据存储或网络通信。

## 与 SAGE 主仓库的关系

```
┌─────────────────────────────────────────────────────────────────┐
│                 SAGE 主仓库 (sage.libs.privacy)                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Interface Layer                         │  │
│  │  • BaseUnlearner (ABC)         • BasePrivacyMechanism (ABC)│  │
│  │  • BaseDPOptimizer (ABC)       • BaseFederatedClient (ABC) │  │
│  │  • BaseFederatedServer (ABC)                               │  │
│  │  • UnlearningMethod, PrivacyLevel (枚举)                   │  │
│  │  • PrivacyBudget, UnlearningResult (数据类型)              │  │
│  │  • create_unlearner(), create_mechanism() (工厂函数)       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ▲                                   │
│                              │ 注册                              │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────┐
│                  isage-privacy (独立 PyPI 包)                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                 Implementation Layer                       │  │
│  │  Machine Unlearning:                                       │  │
│  │  • SISAUnlearner, GradientAscentUnlearner                  │  │
│  │  • FisherUnlearner, AmnesiacUnlearner                      │  │
│  │  Differential Privacy:                                     │  │
│  │  • LaplaceMechanism, GaussianMechanism                     │  │
│  │  • DPSGDOptimizer, PATEOptimizer                           │  │
│  │  Federated Learning:                                       │  │
│  │  • FedAvgClient, FedProxClient                             │  │
│  │  • FedAvgServer, SecureAggregator                          │  │
│  │  PII Detection:                                            │  │
│  │  • PIIDetector, PIIAnonymizer                              │  │
│  │  • _register.py (自动注册到 SAGE 工厂)                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 自动注册机制

```python
# sage_libs/sage_privacy/_register.py
from sage.libs.privacy import (
    register_unlearner, register_mechanism,
    register_dp_optimizer, register_federated_client
)

from .unlearning import SISAUnlearner, GradientAscentUnlearner, FisherUnlearner
from .dp import LaplaceMechanism, GaussianMechanism, DPSGDOptimizer
from .federated import FedAvgClient, FedAvgServer

# 注册 Unlearners
register_unlearner("sisa", SISAUnlearner)
register_unlearner("gradient_ascent", GradientAscentUnlearner)
register_unlearner("fisher", FisherUnlearner)

# 注册 DP Mechanisms
register_mechanism("laplace", LaplaceMechanism)
register_mechanism("gaussian", GaussianMechanism)

# 注册 DP Optimizers
register_dp_optimizer("dp_sgd", DPSGDOptimizer)
```

## 功能模块

### 1. Machine Unlearning (机器遗忘)

```python
from sage.libs.privacy import create_unlearner, UnlearningResult

# SISA (Sharded, Isolated, Sliced, Aggregated)
unlearner = create_unlearner("sisa",
    num_shards=5,
    num_slices=10
)
result: UnlearningResult = unlearner.unlearn(
    model=trained_model,
    forget_data=data_to_forget,
    retain_data=remaining_data
)
print(f"遗忘成功: {result.success}")
print(f"遗忘样本数: {result.samples_forgotten}")

# Gradient Ascent (梯度上升)
unlearner = create_unlearner("gradient_ascent",
    learning_rate=0.01,
    num_steps=100
)

# Fisher Forgetting (Fisher 信息遗忘)
unlearner = create_unlearner("fisher",
    damping=0.1
)

# 验证遗忘效果
score = unlearner.verify_unlearning(
    model=unlearned_model,
    forget_data=data_to_forget,
    original_model=original_model
)
print(f"遗忘验证分数: {score:.4f}")  # 1.0 = 完美遗忘
```

**支持的遗忘方法**:

| 方法              | 类型     | 特点                 |
| ----------------- | -------- | -------------------- |
| `sisa`            | 精确遗忘 | 分片训练，高效删除   |
| `gradient_ascent` | 近似遗忘 | 简单快速，可能不完全 |
| `fisher`          | 近似遗忘 | 基于 Fisher 信息     |
| `amnesiac`        | 近似遗忘 | 缓存更新，快速回滚   |
| `influence`       | 近似遗忘 | 影响函数方法         |

### 2. Differential Privacy (差分隐私)

```python
from sage.libs.privacy import create_mechanism, PrivacyBudget

# 创建隐私预算
budget = PrivacyBudget(
    epsilon=1.0,       # 隐私损失参数
    delta=1e-5,        # 失败概率
    composition="rdp"  # 组合方法
)

# Laplace 机制
mechanism = create_mechanism("laplace", sensitivity=1.0)
noisy_value = mechanism.add_noise(original_value, budget)

# Gaussian 机制
mechanism = create_mechanism("gaussian", sensitivity=1.0)
noisy_vector = mechanism.add_noise(original_vector, budget)

# 查询隐私级别
print(budget.level)  # PrivacyLevel.HIGH (epsilon=1.0)
```

### 3. DP Optimizer (差分隐私优化器)

```python
from sage.libs.privacy import create_dp_optimizer, PrivacyBudget

# DP-SGD 优化器
optimizer = create_dp_optimizer("dp_sgd",
    learning_rate=0.01,
    max_grad_norm=1.0,
    noise_multiplier=1.1
)

# 训练循环
for batch in dataloader:
    loss = model(batch)
    gradients = compute_gradients(loss)

    # 带隐私保证的参数更新
    params = optimizer.step(
        params=model.parameters(),
        gradients=gradients,
        privacy_budget=budget
    )

# 获取已消耗的隐私预算
spent = optimizer.get_privacy_spent()
print(f"已消耗隐私预算: ε={spent.epsilon:.2f}")
```

### 4. Federated Learning (联邦学习)

```python
from sage.libs.privacy import create_federated_client, create_federated_server

# 创建联邦服务器
server = create_federated_server("fedavg",
    num_clients=10,
    rounds=100
)

# 创建联邦客户端
client = create_federated_client("fedavg",
    local_epochs=5,
    learning_rate=0.01
)

# 客户端本地训练
local_model = client.train(
    global_model=global_params,
    local_data=client_data
)

# 服务器聚合
aggregated = server.aggregate(
    client_updates=[client1_update, client2_update, ...]
)

# FedProx (带近端项)
client = create_federated_client("fedprox",
    mu=0.01  # 近端项系数
)
```

### 5. PII Detection & Anonymization (PII 检测与匿名化)

```python
from sage.libs.privacy import PIIDetector, PIIAnonymizer

# PII 检测
detector = PIIDetector(
    entity_types=["PERSON", "EMAIL", "PHONE", "SSN", "CREDIT_CARD"]
)
entities = detector.detect("联系张三，电话：13812345678")
# [PIIEntity(type="PERSON", text="张三", start=2, end=4),
#  PIIEntity(type="PHONE", text="13812345678", start=8, end=19)]

# PII 匿名化
anonymizer = PIIAnonymizer(
    strategies={
        "PERSON": "mask",     # [PERSON]
        "EMAIL": "hash",      # a1b2c3@hash.com
        "PHONE": "redact",    # [REDACTED]
    }
)
anonymized = anonymizer.anonymize("联系张三，电话：13812345678")
# "联系[PERSON]，电话：[REDACTED]"
```

## 目录结构

```
sage-privacy/                       # 独立仓库根目录
├── pyproject.toml                  # 包配置 (name = "isage-privacy")
├── README.md
├── COPILOT_INSTRUCTIONS.md         # 本文件
├── LICENSE
├── src/
│   └── sage_libs/                  # 命名空间包
│       └── sage_privacy/
│           ├── __init__.py         # 主入口
│           ├── _version.py         # 版本信息
│           ├── _register.py        # 自动注册
│           ├── unlearning/         # 机器遗忘实现
│           │   ├── __init__.py
│           │   ├── sisa.py         # SISA 遗忘
│           │   ├── gradient_ascent.py
│           │   ├── fisher.py       # Fisher 遗忘
│           │   ├── amnesiac.py
│           │   └── influence.py    # 影响函数
│           ├── dp/                 # 差分隐私实现
│           │   ├── __init__.py
│           │   ├── mechanisms.py   # Laplace, Gaussian
│           │   ├── optimizers.py   # DP-SGD, PATE
│           │   └── accountant.py   # 隐私预算记账
│           ├── federated/          # 联邦学习实现
│           │   ├── __init__.py
│           │   ├── client.py       # FedAvg, FedProx 客户端
│           │   ├── server.py       # 聚合服务器
│           │   └── secure_agg.py   # 安全聚合
│           └── pii/                # PII 检测实现
│               ├── __init__.py
│               ├── detector.py
│               └── anonymizer.py
├── tests/
│   ├── conftest.py
│   ├── test_unlearning.py
│   ├── test_dp.py
│   ├── test_federated.py
│   └── test_pii.py
└── examples/
    ├── machine_unlearning.py
    ├── dp_training.py
    └── federated_learning.py
```

## 常见问题修复指南

### 1. 隐私预算耗尽

```python
# ❌ 问题：隐私预算超支
for _ in range(1000):
    mechanism.add_noise(value, budget)  # 无限制查询

# ✅ 修复：使用预算记账
from sage_libs.sage_privacy import PrivacyAccountant

accountant = PrivacyAccountant(total_epsilon=10.0, total_delta=1e-5)

for query in queries:
    if not accountant.can_spend(query_epsilon=0.1):
        raise PrivacyBudgetExhausted("隐私预算已耗尽")
    result = mechanism.add_noise(value, query_budget)
    accountant.spend(query_epsilon=0.1)
```

### 2. SISA 分片配置

```python
# ❌ 问题：分片数过少导致遗忘慢
unlearner = create_unlearner("sisa", num_shards=2)  # 重训练 50% 数据

# ✅ 修复：根据数据量调整分片
num_samples = len(dataset)
# 每个分片约 1000-5000 样本
num_shards = max(5, num_samples // 2000)
unlearner = create_unlearner("sisa", num_shards=num_shards)
```

### 3. 梯度裁剪

```python
# ❌ 问题：DP-SGD 忘记裁剪梯度
optimizer = create_dp_optimizer("dp_sgd", max_grad_norm=None)

# ✅ 修复：必须设置最大梯度范数
optimizer = create_dp_optimizer("dp_sgd",
    max_grad_norm=1.0,  # 必须设置
    noise_multiplier=1.1
)
```

### 4. 联邦学习通信

```python
# ❌ 错误：在 L3 库中实现网络通信
class FedAvgClient:
    def send_update(self, url: str):  # ❌ 网络调用
        requests.post(url, data=self.update)

# ✅ 正确：只返回更新，通信在 L4 层
class FedAvgClient:
    def get_update(self) -> dict:  # ✅ 纯数据返回
        return self.local_update

# L4 middleware 层处理通信
from sage.middleware.operators import FederatedOperator
operator = FederatedOperator(client=client, server_url="...")
```

### 5. PII 检测模型加载

```python
# ❌ 问题：每次调用都加载模型
def process_text(text):
    detector = PIIDetector()  # 每次都重新加载模型
    return detector.detect(text)

# ✅ 修复：复用检测器实例
detector = PIIDetector()  # 初始化一次

def process_text(text):
    return detector.detect(text)
```

## 关键设计原则

### 1. 隐私预算追踪

所有隐私操作必须追踪预算消耗：

```python
class DPMechanism:
    def add_noise(self, value: float, budget: PrivacyBudget) -> float:
        # 记录此次查询的隐私消耗
        self._consumed_epsilon += self._compute_epsilon(budget)
        return value + self._sample_noise(budget)

    @property
    def privacy_spent(self) -> PrivacyBudget:
        return PrivacyBudget(epsilon=self._consumed_epsilon)
```

### 2. 可验证性

遗忘效果必须可验证：

```python
class BaseUnlearner:
    @abstractmethod
    def unlearn(self, model, forget_data, **kwargs) -> UnlearningResult:
        pass

    def verify_unlearning(self, model, forget_data, **kwargs) -> float:
        """验证遗忘效果 (0-1，1 = 完美遗忘)"""
        # 使用成员推理攻击等方法验证
        ...
```

### 3. 无网络通信

联邦学习只实现算法，不实现通信：

```python
# ✅ 正确：纯算法
class FedAvgServer:
    def aggregate(self, updates: list[dict]) -> dict:
        """聚合客户端更新"""
        return weighted_average(updates)

# ❌ 错误：包含通信
class FedAvgServer:
    def run_round(self):
        updates = self._collect_from_clients()  # ❌ 网络调用
        return self.aggregate(updates)
```

### 4. 敏感度计算

DP 机制需要明确敏感度：

```python
# ✅ 好：显式敏感度参数
mechanism = LaplaceMechanism(sensitivity=1.0)

# ✅ 好：自动计算敏感度
mechanism = LaplaceMechanism.for_query(
    query_type="count",
    max_records=1000
)

# ❌ 差：隐式敏感度
mechanism = LaplaceMechanism()  # 敏感度是什么？
```

### 5. 类型安全

隐私预算使用专用类型：

```python
# ✅ 好：使用专用类型
def train_with_dp(budget: PrivacyBudget) -> Model:
    if budget.epsilon > 10:
        warnings.warn("隐私保证较弱")
    ...

# ❌ 差：使用原始类型
def train_with_dp(epsilon: float, delta: float) -> Model:
    ...  # 容易混淆参数
```

## 测试规范

```bash
# 运行单元测试
pytest tests/ -v

# 运行隐私验证测试
pytest tests/test_unlearning.py -v -k "verify"

# 检查 DP 保证
pytest tests/test_dp.py -v --run-privacy-audit
```

## 隐私级别参考

| 级别        | Epsilon 范围 | 应用场景                   |
| ----------- | ------------ | -------------------------- |
| `VERY_HIGH` | ≤ 0.1        | 高度敏感数据（医疗、金融） |
| `HIGH`      | 0.1 - 1.0    | 敏感数据（个人信息）       |
| `MEDIUM`    | 1.0 - 10.0   | 一般数据（统计分析）       |
| `LOW`       | > 10.0       | 低敏感数据（聚合统计）     |

## 发布流程

```bash
# 使用 sage-pypi-publisher
cd /path/to/sage-pypi-publisher
./publish.sh sage-privacy --auto-bump patch

# 或手动指定版本
./publish.sh sage-privacy --version 0.1.0.1
```
