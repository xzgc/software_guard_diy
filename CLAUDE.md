# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Software Guard is an internal company software download station with a monorepo structure containing a FastAPI backend and Vue 3 frontend. The application manages software distribution, download tracking, vulnerability notifications, and user access control.

## Development Commands

### Backend (FastAPI)
Located in `backend/` directory. Uses `uv` as the Python package manager.

```bash
cd backend
uv sync                      # Install dependencies
uv run python main.py        # Start development server (http://localhost:8000)
```

### Frontend (Vue 3 + Vite)
Located in `frontend/` directory. Uses `pnpm` as the Node.js package manager.

```bash
cd frontend
pnpm install                 # Install dependencies
pnpm dev                     # Start development server (http://localhost:5173)
pnpm build                   # Build for production
```

## Architecture

### Backend Structure (`backend/app/`)

- **`api/`** - FastAPI route handlers organized by feature:
  - `auth.py` - Authentication endpoints (login, register, token verification)
  - `software.py` - Software CRUD operations and version management
  - `request.py` - Software request workflow (users request software, ops review)
  - `download.py` - Download tracking and statistics
  - `vulnerability.py` - Security vulnerability records for software versions
  - `user.py` - User management
  - `stats.py` - Dashboard statistics
  - `category.py` - Software category management
  - `config.py` - System configuration (site name, upload limits, etc.)
  - `upload.py` - File upload with chunked upload session support

- **`core/`** - Core infrastructure:
  - `config.py` - Pydantic settings with environment variable support (reads from `.env`)
  - `database.py` - SQLAlchemy session management and engine configuration
  - `security.py` - JWT token creation/password hashing (bcrypt)
  - `deps.py` - FastAPI dependency injection for auth/permissions (`require_admin`, `require_ops`)

- **`models/`** - SQLAlchemy ORM models:
  - `user.py` - User with roles (ADMIN, OPS, USER), supports local/LDAP auth
  - `software.py` - Software and SoftwareVersion (one-to-many)
  - `category.py` - SoftwareCategory for organizing software
  - `request.py` - SoftwareRequest workflow model
  - `download.py` - DownloadLog tracking
  - `vulnerability.py` - Vulnerability records linked to software versions
  - `audit.py` - AuditLog for compliance
  - `config.py` - Config key-value store for site settings
  - `upload.py` - UploadSession for chunked upload tracking

- **`schemas/`** - Pydantic models for request/response validation
- **`services/`** - Business logic services:
  - `ai_service.py` - AI-powered software request review (requires AI_API_KEY)

### Frontend Structure (`frontend/src/`)

- **`api/`** - Axios-based API clients, one per backend route module
- **`stores/`** - Pinia stores for state management (user.js for auth state)
- **`router/`** - Vue Router configuration with auth guards
- **`views/`** - Page components organized by feature:
  - `Login.vue` - Authentication
  - `AppLayout.vue` / `AdminLayout.vue` - Main app shell with navigation
  - `Software/` - Software browsing and details
  - `Admin/` - Ops/admin dashboard (Categories, Config, Dashboard, Requests, Users, Vulnerabilities)
  - `Profile.vue`, `MyDownloads.vue`, `Requests.vue` - User-facing pages

### Key Architectural Patterns

**Authentication Flow:**
- Backend uses JWT with `OAuth2PasswordBearer` scheme
- Frontend stores token in Pinia store (`useUserStore`)
- Axios interceptor automatically includes `Authorization: Bearer <token>` header
- Route guards check `userStore.token` and `userStore.isOps()` for admin access

**Permission System:**
- Three roles: USER (default), OPS, ADMIN
- Backend uses `require_ops` dependency for protected endpoints
- Frontend checks `userStore.isOps()` (returns true for both OPS and ADMIN roles)

**Database Setup:**
- Tables auto-created on startup via `Base.metadata.create_all()` in `main.py` lifespan
- Auto-migration: adds missing columns (`token_version`, `auth_source`) to existing tables
- Default admin account created on first run (username: `admin`, password: `admin123`)
- Uses PostgreSQL with connection pooling

**File Storage:**
- Software files stored in `backend/storage/` directory
- Configured via `STORAGE_PATH` in settings

## Configuration

### Backend Environment Variables (`backend/.env`)
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT signing key (auto-generated if not set, but tokens won't persist across restarts)
- `STORAGE_PATH` - File storage location
- `MAX_UPLOAD_SIZE` - Max upload size in bytes (default: 3GB)
- `FIRST_ADMIN_USERNAME` / `FIRST_ADMIN_PASSWORD` / `FIRST_ADMIN_EMAIL` - Initial admin account
- `ALLOW_REGISTRATION` - Whether to allow public registration (default: false)
- `CORS_ORIGINS` - Comma-separated list of allowed CORS origins

### Docker Deployment
```bash
# Start all services (app + postgres)
docker compose --env-file .env.docker up -d

# View logs
docker compose logs -f app

# Stop services
docker compose down

# Stop and remove volumes (destroys data)
docker compose down -v
```

### Frontend Proxy
The Vite dev server proxies `/api` requests to `http://127.0.0.1:8000` (see `vite.config.js`).

## Important Notes

- The project uses Chinese comments and UI text throughout
- CORS is configured for `http://localhost:5173` and `http://localhost:3000`
- File uploads are limited to 3GB with specific allowed extensions (`.exe`, `.msi`, `.zip`, etc.)
- Upload size can be configured per-tenant via `Config` model (key: `max_upload_size`)
- Site name and description are configurable via `Config` model (keys: `site_name`, `site_description`)
- The `upload.py` router is registered directly in `main.py` (not via `api/__init__.py`)
- Alembic is installed but migrations are not currently configured (tables use auto-create)
- AI review service requires `AI_API_KEY` and `AI_MODEL` environment variables

<!-- superpowers-zh:begin (do not edit between these markers) -->
# Superpowers-ZH 中文增强版

本项目已安装 superpowers-zh 技能框架（20 个 skills）。

## 核心规则

1. **收到任务时，先检查是否有匹配的 skill** — 哪怕只有 1% 的可能性也要检查
2. **设计先于编码** — 收到功能需求时，先用 brainstorming skill 做需求分析
3. **测试先于实现** — 写代码前先写测试（TDD）
4. **验证先于完成** — 声称完成前必须运行验证命令

## 可用 Skills

Skills 位于 `.claude/skills/` 目录，每个 skill 有独立的 `SKILL.md` 文件。

- **brainstorming**: 在任何创造性工作之前必须使用此技能——创建功能、构建组件、添加功能或修改行为。在实现之前先探索用户意图、需求和设计。
- **chinese-code-review**: 中文 review 沟通参考——话术模板、分级标注（必须修复/建议修改/仅供参考）、国内团队常见反模式应对。仅在用户显式 /chinese-code-review 时调用，不要根据上下文自动触发。
- **chinese-commit-conventions**: 中文 commit 与 changelog 配置参考——Conventional Commits 中文适配、commitlint/husky/commitizen 中文模板、conventional-changelog 中文配置。仅在用户显式 /chinese-commit-conventions 时调用，不要根据上下文自动触发。
- **chinese-documentation**: 中文文档排版参考——中英文空格、全半角标点、术语保留、链接格式、中文文案排版指北约定。仅在用户显式 /chinese-documentation 时调用，不要根据上下文自动触发。
- **chinese-git-workflow**: 国内 Git 平台配置参考——Gitee、Coding.net、极狐 GitLab、CNB 的 SSH/HTTPS/凭据/CI 接入差异与镜像同步配置。仅在用户显式 /chinese-git-workflow 时调用，不要根据上下文自动触发。
- **dispatching-parallel-agents**: 当面对 2 个以上可以独立进行、无共享状态或顺序依赖的任务时使用
- **executing-plans**: 当你有一份书面实现计划需要在单独的会话中执行，并设有审查检查点时使用
- **finishing-a-development-branch**: 当实现完成、所有测试通过、需要决定如何集成工作时使用——通过提供合并、PR 或清理等结构化选项来引导开发工作的收尾
- **mcp-builder**: MCP 服务器构建方法论 — 系统化构建生产级 MCP 工具，让 AI 助手连接外部能力
- **receiving-code-review**: 收到代码审查反馈后、实施建议之前使用，尤其当反馈不明确或技术上有疑问时——需要技术严谨性和验证，而非敷衍附和或盲目执行
- **requesting-code-review**: 完成任务、实现重要功能或合并前使用，用于验证工作成果是否符合要求
- **subagent-driven-development**: 当在当前会话中执行包含独立任务的实现计划时使用
- **systematic-debugging**: 遇到任何 bug、测试失败或异常行为时使用，在提出修复方案之前执行
- **test-driven-development**: 在实现任何功能或修复 bug 时使用，在编写实现代码之前
- **using-git-worktrees**: 当需要开始与当前工作区隔离的功能开发，或在执行实现计划之前使用——通过原生工具或 git worktree 回退机制确保隔离工作区存在
- **using-superpowers**: 在开始任何对话时使用——确立如何查找和使用技能，要求在任何响应（包括澄清性问题）之前调用 Skill 工具
- **verification-before-completion**: 在宣称工作完成、已修复或测试通过之前使用，在提交或创建 PR 之前——必须运行验证命令并确认输出后才能声称成功；始终用证据支撑断言
- **workflow-runner**: 在 Claude Code / OpenClaw / Cursor 中直接运行 agency-orchestrator YAML 工作流——无需 API key，使用当前会话的 LLM 作为执行引擎。当用户提供 .yaml 工作流文件或要求多角色协作完成任务时触发。
- **writing-plans**: 当你有规格说明或需求用于多步骤任务时使用，在动手写代码之前
- **writing-skills**: 当创建新技能、编辑现有技能或在部署前验证技能是否有效时使用

## 如何使用

当任务匹配某个 skill 时，使用 `Skill` 工具加载对应 skill 并严格遵循其流程。绝不要用 Read 工具读取 SKILL.md 文件。

如果你认为哪怕只有 1% 的可能性某个 skill 适用于你正在做的事情，你必须调用该 skill 检查。
<!-- superpowers-zh:end -->
