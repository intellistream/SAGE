# SAGE 架构审查 2025-10-22

## 当前包结构和依赖关系

### 架构层次（理想状态）

```
L6: sage-studio        (UI 层)
L5: sage-tools         (CLI 工具)
    sage-apps          (应用示例)
    sage-benchmark     (性能测试)
L4: sage-middleware    (中间件 + 领域算子)
L3: sage-libs          (算法库 + Agents)
    sage-kernel        (执行引擎 + 基础算子)
L1: sage-common        (基础设施)
```

### 当前依赖分析

#### ✅ L6: sage-studio
**依赖**: common, kernel, middleware, libs
**问题**: 
- ❌ 依赖了 libs（应该只依赖 middleware）
- ❌ 可能有不必要的 kernel 直接依赖

**建议**: Studio 应该只通过 middleware API 访问功能

#### ⚠️ L5: sage-tools
**依赖**: common, kernel, middleware, libs, apps, benchmark, studio
**问题**:
- ✅ 作为 CLI 聚合层，依赖所有包是合理的
- ⚠️ 但需要确保是可选依赖

#### ⚠️ L5: sage-apps  
**依赖**: common, kernel, middleware, libs
**问题**:
- ❌ 依赖 kernel 和 libs（应该只依赖 middleware）
- 示例应用应该展示如何通过 middleware 使用 SAGE

#### ⚠️ L5: sage-benchmark
**依赖**: common, kernel, middleware, libs
**问题**:
- ❌ 依赖 kernel 和 libs（benchmark 可能需要这些）
- ⚠️ 需要评估是否真的需要直接依赖底层

#### ✅ L4: sage-middleware
**依赖**: kernel (→ common)
**状态**: ✅ 依赖关系正确

#### ⚠️ L3: sage-libs
**依赖**: middleware
**问题**:
- ❌ **严重问题**: libs 不应该依赖 middleware！
- libs 应该是 L3 层，middleware 是 L4 层
- 这是反向依赖，会导致循环

#### ✅ L3: sage-kernel
**依赖**: common
**状态**: ✅ 依赖关系正确

#### ✅ L1: sage-common
**依赖**: 无 SAGE 内部依赖
**状态**: ✅ 依赖关系正确

## 发现的问题

### 🔴 严重问题：循环依赖风险

```
middleware → kernel → (应该独立)
libs → middleware  ❌ 错误！
```

**libs 不应该依赖 middleware**，因为：
1. libs 是算法库，应该是独立的
2. middleware 需要使用 libs 的算法
3. 当前依赖会造成 middleware ← libs ← middleware 循环

### 🟡 中等问题：上层过度依赖底层

#### Studio 的问题
- Studio 应该是纯 UI 层
- 不应该直接依赖 libs 或 kernel
- 应该通过 middleware 的 API 使用功能

#### Apps 的问题  
- Apps 是示例应用
- 应该展示如何正确使用 SAGE
- 不应该绕过 middleware 直接用底层

#### Benchmark 的问题
- Benchmark 可能需要底层访问（性能测试）
- 但应该明确区分哪些是必需的

## 修复计划

### Phase 1: 修复 libs 依赖（最紧急）

**当前**: `libs → middleware`
**目标**: `libs` 独立，`middleware → libs`

**行动**:
1. 检查 libs 中使用 middleware 的代码
2. 将这些代码移到 middleware 或 apps
3. 更新 libs/pyproject.toml 移除 middleware 依赖

### Phase 2: 规范上层依赖

#### Studio
- 移除 libs 依赖
- 评估是否需要 kernel 依赖
- 通过 middleware API 访问功能

#### Apps  
- 移除不必要的 kernel 和 libs 依赖
- 作为最佳实践示例，应该只用 middleware

#### Benchmark
- 保留必要的底层依赖（性能测试需要）
- 明确标注为 "性能测试专用"

### Phase 3: 补充测试

每个包都应该有：
```
package/
├── src/
│   └── sage/
│       └── {package}/
└── tests/
    ├── unit/
    ├── integration/
    └── conftest.py
```

### Phase 4: 更新文档

更新架构图和依赖说明。

## 期望的最终状态

```
sage-studio ─────────────────────┐
                                  ↓
sage-tools ──────────────┐        │
sage-apps ───────────────┤        │
sage-benchmark ──────────┤        │
                         ↓        ↓
                    sage-middleware
                         ↓
        ┌────────────────┴────────────────┐
        ↓                                  ↓
   sage-kernel                        sage-libs
        ↓                                  ↓
        └──────────────┬───────────────────┘
                       ↓
                  sage-common
```

**关键原则**:
1. 单向依赖，自上而下
2. middleware 是上层的统一入口
3. kernel 和 libs 是平行的底层
4. common 是所有包的基础

## 下一步行动

1. ✅ 检查 sage-libs 中对 middleware 的使用
2. ⚠️ 迁移或重构违反依赖规则的代码
3. ⚠️ 更新所有 pyproject.toml
4. ⚠️ 补充测试覆盖
5. ⚠️ 验证架构并更新文档
