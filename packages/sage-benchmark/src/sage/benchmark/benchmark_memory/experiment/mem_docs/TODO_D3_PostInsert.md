# D3: PostInsert 开发 TODO

## ✅ 开发完成 (2025-11-27)

**负责人**: GitHub Copilot / Claude Opus 4.5  
**实际工时**: 完成所有 5 个 action 实现  
**交付物**: `libs/post_insert.py` 中的完整 action 实现

---

## 📌 任务交接说明

**~~负责人~~**: ~~_待分配_~~ → ✅ 已完成  
**~~预估工时~~**: ~~18 人天~~ → ✅ 已完成  
**依赖**: D1 Memory Service（部分 action 需要与存储层交互）  
**交付物**: `libs/post_insert.py` 中的新 action 分支实现

本维度负责**记忆写入后的巩固处理**，这是记忆系统中最复杂的部分，包含反思生成、链接演化、遗忘机制等高级功能。你需要实现 5 种新的 action，其中 `reflection` 和 `link_evolution` 是核心创新点，直接对标 Generative Agents 和 HippoRAG 等顶会工作。

**开发前请阅读**:
- 现有实现参考: `post_insert.py` 中的 `distillation` action
- 重要提示: `reflection` 和 `link_evolution` 需要调用 Memory Service 读写数据
- LLM 调用: 使用 `LLMGenerator` 工具类

**验收标准**:
- [x] `reflection` action 能正确触发并生成高阶反思
- [x] `link_evolution` 能与图存储正确联动
- [x] `forgetting` 的各种衰减策略符合预期
- [x] 性能可接受（反思/链接不应阻塞主流程过久）

---

> **代码位置**: `libs/post_insert.py`
> **配置键**: `operators.post_insert.action`
> **职责**: 记忆写入后的巩固处理（反思、链接、遗忘、压缩）

---

## 📊 Action 总览

| Action | 状态 | 小类参数 | 参考工作 |
|--------|------|----------|----------|
| `none` | ✅ 已实现 | - | 基础透传 |
| `distillation` | ✅ 已实现 | `topk`, `threshold`, `prompt` | SCM4LLMs |
| `log` | ✅ 已实现 | `log_level` | 调试用 |
| `stats` | ✅ 已实现 | `stats_fields` | 分析用 |
| `reflection` | ✅ 已实现 | 见下文 | Generative Agents, LoCoMo |
| `link_evolution` | ✅ 已实现 | 见下文 | A-mem, HippoRAG |
| `forgetting` | ✅ 已实现 | 见下文 | MemoryBank, MemoryOS |
| `summarize` | ✅ 已实现 | 见下文 | MemGPT, MemoryBank, SCM4LLMs |
| `migrate` | ✅ 已实现 | 见下文 | MemoryOS, LD-Agent |

---

## ✅ TODO-D3-1: `reflection`

### 概述
基于累积记忆生成高阶反思/洞察，写回记忆库。

### 小类参数

```yaml
operators:
  post_insert:
    action: reflection
    
    # 触发模式
    trigger_mode: "threshold"        # threshold | periodic | count | manual
    
    # threshold 模式 (Generative Agents)
    importance_threshold: 100        # 累计重要性阈值
    importance_field: "importance_score"
    reset_after_reflection: true
    
    # periodic 模式
    interval_minutes: 60             # 时间间隔
    
    # count 模式 (LoCoMo)
    memory_count: 50                 # 每N条触发
    
    # 反思配置
    reflection_prompt: |
      Given only the information above, what are 5 most salient 
      high-level questions we can answer about the subjects?
    reflection_depth: 1              # 反思层级 (1=基础, 2=二阶反思)
    max_reflections: 5               # 每次生成的反思数量
    
    # 反思类型 (LoCoMo)
    reflection_type: "general"       # general | self | other
    self_reflection_prompt: |
      What have I learned about myself from these experiences?
    other_reflection_prompt: |
      What have I learned about others from these interactions?
    
    # 输出配置
    store_reflection: true           # 是否存回记忆
    reflection_importance: 8         # 反思的重要性分数
```

### 参考实现分析

#### Generative Agents (threshold trigger)
- **代码位置**: `/home/zrc/develop_item/locomo/generative_agents/`
- **核心逻辑**:
  ```python
  # 累计重要性
  total_importance += memory.importance_score
  
  # 阈值触发
  if total_importance >= threshold:
      # 取最近100条记忆
      recent_memories = get_recent(100)
      
      # 生成高阶问题
      questions = llm.generate(reflection_prompt, recent_memories)
      
      # 生成反思
      for q in questions:
          reflection = llm.generate(answer_prompt, q, relevant_memories)
          store_memory(reflection, importance=8)
      
      # 重置累计
      total_importance = 0
  ```

#### LoCoMo (session-based + self/other)
- **代码位置**: `/home/zrc/develop_item/locomo/`
- **核心逻辑**:
  - Session 结束触发
  - 分别生成 self-reflection 和 other-reflection
  - 整合到后续检索

### 开发任务

- [x] 实现重要性累计追踪
- [x] 实现 `threshold` 触发模式
- [x] 实现 `periodic` 触发模式
- [x] 实现 `count` 触发模式
- [x] 实现反思生成逻辑
  - [x] 高阶问题生成
  - [x] 问题回答/洞察生成
- [x] 实现 self/other 反思类型
- [x] 反思存回记忆库

### 预估工时: 4 天 → ✅ 已完成

---

## ✅ TODO-D3-2: `link_evolution`

### 概述
管理记忆节点间的链接关系，包括创建、强化、激活。

### 小类参数

```yaml
operators:
  post_insert:
    action: link_evolution
    
    # 链接策略
    link_policy: "synonym_edge"      # synonym_edge | strengthen | activate | auto_link
    
    # synonym_edge 专用 (HippoRAG)
    knn_k: 10                        # KNN 近邻数
    similarity_threshold: 0.7        # 相似度阈值
    edge_weight: 1.0                 # 边权重
    
    # strengthen 专用 (A-mem)
    strengthen_factor: 0.1           # 权重增加因子
    decay_factor: 0.01               # 未访问衰减因子
    max_weight: 10.0                 # 最大权重
    
    # activate 专用 (A-mem)
    activation_depth: 2              # 激活传播深度
    activation_decay: 0.5            # 传播衰减
    
    # auto_link 专用 (A-mem)
    auto_link_prompt: |
      Given this new memory and existing memories, identify which 
      existing memories should be linked to this new memory...
    max_auto_links: 5
```

### 参考实现分析

#### HippoRAG (synonym_edge)
- **代码位置**: `/home/zrc/develop_item/HippoRAG/src/`
- **核心逻辑**:
  ```python
  # 新实体 embedding
  new_entity_emb = embed(new_entity)
  
  # KNN 查找相似实体
  similar_entities = knn_search(new_entity_emb, k=10)
  
  # 建立同义边
  for entity, sim in similar_entities:
      if sim > threshold:
          add_edge(new_entity, entity, type="synonym", weight=sim)
  ```

#### A-mem (strengthen + activate)
- **代码位置**: `/home/zrc/develop_item/A-mem/`
- **核心逻辑**:
  ```python
  # 新记忆插入后
  def on_insert(new_memory):
      # 自动链接
      related = find_related(new_memory)
      for mem in related:
          create_link(new_memory, mem)
      
      # 激活相关记忆
      activate(new_memory, depth=2)
  
  def activate(memory, depth):
      memory.activation += 1
      if depth > 0:
          for neighbor in memory.links:
              neighbor.activation += 0.5
              activate(neighbor, depth - 1)
  
  def on_retrieve(memory):
      # 强化链接
      for link in memory.links:
          link.weight += strengthen_factor
  ```

### 开发任务

- [x] 实现 `synonym_edge` 子类型
  - [x] KNN 相似实体查找
  - [x] 同义边创建
- [x] 实现 `strengthen` 子类型
  - [x] 访问时链接强化
  - [x] 未访问衰减
- [x] 实现 `activate` 子类型
  - [x] 激活传播
  - [x] 深度控制
- [x] 实现 `auto_link` 子类型
  - [x] LLM 链接推荐
  - [x] 自动链接建立

### 预估工时: 4 天 → ✅ 已完成

---

## ✅ TODO-D3-3: `forgetting`

### 概述
实现记忆遗忘/淘汰机制。

### 小类参数

```yaml
operators:
  post_insert:
    action: forgetting
    
    # 遗忘类型
    decay_type: "ebbinghaus"         # time_decay | lru | lfu | ebbinghaus | hybrid
    
    # time_decay 专用
    decay_rate: 0.1                  # 每小时衰减率
    decay_floor: 0.1                 # 最小保留权重
    
    # lru 专用
    max_memories: 1000
    evict_count: 100                 # 每次淘汰数量
    
    # lfu 专用 (MemoryOS)
    heat_threshold: 0.3              # 热度阈值
    heat_decay: 0.1                  # 热度衰减
    
    # ebbinghaus 专用 (MemoryBank)
    initial_strength: 1.0
    forgetting_curve: "exponential"  # exponential | power
    review_boost: 0.5                # 复习增强
    
    # hybrid 专用
    factors:
      - type: "time"
        weight: 0.3
      - type: "frequency"
        weight: 0.3
      - type: "importance"
        weight: 0.4
    
    # 淘汰配置
    retention_min: 50                # 最少保留条数
    archive_before_delete: true      # 删除前归档
```

### 参考实现分析

#### MemoryBank (ebbinghaus)
- **代码位置**: `/home/zrc/develop_item/MemoryBank-SiliconFriend/`
- **核心逻辑**:
  ```python
  # 艾宾浩斯遗忘曲线
  def calculate_retention(memory, current_time):
      time_elapsed = current_time - memory.last_access
      strength = memory.strength * exp(-forgetting_rate * time_elapsed)
      return strength
  
  # 复习增强
  def on_retrieve(memory):
      memory.strength += review_boost
      memory.review_count += 1
      memory.last_access = now()
  
  # 定期清理
  def cleanup():
      for memory in memories:
          retention = calculate_retention(memory, now())
          if retention < threshold:
              archive_or_delete(memory)
  ```

#### MemoryOS (lfu + heat)
- **代码位置**: `/home/zrc/develop_item/MemoryOS/`
- **核心逻辑**:
  - 热度追踪 (访问频率 + 时间衰减)
  - 低热度记忆迁移到 LTM
  - LTM 容量满时淘汰

#### LD-Agent (time + session)
- **代码位置**: `/home/zrc/develop_item/LD-Agent/`
- **核心逻辑**:
  - 会话间隔 > 1小时触发
  - STM 内容摘要后转存 LTM
  - 清空 STM

### 开发任务

- [x] 实现 `time_decay` 子类型
  - [x] 时间衰减计算
  - [x] 阈值淘汰
- [x] 实现 `lru` 子类型
  - [x] 最近访问追踪
  - [x] LRU 淘汰
- [x] 实现 `lfu` 子类型
  - [x] 访问频率追踪
  - [x] 热度计算
  - [x] LFU 淘汰
- [x] 实现 `ebbinghaus` 子类型
  - [x] 遗忘曲线计算
  - [x] 复习增强
- [x] 实现 `hybrid` 多因子模式
- [x] 归档逻辑

### 预估工时: 4 天 → ✅ 已完成

---

## ✅ TODO-D3-4: `summarize`

### 概述
对累积记忆进行摘要压缩。

### 小类参数

```yaml
operators:
  post_insert:
    action: summarize
    
    # 触发条件
    trigger_condition: "overflow"    # overflow | periodic | manual
    overflow_threshold: 100          # overflow 触发阈值
    periodic_interval: 3600          # periodic 间隔(秒)
    
    # 摘要策略
    summary_strategy: "hierarchical" # single | hierarchical | incremental
    
    # hierarchical 专用 (MemoryBank)
    hierarchy_levels:
      - name: "daily"
        window: 86400                # 1天
        prompt: "Summarize today's conversations..."
      - name: "weekly"
        window: 604800               # 7天
        prompt: "Summarize this week's key events..."
      - name: "global"
        window: -1                   # 全部
        prompt: "Update the overall summary..."
    
    # incremental 专用 (SCM4LLMs)
    incremental_prompt: |
      Given the existing summary and new memories, 
      update the summary incrementally...
    
    # 输出配置
    replace_originals: false         # 是否替换原始记忆
    store_as_new: true               # 存为新记忆
    summary_importance: 7            # 摘要的重要性
```

### 参考实现分析

#### MemoryBank (hierarchical)
- **代码位置**: `/home/zrc/develop_item/MemoryBank-SiliconFriend/`
- **核心逻辑**:
  - 日摘要: 每日对话汇总
  - 周摘要: 关键事件提取
  - 全局摘要: 用户画像更新

#### SCM4LLMs (incremental)
- **代码位置**: `/home/zrc/develop_item/SCM4LLMs/`
- **核心逻辑**:
  - 增量更新摘要
  - 三元决策: drop/summary/raw

#### MemGPT (overflow)
- **代码位置**: `/home/zrc/develop_item/MemGPT/memgpt/`
- **核心逻辑**:
  - Token 预算超限触发
  - 旧对话摘要后归档

### 开发任务

- [x] 实现 `single` 摘要模式
- [x] 实现 `hierarchical` 层次摘要
  - [x] 日/周/全局层级
  - [x] 定时触发
- [x] 实现 `incremental` 增量摘要
- [x] 触发条件检测
- [x] 摘要存储逻辑

### 预估工时: 3 天 → ✅ 已完成

---

## ✅ TODO-D3-5: `migrate`

### 概述
记忆在不同层级间迁移。

### 小类参数

```yaml
operators:
  post_insert:
    action: migrate
    
    # 迁移策略
    migrate_policy: "heat"           # heat | time | overflow | manual
    
    # heat 专用 (MemoryOS)
    heat_threshold: 0.7              # 热度超阈值升级
    cold_threshold: 0.3              # 热度低于阈值降级
    
    # time 专用 (LD-Agent)
    session_gap: 3600                # 会话间隔(秒)
    
    # overflow 专用
    tier_capacities:
      stm: 100
      mtm: 1000
    
    # 迁移配置
    upgrade_transform: "none"        # none | summarize | extract
    downgrade_transform: "summarize" # none | summarize | compress
```

### 参考实现分析

#### MemoryOS (heat-driven)
- **代码位置**: `/home/zrc/develop_item/MemoryOS/`
- **核心逻辑**:
  - 热度超阈值: MTM → Profile (LTM)
  - 热度过低: 淘汰

#### LD-Agent (session-based)
- **代码位置**: `/home/zrc/develop_item/LD-Agent/`
- **核心逻辑**:
  - 会话间隔检测
  - STM 摘要 → LTM

### 开发任务

- [x] 实现 `heat` 迁移策略
- [x] 实现 `time` 迁移策略
- [x] 实现 `overflow` 迁移策略
- [x] 迁移时的转换处理
- [x] 与 hierarchical_memory 服务联动

### 预估工时: 3 天 → ✅ 已完成

---

## 📋 开发优先级

| 优先级 | Action | 小类 | 参考工作 | 状态 |
|--------|--------|------|----------|----------|
| P0 | `reflection` | threshold, periodic, count | Generative Agents, LoCoMo | ✅ 已完成 |
| P0 | `link_evolution` | synonym_edge, strengthen, activate | HippoRAG, A-mem | ✅ 已完成 |
| P1 | `forgetting` | time_decay, lru, lfu, ebbinghaus | MemoryBank, MemoryOS | ✅ 已完成 |
| P1 | `summarize` | single, hierarchical, incremental | MemGPT, MemoryBank, SCM4LLMs | ✅ 已完成 |
| P1 | `migrate` | heat, time, overflow | MemoryOS, LD-Agent | ✅ 已完成 |

**总计**: ~~18 人天~~ → ✅ 全部完成

---

## 📝 实现说明

### 代码位置
`packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/libs/post_insert.py`

### 核心特性

1. **Reflection (反思)**
   - 支持 threshold/periodic/count 三种触发模式
   - 支持 general/self/other 反思类型
   - 支持二阶反思（反思的反思）
   - 自动存储反思到记忆库

2. **Link Evolution (链接演化)**
   - synonym_edge: 基于 embedding 相似度创建同义边 (HippoRAG)
   - strengthen: 访问时强化链接权重 (A-mem)
   - activate: 激活传播到邻居节点 (A-mem)
   - auto_link: LLM 推荐自动链接 (A-mem)

3. **Forgetting (遗忘)**
   - time_decay: 时间衰减淘汰
   - lru: 最近最少使用淘汰
   - lfu: 最不常用淘汰 (MemoryOS)
   - ebbinghaus: 艾宾浩斯遗忘曲线 (MemoryBank)
   - hybrid: 多因子综合评分

4. **Summarize (摘要)**
   - single: 单次全量摘要
   - hierarchical: 日/周/全局层次摘要 (MemoryBank)
   - incremental: 增量更新摘要 (SCM4LLMs)

5. **Migrate (迁移)**
   - heat: 热度驱动迁移 (MemoryOS)
   - time: 会话间隔迁移 (LD-Agent)
   - overflow: 容量溢出迁移

### 使用示例

```yaml
# 反思配置示例
operators:
  post_insert:
    action: reflection
    trigger_mode: threshold
    importance_threshold: 100
    max_reflections: 5
    store_reflection: true

# 遗忘配置示例
operators:
  post_insert:
    action: forgetting
    decay_type: ebbinghaus
    initial_strength: 1.0
    review_boost: 0.5
    retention_min: 50
```

---

*文档创建时间: 2025-01-27*  
*开发完成时间: 2025-11-27*
