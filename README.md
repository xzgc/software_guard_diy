<div align="center">

  ![Software Guard](https://img.shields.io/badge/Software_Guard-v1.0-blue)
  ![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)
  ![Vue 3](https://img.shields.io/badge/Vue-3.3-brightgreen)
  ![AI](https://img.shields.io/badge/AI-Powered-purple)
  ![License](https://img.shields.io/badge/License-MIT-yellow)

  # 🛡️ Software Guard Diy

  **基于 [Software Guard](https://github.com/your-org/software_guard) 的二次定制开发版本**

  企业级软件分发管理平台 · 增强的权限控制 · 游客访问模式 · 版本编辑能力

  [原始项目](#-致谢上游项目) • [新增功能](#-本版本新增功能) • [快速开始](#-快速开始) • [技术架构](#-技术架构)

</div>

---

## 📋 项目说明

本项目（`software_guard_diy`）是基于开源项目 **Software Guard** 的二次定制开发版本。

我们 fork 了原始项目，在保留其核心架构（FastAPI + Vue 3 + AI 智能审核）的基础上，针对**企业内部实际使用场景**进行了功能增强和优化定制。

### 🎯 二次开发背景

原始 Software Guard 提供了完善的基础能力，但在以下场景中存在不足：

- 🔒 **强认证门槛** — 任何操作（甚至浏览）都必须登录，对内部推广造成障碍
- 🚫 **权限控制粒度不够** — 缺少对单个软件设置下载权限的能力
- 📎 **下载方式单一** — 仅支持实际上传文件，无法使用外部下载地址
- ✏️ **版本元数据不可编辑** — 上传后无法修改版本信息

### ✅ 解决方案

在 `software_guard_diy` 中，我们针对上述问题增加了：

- 👥 **游客访问模式** — 管理员可配置是否允许未登录用户访问
- 🔐 **软件级别下载权限** — 每个软件可独立设置"需登录下载"或"游客可下载"
- 🔗 **外部下载地址支持** — 上传版本时可选择"提供下载地址"模式，地址为空时 fallback 到软件官网
- ✏️ **版本编辑能力** — Admin 可编辑版本的全部字段（版本号、文件信息、外部地址、更新说明等）

---

## 🆕 本版本新增功能

| 模块 | 新增功能 | 说明 |
|------|---------|------|
| **游客访问** | `allow_guest_access` 配置项 | 后台可配置是否允许未登录用户访问 |
| **游客访问** | 路由守卫改造 | 软件列表/详情支持游客访问，个人中心/申请/下载记录仍需登录 |
| **软件权限** | `require_login` 字段 | 每个软件可独立设置是否需要登录才能下载 |
| **软件权限** | UI 标识 | 列表/详情显示"游客可下载"或"需登录下载"标签 |
| **版本上传** | Tab 切换模式 | 支持"上传文件"和"提供下载地址"两种模式 |
| **版本上传** | URL fallback | 未填写外部地址时自动 fallback 到软件官网 |
| **版本编辑** | PUT API | Admin 可编辑版本的全部字段 |
| **版本编辑** | 文件元数据自定义 | 手动设置 file_name 和 file_size，留空时自动获取 |
| **版本编辑** | 文件覆盖/删除 | 上传新文件覆盖原文件，delete_file=true 显式删除 |
| **软件 Logo** | Logo URL 模式 | Logo 字段也支持 Tab 切换：上传图片 / 输入图片URL |
| **软件 Logo** | URL 校验放宽 | 输入 Logo URL 时不再校验扩展名与 URL 格式，仅依赖后端 `urlparse` 兜底（scheme + netloc） |
| **截图上传** | 剪贴板粘贴 | 编辑弹窗打开期间激活全局 `Ctrl+V` 监听，剪贴板中的图片可自动分配到空截图槽 |
| **配置页面** | 安全配置开关 | 在 `/admin/config` 安全配置卡片中控制游客访问 |

### 🔧 本版本修复的 Bug

- 🐛 修复软件列表 Logo 不显示问题（同时支持 `icon_url` 和 `logo` 字段）
- 🐛 修复游客模式下版本列表显示"检查漏洞"按钮的问题
- 🐛 修复 `/api/categories/all` 端点不支持游客访问的问题
- 🐛 修复 admin 用户密码不可在用户管理界面修改的问题（已通过数据库直接重置）
- 🐛 修复版本弹窗点击"确定"无反应 bug（Vue 3 inline 三元表达式 `@ok` 事件处理器被编译为 `o => a ? b : c`——返回函数引用而非调用，改用显式分发方法解决）

---

## 🙏 致谢上游项目

本项目基于以下开源项目进行二次开发：

### Software Guard

- **原始项目地址**：https://github.com/your-org/software_guard
- **许可协议**：MIT License
- **原始作者**：Software Guard Team
- **核心功能**：软件分发管理、版本控制、漏洞追踪、AI 智能审核、权限控制

感谢原作者提供了如此优秀的基础架构，让我们可以在此基础上进行业务定制。

---

## 📦 原始项目核心能力（继承自上游）

我们保留了 Software Guard 原始项目的所有核心能力，包括：

### 用户功能

| 功能 | 描述 |
|------|------|
| 📦 软件浏览 | 支持分类浏览和关键词搜索 |
| ⬇️ 安全下载 | 官方渠道下载，所有文件经过安全检查 |
| 📝 软件申请 | 一键申请未收录软件，AI 智能辅助审核 |
| 📊 下载历史 | 查看个人下载记录 |
| ⚠️ 漏洞提醒 | 下载前自动检查已知安全漏洞 |

### 运维管理

| 功能 | 描述 |
|------|------|
| 🚀 软件管理 | 添加、编辑软件及版本上传 |
| ✅ AI 智能审核 | 自动评估软件申请，智能推荐决策 |
| 🛡️ 漏洞管理 | 漏洞信息录入与批量通知 |
| 📈 数据统计 | 下载量统计与趋势分析 |
| 👥 用户管理 | 用户权限与账号管理 |
| 🎯 系统配置 | 灵活的分类和权限配置 |
| 📤 大文件上传 | 分片上传、进度条、可配置上传大小 |

### AI 智能审核

- **自动识别** - AI 自动识别申请软件的类别和风险等级
- **智能推荐** - 基于软件名称和描述，智能推荐审核决策
- **风险分析** - 分析软件申请的合理性和潜在风险
- **效率提升** - 减少 70% 的人工审核工作量

---

## 🚀 快速开始

### 🐳 Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/xzgc/software_guard_diy.git
cd software_guard_diy

# 2. 创建环境配置文件
cp .env.docker.example .env.docker

# 3. 编辑 .env.docker（必须修改以下变量）：
#    - POSTGRES_PASSWORD  数据库密码（至少16位强密码）
#    - SECRET_KEY         JWT 密钥（可用 python -c "import secrets; print(secrets.token_hex(32))" 生成）
#    - ADMIN_PASSWORD     管理员密码（至少12位强密码）
nano .env.docker

# 4. 启动服务（后台运行）
docker compose --env-file .env.docker up -d

# 5. 查看运行状态
docker compose ps

# 6. 查看日志
docker compose logs -f app
```

启动完成后访问 **http://localhost:8000** 即可使用。

### 🔧 本地开发

**前置要求：** Python 3.9+, Node.js 16+, PostgreSQL 12+, uv, pnpm

#### 后端

```bash
cd backend
uv sync
cp .env.example .env  # 配置数据库连接等
uv run python main.py
```

后端运行在 **http://localhost:8000**

#### 前端

```bash
cd frontend
pnpm install
pnpm dev
```

前端运行在 **http://localhost:5173**

### 👤 默认账号

首次启动自动创建管理员账号：

```
用户名: admin
密码: （见 .env.docker 中的 ADMIN_PASSWORD 配置）
```

> ⚠️ **生产环境请务必使用强密码，登录后建议立即修改！**

---

## 🆕 本版本特有配置说明

### 配置游客访问

1. 使用 admin 账号登录
2. 进入 **管理后台 → 配置管理 → 安全配置**
3. 找到 **"允许游客访问"** 开关
4. 关闭后，未登录用户访问站点会自动跳转到登录页

### 设置软件下载权限

1. 进入 **管理后台** 或 **软件列表** 的"新建软件" / "编辑软件" 弹窗
2. 在表单底部找到 **"需要登录下载"** 开关
3. 关闭后，游客无需登录即可下载该软件（依赖"允许游客访问"总开关）

### 上传版本时使用外部下载地址

1. 进入软件详情页 → "上传新版本"
2. 在弹窗中选择 **"提供下载地址"** Tab
3. 填写版本号、下载地址（留空则 fallback 到软件官网）
4. 点击确定

### 编辑版本（仅 admin）

1. 进入软件详情页
2. 在版本表格中找到目标版本，点击 **"编辑"** 按钮
3. 在弹窗中修改：版本号、文件、外部地址、更新说明、文件名、文件大小
4. 上传新文件会覆盖原文件，点击确定提交

---

## 🏗️ 技术架构

### 后端技术栈

- **FastAPI** - 高性能异步 Web 框架
- **SQLAlchemy** - Python ORM
- **PostgreSQL** - 关系型数据库
- **Pydantic** - 数据验证和设置管理
- **AI Service** - 集成大语言模型的智能审核服务
- **uv** - Python 包管理器

### 前端技术栈

- **Vue 3** - 渐进式 JavaScript框架
- **Ant Design Vue** - 企业级 UI 组件库
- **Vite** - 前端构建工具
- **Pinia** - Vue 3 状态管理
- **Axios** - HTTP 客户端
- **pnpm** - 包管理器

---

## 📁 项目结构

```
software_guard_diy/
├── backend/                # 后端服务（FastAPI）
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # 数据验证
│   │   └── services/       # 业务服务
│   ├── storage/            # 文件存储
│   └── main.py
├── frontend/               # 前端（Vue 3）
│   ├── src/
│   │   ├── api/            # API 客户端
│   │   ├── stores/         # Pinia 状态
│   │   ├── router/         # 路由
│   │   ├── views/          # 页面
│   │   └── App.vue
│   ├── package.json
│   └── vite.config.js
├── docs/                   # 文档
├── docker-compose.yml
├── Dockerfile
└── README.md
```

---

## 📄 许可协议

本项目基于上游 [Software Guard](https://github.com/your-org/software_guard)（MIT License）进行二次开发，遵循相同的 MIT License。

---

## 🤝 贡献与反馈

- 🐛 **报告问题**：[GitHub Issues](https://github.com/xzgc/software_guard_diy/issues)
- 💡 **功能建议**：[GitHub Discussions](https://github.com/xzgc/software_guard_diy/discussions)
- ⭐ **支持项目**：给本仓库点 Star

---

<div align="center">

  **本项目基于 Software Guard 开源项目二次开发，感谢原作者的贡献！**

  [⭐ Star 本项目](https://github.com/xzgc/software_guard_diy) • [查看上游项目](https://github.com/your-org/software_guard)

</div>
