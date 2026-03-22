# GitHub Workflows (Main-Only Policy)

本仓库采用 main-only 分支策略。

## Branch Strategy

- 默认分支: main
- 常规修改: 从 feature/* 分支发起 PR 合并到 main
- 较大功能: 必须使用 feature/* 分支并通过 PR 合并到 main
- 禁止: main-dev 分支流程

## Workflow Triggers

- CI workflows: PR to main, push to main, or workflow_dispatch
- Release workflows: push to main or manual dispatch

## Typical Flow

1. 从 main 拉取最新代码
2. 创建 feature/<topic> 分支开发
3. 提交并推送 feature 分支
4. 创建 PR: feature/<topic> -> main
5. CI 通过后合并到 main

## Notes

- 若历史文档中出现 main-dev，请以本文件和 .github/copilot-instructions.md 的 main-only 规则为准。
