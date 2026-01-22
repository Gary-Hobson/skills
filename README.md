# Claude Code Skills 说明文档

本目录包含了一系列 Claude Code 技能（Skills），用于自动化和标准化常见的开发工作流程。

## 什么是 Skills？

Skills 是 Claude Code 的可调用能力模块，每个 skill 封装了特定领域的最佳实践和自动化逻辑。


## 如何使用？
1. 安装依赖
```bash
pip install python-gerrit-api
# 需要 github 提交 PR 权限
sudo apt-get install gh
gh auth login
gh auth status
```

2. 下载仓库

```bash
git clone https://github.com/Gary-Hobson/skills.git .claude

#or

npx openskills install Gary-Hobson/skills
npx openskills sync
```

### 自动调用
直接描述你的需求，Claude 会自动选择合适的 skill：
```bash
"帮我创建一个 commit"          # 自动使用 git-commit
"创建一个 Pull Request"       # 自动使用 github-pr-creation
"处理 PR 的审查评论"           # 自动使用 github-pr-review
"将 https://your-gerrit-server.com/c/repo/nuttx/+/1234 上提交到 apache nuttx 社区" # 自动使用 gerritcomment 和 nuttx-commit-pr
```

## 可用的 Skills

| Skill | 描述 | 依赖 | 来源 |
|-------|------|----------|------|
| **git-commit** | 创建符合 Conventional Commits 规范的 git commit | - | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills) |
| **gerritcomment** | 获取和发布 Gerrit 代码审查评论（JSON 格式）| ⚠️ 需要[设置环境变量](#gerrit-skill-gerritcomment) `GERRIT_USER`, `GERRIT_HTTP_PASSWORD`, `GERRIT_BASE_URL` | [XuNeo/skills](https://github.com/XuNeo/skills) |
| **github-pr-review** | 处理 GitHub PR 审查评论，按严重程度分类并修复问题 | ⚠️ 需要[安装并登录 GitHub CLI](#github-skills-pr-review-pr-creation-pr-merge) | [fvadicamo/dev-agent-skills](https://github.com/fvadicamo/dev-agent-skills) |
| **github-pr-creation** | 创建 GitHub PR，自动分析 commits、验证任务完成、生成描述 | ⚠️ 需要[安装并登录 GitHub CLI](#github-skills-pr-review-pr-creation-pr-merge) | [fvadicamo/dev-agent-skills](https://github.com/fvadicamo/dev-agent-skills) |
| **github-pr-merge** | 合并 GitHub PR，带预合并验证（测试、lint、CI 检查）| ⚠️ 需要[安装并登录 GitHub CLI](#github-skills-pr-review-pr-creation-pr-merge) | [fvadicamo/dev-agent-skills](https://github.com/fvadicamo/dev-agent-skills) |
| **nuttx-commit-pr** | 生成符合 nuttx 社区要求的 git commit 和 PR | - | [Gary-Hobson](https://github.com/Gary-Hobson/skills) |
| **skill-creator** | 创建新 Claude Code skills 的指南和模板 | - | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills) |
| **mcp-builder** | 创建 MCP 服务器，支持 FastMCP (Python) 和 MCP SDK (TypeScript) | - | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills) |
| **creating-skills** | 遵循 Anthropic 官方最佳实践创建高质量 skills | - | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills) |
| **template** | Skill 模板示例，用作创建新 skill 的起点 | - | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills) |

---

## 环境设置总览

### GitHub Skills (pr-review, pr-creation, pr-merge)
```bash
# 安装 GitHub CLI
brew install gh
# 或在 Ubuntu/Debian 上
sudo apt-get install gh

# 登录（仅需一次）
gh auth login

# 验证登录状态
gh auth status
```

### Gerrit Skill (gerritcomment)
```bash
# 安装 Python Gerrit API
pip install python-gerrit-api

# 在 .claude/skills/gerritcomment/.env 文件中配置 `GERRIT_USER`, `GERRIT_HTTP_PASSWORD`, `GERRIT_BASE_URL`
cp .claude/skills/gerritcomment/.env.example .claude/skills/gerritcomment/.env

# Or

# 设置环境变量（在 ~/.bashrc 或 ~/.zshrc 中）
export GERRIT_USER="your-username"
export GERRIT_HTTP_PASSWORD="your-http-password"
export GERRIT_BASE_URL="https://your-gerrit-server.com"

```
