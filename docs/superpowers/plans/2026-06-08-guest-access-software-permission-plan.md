# 游客访问与软件权限功能实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为 Software Guard 添加软件级别下载权限控制、游客访问支持、版本外部下载地址上传功能

**架构：** 通过在 Software 模型添加 `require_login` 字段控制下载权限，在 SoftwareVersion 模型添加 `original_download_url` 支持外部地址，后端 API 支持可选认证，前端配置页面控制游客访问开关

**技术栈：** FastAPI + SQLAlchemy + Vue 3 + Pinia + Ant Design Vue

---

## 文件结构

| 职责 | 文件 |
|------|------|
| 数据模型 | `backend/app/models/software.py` |
| Schema | `backend/app/schemas/software.py` |
| 软件API | `backend/app/api/software.py` |
| 下载API | `backend/app/api/download.py` |
| 站点信息API | `backend/main.py` |
| 配置API | `backend/app/api/config.py` |
| 前端配置页 | `frontend/src/views/Admin/Config.vue` |
| 前端站点Store | `frontend/src/stores/site.js` |
| 前端路由守卫 | `frontend/src/router/index.js` |
| 前端软件列表 | `frontend/src/views/Software/List.vue` |
| 前端软件详情 | `frontend/src/views/Software/Detail.vue` |

---

## 任务清单

### 任务 1：后端 — Software 模型添加权限字段

**文件：**
- 修改：`backend/app/models/software.py:1-50`

- [ ] **步骤 1：查看现有 Software 和 SoftwareVersion 模型结构**

运行：`head -80 /root/dockerProjectDir/software_guard/backend/app/models/software.py`

- [ ] **步骤 2：在 Software 模型添加 `require_login` 字段**

在 `Software` 类中添加：
```python
require_login: bool = Column(Boolean, default=True, nullable=False)
```

- [ ] **步骤 3：在 SoftwareVersion 模型添加 `original_download_url` 字段**

在 `SoftwareVersion` 类中添加：
```python
original_download_url: str = Column(String(500), nullable=True)
```

- [ ] **步骤 4：在 main.py 的 lifespan 中添加自动迁移**

确认自动迁移逻辑已覆盖新字段（检查列是否存在，如不存在则 ALTER TABLE 添加）

- [ ] **步骤 5：Commit**

```bash
git add backend/app/models/software.py backend/main.py
git commit -m "feat: Software 模型添加 require_login 和 original_download_url 字段"
```

---

### 任务 2：后端 — Schema 添加新字段

**文件：**
- 修改：`backend/app/schemas/software.py`

- [ ] **步骤 1：查看现有 schema 文件**

运行：`cat /root/dockerProjectDir/software_guard/backend/app/schemas/software.py`

- [ ] **步骤 2：在 SoftwareCreate 和 SoftwareUpdate 添加 `require_login` 字段**

```python
require_login: bool = True
```

- [ ] **步骤 3：在 SoftwareResponse 添加 `require_login` 字段**

```python
require_login: bool
```

- [ ] **步骤 4：在 VersionCreate 添加 `original_download_url` 字段**

```python
original_download_url: str | None = None
```

- [ ] **步骤 5：在 VersionInfo 添加 `original_download_url` 字段**

```python
original_download_url: str | None
```

- [ ] **步骤 6：Commit**

```bash
git add backend/app/schemas/software.py
git commit -m "feat: Schema 添加 require_login 和 original_download_url 字段"
```

---

### 任务 3：后端 — 软件列表/详情 API 支持游客访问

**文件：**
- 修改：`backend/app/api/software.py`

- [ ] **步骤 1：查看 software.py 中的 get_current_active_user 引用**

运行：`grep -n "get_current_active_user\|get_optional_current_user" /root/dockerProjectDir/software_guard/backend/app/api/software.py`

- [ ] **步骤 2：将软件列表和详情接口的认证改为 get_optional_current_user**

```python
from app.core.deps import get_optional_current_user

@router.get("")
async def list_software(
    ...
    current_user: User | None = Depends(get_optional_current_user),
    ...
)

@router.get("/{software_id}")
async def get_software(
    software_id: int,
    ...
    current_user: User | None = Depends(get_optional_current_user),
    ...
)
```

- [ ] **步骤 3：Commit**

```bash
git add backend/app/api/software.py
git commit -m "feat: 软件列表/详情 API 支持游客访问"
```

---

### 任务 4：后端 — 下载 API 实现 require_login 检查和 external_url

**文件：**
- 修改：`backend/app/api/download.py`

- [ ] **步骤 1：查看现有 download.py 结构**

运行：`cat /root/dockerProjectDir/software_guard/backend/app/api/download.py`

- [ ] **步骤 2：修改 download 依赖为 get_optional_current_user**

```python
from app.core.deps import get_optional_current_user

@router.get("/{version_id}")
async def download_software(
    version_id: int,
    request: Request,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
```

- [ ] **步骤 3：在下载函数开头添加 require_login 检查**

```python
# 获取版本信息和所属软件
version = db.query(SoftwareVersion).filter(SoftwareVersion.id == version_id).first()
if not version:
    raise HTTPException(status_code=404, detail="版本不存在")

software = db.query(Software).filter(Software.id == version.software_id).first()

# 检查下载权限
if software.require_login and current_user is None:
    raise HTTPException(
        status_code=401,
        detail="该软件需要登录后才能下载"
    )
```

- [ ] **步骤 4：修改下载逻辑支持 original_download_url**

```python
# 如果有外部下载地址，返回下载地址信息
if version.original_download_url:
    return {
        "download_url": version.original_download_url,
        "file_name": version.file_name,
        "is_external": True
    }

# 否则返回文件流（原有逻辑）
...
```

- [ ] **步骤 5：Commit**

```bash
git add backend/app/api/download.py
git commit -m "feat: 下载 API 实现 require_login 检查和 external_url 支持"
```

---

### 任务 5：后端 — 站点信息 API 返回 allow_guest_access

**文件：**
- 修改：`backend/main.py`

- [ ] **步骤 1：查看现有 site_info 函数**

运行：`grep -A 15 "def site_info" /root/dockerProjectDir/software_guard/backend/main.py`

- [ ] **步骤 2：修改 site_info 返回 allow_guest_access**

```python
@app.get("/api/site/info")
async def site_info(db=Depends(get_db)):
    name_cfg = db.query(Config).filter(Config.key == "site_name").first()
    desc_cfg = db.query(Config).filter(Config.key == "site_description").first()
    allow_guest_cfg = db.query(Config).filter(Config.key == "allow_guest_access").first()
    return {
        "name": name_cfg.value if name_cfg else settings.APP_NAME,
        "description": desc_cfg.value if desc_cfg else "公司内网软件下载站",
        "allow_guest_access": allow_guest_cfg.value == "true" if allow_guest_cfg else True
    }
```

- [ ] **步骤 3：Commit**

```bash
git add backend/main.py
git commit -m "feat: 站点信息 API 返回 allow_guest_access 配置"
```

---

### 任务 6：后端 — 配置 API 支持 allow_guest_access

**文件：**
- 修改：`backend/app/api/config.py`

- [ ] **步骤 1：确认配置 API 结构支持动态配置项**

配置 API 已通过 Config 模型支持任意 key-value，无需修改

- [ ] **步骤 2：确认默认值逻辑正确**

在数据库初始化时，确保 allow_guest_access 的默认值为 "true"

- [ ] **步骤 3：Commit**

```bash
git commit --allow-empty -m "chore: 配置 API 已支持 allow_guest_access，无需修改"
```

---

### 任务 7：前端 — Site Store 添加 allowGuestAccess

**文件：**
- 修改：`frontend/src/stores/site.js`

- [ ] **步骤 1：查看现有 site store**

运行：`cat /root/dockerProjectDir/software_guard/frontend/src/stores/site.js`

- [ ] **步骤 2：添加 allowGuestAccess 字段**

```javascript
const state = reactive({
    name: '',
    description: '',
    allowGuestAccess: true  // 新增
})

// 在 fetchSiteInfo 中更新
const fetchSiteInfo = async () => {
    const res = await axios.get('/api/site/info')
    state.name = res.data.name
    state.description = res.data.description
    state.allowGuestAccess = res.data.allow_guest_access ?? true  // 新增
}
```

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/stores/site.js
git commit -m "feat: Site Store 添加 allowGuestAccess 字段"
```

---

### 任务 8：前端 — 路由守卫支持游客访问

**文件：**
- 修改：`frontend/src/router/index.js`

- [ ] **步骤 1：查看现有路由守卫逻辑**

运行：`grep -n "requiresAuth\|next\|/login" /root/dockerProjectDir/software_guard/frontend/src/router/index.js | head -30`

- [ ] **步骤 2：修改路由守卫，添加 siteStore.allowGuestAccess 检查**

```javascript
import { useSiteStore } from '@/stores/site'

// 在 router guard 中
if (to.meta.requiresAuth && !userStore.token && !siteStore.allowGuestAccess) {
    next('/login')
}
```

注意：需要确保 siteStore 在 router 初始化前已加载，可以在 App.vue 的 onMounted 中先调用 fetchSiteInfo

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/router/index.js
git commit -m "feat: 路由守卫支持游客访问配置"
```

---

### 任务 9：前端 — 配置页面添加 allow_guest_access 开关

**文件：**
- 修改：`frontend/src/views/Admin/Config.vue`

- [ ] **步骤 1：查看现有安全配置卡片结构**

运行：`grep -n "allow_registration\|安全配置" /root/dockerProjectDir/software_guard/frontend/src/views/Admin/Config.vue`

- [ ] **步骤 2：在安全配置卡片添加 allow_guest_access 开关**

在 `allow_registration` 配置项下方添加：

```vue
<a-form-item label="允许游客访问">
  <a-switch
    v-model="configForm.allow_guest_access"
    checked-children="开"
    un-checked-children="关"
  />
  <div class="form-item-tip">开启后，未登录用户可以浏览和下载软件</div>
</a-form-item>
```

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/views/Admin/Config.vue
git commit -m "feat: 配置页面添加允许游客访问开关"
```

---

### 任务 10：前端 — 软件列表页根据 require_login 显示下载按钮

**文件：**
- 修改：`frontend/src/views/Software/List.vue`

- [ ] **步骤 1：查看软件列表模板中的下载逻辑**

运行：`grep -n "下载\|download" /root/dockerProjectDir/software_guard/frontend/src/views/Software/List.vue`

- [ ] **步骤 2：修改下载按钮逻辑**

根据软件 `require_login` 字段和用户登录状态显示不同内容：
- `require_login=true` 且已登录：显示"下载"按钮
- `require_login=true` 且未登录：显示"登录后下载"提示
- `require_login=false`：显示"下载"按钮（游客可下载）

```vue
<template v-for="software in softwareList">
  <a-button
    v-if="!software.require_login || userStore.token"
    type="primary"
    @click="handleDownload(software)"
  >
    下载
  </a-button>
  <a-button v-else type="text" disabled>
    登录后下载
  </a-button>
</template>
```

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/views/Software/List.vue
git commit -m "feat: 软件列表页根据 require_login 显示下载按钮"
```

---

### 任务 11：前端 — 软件详情页上传版本 Tab 切换

**文件：**
- 修改：`frontend/src/views/Software/Detail.vue`

- [ ] **步骤 1：查看现有上传版本弹窗结构**

运行：`grep -n "showVersionModal\|上传新版本\|fileList" /root/dockerProjectDir/software_guard/frontend/src/views/Software/Detail.vue | head -20`

- [ ] **步骤 2：将上传版本弹窗改为 Tab 切换**

```vue
<a-modal v-model:open="showVersionModal" title="上传新版本">
  <a-tabs v-model:activeKey="versionTab">
    <a-tab-pane key="upload" tab="上传文件">
      <!-- 现有文件上传内容 -->
    </a-tab-pane>
    <a-tab-pane key="url" tab="提供下载地址">
      <a-form-item label="外部下载地址" required>
        <a-input
          v-model:value="versionForm.external_url"
          placeholder="请输入软件下载地址"
        />
      </a-form-item>
      <a-form-item label="版本号" required>
        <a-input v-model:value="versionForm.version" placeholder="如: 1.0.0" />
      </a-form-item>
      <a-form-item label="更新说明">
        <a-textarea v-model:value="versionForm.release_notes" :rows="3" />
      </a-form-item>
    </a-tab-pane>
  </a-tabs>
</a-modal>
```

- [ ] **步骤 3：添加 versionTab 和 versionForm.external_url**

```javascript
const versionTab = ref('upload')
const versionForm = reactive({
    version: '',
    release_notes: '',
    external_url: ''  // 新增
})
```

- [ ] **步骤 4：修改 handleUploadVersion 支持 external_url**

```javascript
const handleUploadVersion = async () => {
    if (versionTab.value === 'url') {
        // 外部地址模式
        await softwareApi.uploadVersion(software.value.id, {
            version: versionForm.version,
            release_notes: versionForm.release_notes,
            original_download_url: versionForm.external_url
        })
    } else {
        // 文件上传模式 - 现有逻辑
        ...
    }
}
```

- [ ] **步骤 5：Commit**

```bash
git add frontend/src/views/Software/Detail.vue
git commit -m "feat: 软件详情页上传版本弹窗支持 Tab 切换外部地址"
```

---

### 任务 12：前端 — 软件详情页下载逻辑支持 external_url fallback

**文件：**
- 修改：`frontend/src/views/Software/Detail.vue`

- [ ] **步骤 1：查看现有下载函数**

运行：`grep -n "downloadVersion\|fetch\|/downloads" /root/dockerProjectDir/software_guard/frontend/src/views/Software/Detail.vue`

- [ ] **步骤 2：修改下载逻辑**

```javascript
const downloadVersion = async (version) => {
    try {
        message.loading({ content: '准备下载...', key: 'download' })

        const token = localStorage.getItem('token')
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {}

        const response = await fetch(`/api/downloads/${version.id}`, { headers })

        if (response.status === 401) {
            message.error({ content: '该软件需要登录后才能下载', key: 'download' })
            return
        }

        if (response.status === 200) {
            const data = await response.json()
            if (data.is_external && data.download_url) {
                // 外部地址，直接跳转
                window.open(data.download_url, '_blank')
                message.success({ content: '正在跳转到下载页面', key: 'download' })
            } else {
                // 文件下载，现有逻辑
                const blob = await response.blob()
                ...
            }
        }
    } catch (error) {
        message.error({ content: '下载失败', key: 'download' })
    }
}
```

- [ ] **步骤 3：在版本列表中显示下载地址状态**

```vue
<a-tag v-if="version.original_download_url" color="blue">
  外部地址
</a-tag>
```

- [ ] **步骤 4：Commit**

```bash
git add frontend/src/views/Software/Detail.vue
git commit -m "feat: 软件详情页下载逻辑支持 external_url 和 fallback"
```

---

### 任务 13：前端 — 新建/编辑软件表单添加 require_login 开关

**文件：**
- 修改：`frontend/src/views/Software/List.vue`（新建）
- 修改：`frontend/src/views/Software/Detail.vue`（编辑）

- [ ] **步骤 1：在 List.vue 新建软件表单添加 require_login**

在官网链接字段后添加：
```vue
<a-form-item label="需要登录下载">
  <a-switch v-model="uploadForm.require_login" />
  <div class="form-item-tip">关闭后，游客可直接下载</div>
</a-form-item>
```

- [ ] **步骤 2：在 Detail.vue 编辑软件表单添加 require_login**

同上

- [ ] **步骤 3：确保 uploadForm 和 editForm 包含 require_login**

```javascript
const uploadForm = reactive({
    name: '',
    category: '',
    description: '',
    official_url: '',
    require_login: true  // 新增
})
```

- [ ] **步骤 4：Commit**

```bash
git add frontend/src/views/Software/List.vue frontend/src/views/Software/Detail.vue
git commit -m "feat: 新建/编辑软件表单添加 require_login 开关"
```

---

## 自检清单

- [ ] 规格中每个需求都有对应任务
- [ ] 无占位符（TODO/待定/后续实现）
- [ ] 字段名在所有任务中一致（require_login, original_download_url, allow_guest_access, allowGuestAccess）
- [ ] API 路由变更正确（get_optional_current_user）
- [ ] 前端字段名正确（allow_guest_access ↔ allowGuestAccess）

---

## 执行选项

计划已完成并保存到 `docs/superpowers/plans/2026-06-08-guest-access-software-permission-plan.md`。

**推荐执行方式：子代理驱动（subagent-driven-development）**

由于任务间存在依赖关系（任务 1→2→3→4→5 的后端链，任务 7→8→9→10→11→12→13 的前端链），建议：
1. 首先并行执行任务 1-2（后端基础）
2. 然后执行任务 3-6（后端 API）
3. 然后执行任务 7-9（前端配置和路由）
4. 最后执行任务 10-13（前端业务逻辑）

**请选择执行方式：**
- **A. 子代理驱动（推荐）** - 每个任务调度新子代理，任务间有审查
- **B. 内联执行** - 当前会话批量执行，设有检查点
