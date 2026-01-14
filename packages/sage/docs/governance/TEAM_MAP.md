# SAGE 包级角色代号总览（placeholders）

- 版本：2026-01-14
- 说明：仅罗列代号，姓名暂用 `TBD`，后续按实际分工替换；通用制度见 packages/sage/docs/governance/TEAM_BASE.md。

| 包 | Maintainer | Engineering Core | Research Core | 备注 |
| --- | --- | --- | --- | --- |
| sage (meta) | A1 | — | — | 元包，仅治理文档与依赖聚合，无实际代码 |
| sage-common (L1) | A1 | B1 | — | 代码量小，配置/端口/路径等基础能力 |
| sage-platform (L2) | A2 | B2, B3 | C1（按需） | 平台服务/控制面，中等复杂度 |
| sage-kernel (L3) | A3 | B4, B5, B6 | C2, C3 | 核心数据流/执行引擎/调度，复杂度高，需重点投入 |
| sage-libs (L3) | A4 | B7, B8, B9 | C4, C5, C6 | 算法/RAG/Agent/独立库，复杂度高，研究密集 |
| sage-middleware (L4) | A5 | B10, B11, B12 | C7, C8 | 组件/VDB/Memory/外部服务集成，复杂度高 |
| sage-cli (L5) | A1 | B13 | — | 用户入口，代码量中等，兼容性要求高 |
| sage-tools (L5) | A2 | B14, B15 | — | 质量/发布/检查工具链，代码量中等 |

> 所有姓名保持 `TBD`，仅当实际分工确定后再填写实名。
