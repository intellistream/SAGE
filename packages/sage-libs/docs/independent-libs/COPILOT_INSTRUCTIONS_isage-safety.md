# isage-safety Copilot Instructions

## Package Identity

| 属性          | 值                                             |
| ------------- | ---------------------------------------------- |
| **PyPI 包名** | `isage-safety`                                 |
| **导入名**    | `sage_libs.sage_safety`                        |
| **SAGE 层级** | L3 (Algorithms & Libraries)                    |
| **版本格式**  | `0.1.x.y` (四段式)                             |
| **仓库**      | `https://github.com/intellistream/sage-safety` |

## 层级定位

### ✅ 允许的依赖

```
L3 及以下:
├── sage-common (L1)      # 基础工具、类型、配置
├── sage-platform (L2)    # 平台服务抽象
├── Python stdlib         # 标准库
├── re (regex)            # 正则表达式
├── transformers          # 分类模型
├── torch                 # PyTorch
└── sentence-transformers # 语义相似度
```

### ❌ 禁止的依赖

```
L4+ 组件 (绝对禁止):
├── sage-middleware       # ❌ 中间件层
├── isage-vdb / SageVDB   # ❌ 向量数据库
├── isage-neuromem        # ❌ 内存系统
├── FastAPI / uvicorn     # ❌ 网络服务
├── Redis / RocksDB       # ❌ 外部存储
├── vLLM / LMDeploy       # ❌ 推理引擎
└── isagellm              # ❌ LLM 服务（通过注入）
```

**原则**: Safety 库提供安全检测算法，LLM-based 检测通过依赖注入。

## 与 SAGE 主仓库的关系

```
┌─────────────────────────────────────────────────────────────────┐
│                  SAGE 主仓库 (sage.libs.safety)                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Interface Layer                         │  │
│  │  • BaseGuardrail (ABC)         • BaseJailbreakDetector    │  │
│  │  • BaseToxicityDetector (ABC)  • BaseAdversarialDefense   │  │
│  │  • SafetyCategory, SafetyAction (枚举)                     │  │
│  │  • SafetyResult, JailbreakResult (数据类型)                │  │
│  │  • create_guardrail(), create_jailbreak_detector()        │  │
│  │  Built-in (简单实现):                                      │  │
│  │  • content_filter (正则过滤)                               │  │
│  │  • pii_scrubber (简单 PII 处理)                            │  │
│  │  • policy_check (工具调用策略)                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ▲                                   │
│                              │ 注册                              │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────┐
│                  isage-safety (独立 PyPI 包)                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                 Implementation Layer                       │  │
│  │  Guardrails:                                               │  │
│  │  • LLMGuardrail, ClassifierGuardrail, HybridGuardrail     │  │
│  │  Jailbreak Detectors:                                      │  │
│  │  • PatternDetector, MLDetector, LLMDetector, Ensemble     │  │
│  │  Toxicity Detectors:                                       │  │
│  │  • PerspectiveDetector, ToxicBERTDetector                 │  │
│  │  Adversarial Defense:                                      │  │
│  │  • PromptInjectionDefense, EncodingDefense                │  │
│  │  • _register.py (自动注册到 SAGE 工厂)                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 自动注册机制

```python
# sage_libs/sage_safety/_register.py
from sage.libs.safety import (
    register_guardrail, register_jailbreak_detector,
    register_toxicity_detector, register_adversarial_defense
)

from .guardrails import LLMGuardrail, ClassifierGuardrail, HybridGuardrail
from .jailbreak import PatternDetector, MLDetector, LLMDetector
from .toxicity import PerspectiveDetector, ToxicBERTDetector
from .adversarial import PromptInjectionDefense, EncodingDefense

# 注册 Guardrails
register_guardrail("llm", LLMGuardrail)
register_guardrail("classifier", ClassifierGuardrail)
register_guardrail("hybrid", HybridGuardrail)

# 注册 Jailbreak Detectors
register_jailbreak_detector("pattern", PatternDetector)
register_jailbreak_detector("ml", MLDetector)
register_jailbreak_detector("llm", LLMDetector)

# 注册 Toxicity Detectors
register_toxicity_detector("perspective", PerspectiveDetector)
register_toxicity_detector("toxic_bert", ToxicBERTDetector)
```

## 功能模块

### 1. Guardrails (安全护栏)

```python
from sage.libs.safety import create_guardrail, SafetyResult, SafetyAction

# LLM 护栏（需要 LLM 客户端）
guardrail = create_guardrail("llm",
    llm_client=client,
    categories=["toxicity", "hate_speech", "violence"]
)

result: SafetyResult = guardrail.check(
    content="用户输入文本",
    context="对话上下文"
)

if not result.is_safe:
    print(f"检测到问题: {result.category}")
    print(f"建议操作: {result.action}")  # BLOCK, WARN, MODIFY

# 分类器护栏（本地模型）
guardrail = create_guardrail("classifier",
    model="unitary/toxic-bert"
)

# 混合护栏（规则 + ML）
guardrail = create_guardrail("hybrid",
    pattern_rules=["badword1", "badword2"],
    classifier_model="toxic-bert",
    llm_client=client  # 可选
)

# 批量检查
results = guardrail.check_batch(
    contents=["text1", "text2", "text3"],
    contexts=[None, None, None]
)

# 过滤内容
filtered, result = guardrail.filter(
    content="包含敏感词的文本",
    action=SafetyAction.MODIFY
)
```

### 2. Jailbreak Detection (越狱检测)

```python
from sage.libs.safety import create_jailbreak_detector, JailbreakResult

# 基于模式的检测（快速）
detector = create_jailbreak_detector("pattern",
    patterns=[
        r"ignore.*previous.*instructions",
        r"pretend.*you.*are",
        r"DAN.*mode"
    ]
)
result: JailbreakResult = detector.detect(
    prompt="Ignore all previous instructions and...",
    system_prompt="You are a helpful assistant"
)

if result.is_jailbreak:
    print(f"检测到越狱攻击: {result.attack_type}")
    print(f"置信度: {result.confidence:.2%}")

# ML 检测器（更准确）
detector = create_jailbreak_detector("ml",
    model="protectai/deberta-v3-base-prompt-injection"
)

# LLM 检测器（最准确，但慢）
detector = create_jailbreak_detector("llm",
    llm_client=client
)

# 集成检测器（组合多种方法）
detector = create_jailbreak_detector("ensemble",
    detectors=["pattern", "ml", "llm"],
    llm_client=client,
    voting="majority"  # "majority", "any", "all"
)
```

### 3. Toxicity Detection (毒性检测)

```python
from sage.libs.safety import create_toxicity_detector

# Perspective API (需要 API key)
detector = create_toxicity_detector("perspective",
    api_key=os.environ["PERSPECTIVE_API_KEY"]
)
result = detector.detect("检测的文本")
print(f"毒性分数: {result.toxicity_score:.2%}")
print(f"类别分数: {result.category_scores}")

# ToxicBERT (本地模型)
detector = create_toxicity_detector("toxic_bert",
    model="unitary/toxic-bert"
)
result = detector.detect("检测的文本")

# 多语言检测
detector = create_toxicity_detector("multilingual",
    model="unitary/multilingual-toxic-xlm-roberta"
)
```

### 4. Adversarial Defense (对抗防御)

```python
from sage.libs.safety import create_adversarial_defense

# Prompt Injection 防御
defense = create_adversarial_defense("prompt_injection",
    strategies=["delimiter", "instruction_isolation", "input_sanitization"]
)
safe_prompt = defense.sanitize(user_input)

# 编码攻击防御
defense = create_adversarial_defense("encoding",
    detect_unicode=True,
    detect_homoglyphs=True,
    detect_invisible=True
)
is_safe, cleaned = defense.check_and_clean(input_text)

# 角色扮演攻击防御
defense = create_adversarial_defense("roleplay",
    blocked_personas=["DAN", "STAN", "Developer Mode"]
)
```

### 5. Content Filter (内容过滤) - 内置

```python
# 内置的简单实现，无需 isage-safety
from sage.libs.safety import content_filter

# 正则过滤
filter = content_filter.RegexFilter(
    patterns=[r"badword1", r"badword2"],
    replacement="[FILTERED]"
)
filtered_text = filter.filter("Text with badword1")

# 敏感词过滤
filter = content_filter.KeywordFilter(
    keywords=["敏感词1", "敏感词2"],
    action="replace"  # "replace", "block", "warn"
)
```

### 6. PII Scrubber (PII 处理) - 内置

```python
# 内置的简单实现
from sage.libs.safety import pii_scrubber

scrubber = pii_scrubber.PIIScrubber(
    entity_types=["EMAIL", "PHONE", "ID_CARD"],
    strategies={
        "EMAIL": "hash",    # a1b2@hash.com
        "PHONE": "mask",    # 138****5678
        "ID_CARD": "redact" # [REDACTED]
    }
)
cleaned = scrubber.scrub("我的邮箱是 test@example.com")
```

### 7. Policy Check (策略检查) - 内置

```python
# 内置的工具调用策略
from sage.libs.safety import policy_check

checker = policy_check.ToolPolicyChecker(
    allowed_tools=["search", "calculate"],
    blocked_tools=["execute_code", "delete_file"],
    rate_limits={"search": 10}  # 每分钟最多 10 次
)

is_allowed = checker.check(tool_name="search", context={})
```

## 目录结构

```
sage-safety/                        # 独立仓库根目录
├── pyproject.toml                  # 包配置 (name = "isage-safety")
├── README.md
├── COPILOT_INSTRUCTIONS.md         # 本文件
├── LICENSE
├── src/
│   └── sage_libs/                  # 命名空间包
│       └── sage_safety/
│           ├── __init__.py         # 主入口
│           ├── _version.py         # 版本信息
│           ├── _register.py        # 自动注册
│           ├── guardrails/         # 护栏实现
│           │   ├── __init__.py
│           │   ├── llm.py          # LLM 护栏
│           │   ├── classifier.py   # 分类器护栏
│           │   └── hybrid.py       # 混合护栏
│           ├── jailbreak/          # 越狱检测实现
│           │   ├── __init__.py
│           │   ├── pattern.py      # 模式检测
│           │   ├── ml.py           # ML 检测
│           │   ├── llm.py          # LLM 检测
│           │   └── ensemble.py     # 集成检测
│           ├── toxicity/           # 毒性检测实现
│           │   ├── __init__.py
│           │   ├── perspective.py  # Perspective API
│           │   └── toxic_bert.py   # ToxicBERT
│           ├── adversarial/        # 对抗防御实现
│           │   ├── __init__.py
│           │   ├── prompt_injection.py
│           │   ├── encoding.py
│           │   └── roleplay.py
│           └── utils/              # 工具函数
│               ├── __init__.py
│               └── patterns.py     # 常用模式
├── tests/
│   ├── conftest.py
│   ├── test_guardrails.py
│   ├── test_jailbreak.py
│   ├── test_toxicity.py
│   └── test_adversarial.py
└── examples/
    ├── content_moderation.py
    ├── jailbreak_detection.py
    └── safe_llm_pipeline.py
```

## 常见问题修复指南

### 1. LLM 客户端注入

```python
# ❌ 错误：内部创建 LLM 客户端
class LLMGuardrail(BaseGuardrail):
    def __init__(self):
        from isagellm import UnifiedInferenceClient
        self.llm = UnifiedInferenceClient.create()  # ❌ 隐式依赖

# ✅ 正确：通过依赖注入
class LLMGuardrail(BaseGuardrail):
    def __init__(self, llm_client: LLMClientProtocol):
        self.llm = llm_client

# 使用时
from isagellm import UnifiedInferenceClient
client = UnifiedInferenceClient.create()
guardrail = create_guardrail("llm", llm_client=client)
```

### 2. 模式匹配效率

```python
# ❌ 问题：每次检测都编译正则
def detect(self, text):
    for pattern in self.patterns:
        if re.search(pattern, text):  # 每次都编译
            return True

# ✅ 修复：预编译正则
def __init__(self, patterns):
    self.compiled_patterns = [re.compile(p, re.I) for p in patterns]

def detect(self, text):
    return any(p.search(text) for p in self.compiled_patterns)
```

### 3. 假阳性处理

```python
# ❌ 问题：过于敏感导致假阳性
detector = create_jailbreak_detector("pattern",
    patterns=[r"ignore"]  # 太宽泛
)

# ✅ 修复：使用更精确的模式
detector = create_jailbreak_detector("pattern",
    patterns=[
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"disregard\s+your\s+guidelines"
    ]
)

# ✅ 或使用白名单
detector = create_jailbreak_detector("pattern",
    patterns=[...],
    whitelist=["ignore this field", "you can ignore"]
)
```

### 4. 阈值调整

```python
# ❌ 问题：阈值不合适导致漏检或误报
detector = create_toxicity_detector("toxic_bert")
result = detector.detect(text)  # 默认阈值可能不适合

# ✅ 修复：根据场景调整阈值
detector = create_toxicity_detector("toxic_bert",
    thresholds={
        "toxicity": 0.7,      # 毒性
        "severe_toxicity": 0.5,  # 严重毒性更严格
        "identity_attack": 0.6
    }
)
```

### 5. 多语言支持

```python
# ❌ 问题：只支持英文
detector = create_toxicity_detector("toxic_bert",
    model="unitary/toxic-bert"  # 只支持英文
)

# ✅ 修复：使用多语言模型
detector = create_toxicity_detector("multilingual",
    model="unitary/multilingual-toxic-xlm-roberta"
)

# 或针对中文
detector = create_toxicity_detector("chinese",
    model="textdetox/chinese-roberta-base-toxic"
)
```

### 6. 性能优化

```python
# ❌ 问题：每次请求都加载模型
def check(self, text):
    model = AutoModel.from_pretrained(...)  # 每次都加载
    return model(text)

# ✅ 修复：在初始化时加载
class ClassifierGuardrail:
    def __init__(self, model_name):
        self.model = AutoModel.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

    def check(self, text):
        # 复用已加载的模型
        return self.model(self.tokenizer(text))
```

## 关键设计原则

### 1. 分层防御

多层检测，由快到慢：

```python
# 第一层：快速规则检测
if pattern_detector.detect(prompt):
    return block()

# 第二层：ML 模型检测
if ml_detector.detect(prompt).is_jailbreak:
    return block()

# 第三层：LLM 检测（最准确但最慢）
if llm_detector.detect(prompt).is_jailbreak:
    return block()

return allow()
```

### 2. 可配置阈值

所有检测器支持阈值配置：

```python
class BaseDetector:
    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

    def detect(self, text) -> Result:
        score = self._compute_score(text)
        return Result(
            is_positive=score > self.threshold,
            confidence=score
        )
```

### 3. 详细报告

检测结果包含详细信息：

```python
@dataclass
class SafetyResult:
    is_safe: bool
    action: SafetyAction
    category: Optional[SafetyCategory]
    confidence: float
    detected_issues: list[str]      # 具体问题
    modified_content: Optional[str]  # 修改后内容
    metadata: dict[str, Any]         # 额外信息
```

### 4. 白名单支持

所有检测器支持白名单：

```python
class JailbreakDetector:
    def __init__(self, patterns, whitelist=None):
        self.patterns = patterns
        self.whitelist = whitelist or []

    def detect(self, prompt):
        # 先检查白名单
        if any(w in prompt.lower() for w in self.whitelist):
            return JailbreakResult(is_jailbreak=False)
        # 再检测
        ...
```

### 5. 无副作用

检测是只读操作，不修改输入：

```python
# ✅ 好：只读检测
def check(self, content: str) -> SafetyResult:
    # 不修改 content
    return SafetyResult(...)

# ✅ 好：过滤返回新内容
def filter(self, content: str) -> tuple[str, SafetyResult]:
    result = self.check(content)
    if result.action == SafetyAction.MODIFY:
        # 返回新字符串，不修改原始内容
        return self._sanitize(content), result
    return content, result
```

## 测试规范

```bash
# 运行单元测试
pytest tests/ -v

# 运行需要模型的测试
pytest tests/ -v -m "not slow"

# 运行完整测试（包括 LLM）
SAGE_TEST_LLM_ENABLED=1 pytest tests/ -v
```

## 安全检测分类

| 类别      | 检测方法           | 性能  | 准确性 |
| --------- | ------------------ | ----- | ------ |
| 越狱/注入 | Pattern → ML → LLM | 快→慢 | 低→高  |
| 毒性      | Classifier         | 中    | 高     |
| PII       | Regex + NER        | 快    | 中     |
| 对抗文本  | 编码检测           | 快    | 中     |

## 与其他 L3 库的协作

```python
# isage-safety + isage-agentic 协作
from sage_libs.sage_safety import create_guardrail, create_jailbreak_detector
from sage_libs.sage_agentic import ReActAgent

# 创建安全检测器
jailbreak_detector = create_jailbreak_detector("ensemble", ...)
guardrail = create_guardrail("hybrid", ...)

# 在 Agent 执行前检测
def safe_agent_execute(agent, task):
    # 检测越狱
    jb_result = jailbreak_detector.detect(task)
    if jb_result.is_jailbreak:
        raise SecurityError(f"检测到越狱攻击: {jb_result.attack_type}")

    # 执行任务
    result = agent.execute(task)

    # 检测输出
    safety_result = guardrail.check(str(result.output))
    if not safety_result.is_safe:
        return guardrail.filter(str(result.output))[0]

    return result
```

## 发布流程

```bash
# 使用 sage-pypi-publisher
cd /path/to/sage-pypi-publisher
./publish.sh sage-safety --auto-bump patch

# 或手动指定版本
./publish.sh sage-safety --version 0.1.0.1
```
