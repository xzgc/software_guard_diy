# 软件权限与游客访问功能设计

## 概述

为 Software Guard 添加以下功能：
1. 软件级别下载权限控制（是否需要登录）
2. 游客访问支持（配置开关）
3. 版本上传支持外部下载地址
4. 下载地址 Fallback 逻辑（版本地址 → 软件官网地址）

---

## 1. 数据模型变更

### 1.1 Software 模型新增字段

文件：`backend/app/models/software.py`

```python
class Software(Base):
    # ... 现有字段 ...
    require_login: bool = Column(Boolean, default=True, nullable=False)
    # 是否需要登录才能下载，默认 True（需要登录）
```

### 1.2 SoftwareVersion 模型新增字段

文件：`backend/app/models/software.py`

```python
class SoftwareVersion(Base):
    # ... 现有字段 ...
    original_download_url: str = Column(String(500), nullable=True)
    # 外部下载地址（可选），优先级高于实际上传文件
```

---

## 2. API 变更

### 2.1 软件列表/详情 API — 支持游客访问

变更文件：`backend/app/api/software.py`

| 接口 | 原认证 | 新认证 |
|------|--------|--------|
| `GET /api/software` | `get_current_active_user` | `get_optional_current_user` |
| `GET /api/software/{id}` | `get_current_active_user` | `get_optional_current_user` |

### 2.2 下载 API — 细粒度权限检查

变更文件：`backend/app/api/download.py`

```python
@router.get("/{version_id}")
async def download_software(
    version_id: int,
    request: Request,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    # 1. 获取版本信息和所属软件的 require_login 字段
    # 2. 如果 require_login=True 且 current_user is None，返回 401
    # 3. 如果有 original_download_url，返回 URL 重定向或 JSON
    # 4. 否则返回文件流
```

### 2.3 站点信息 API — 新增配置字段

变更文件：`backend/main.py`

```python
@app.get("/api/site/info")
async def site_info(db=Depends(get_db)):
    allow_guest_cfg = db.query(Config).filter(Config.key == "allow_guest_access").first()
    return {
        "name": ...,
        "description": ...,
        "allow_guest_access": allow_guest_cfg.value == "true" if allow_guest_cfg else True
    }
```

### 2.4 版本上传 API — 支持外部地址

变更文件：`backend/app/api/software.py`

`POST /api/software/{software_id}/versions` 新增参数：
```python
class VersionCreate:
    version: str
    release_notes: str | None = None
    file: UploadFile | None = None  # 现有
    external_url: str | None = None  # 新增：外部下载地址
```

---

## 3. Schema 变更

### 3.1 SoftwareCreate / SoftwareUpdate

新增 `require_login` 字段。

### 3.2 SoftwareResponse

返回 `require_login` 字段。

### 3.3 VersionCreate / VersionInfo

新增 `original_download_url` 字段。

---

## 4. 前端变更

### 4.1 配置页面 — 安全配置卡片

文件：`frontend/src/views/Admin/Config.vue`

在"安全配置"卡片中添加：
```vue
<a-form-item label="允许游客访问">
  <a-switch v-model="configForm.allow_guest_access" />
</a-form-item>
```

### 4.2 Site Store

文件：`frontend/src/stores/site.js`

新增 `allowGuestAccess` 字段，从 `/api/site/info` 读取。

### 4.3 路由守卫

文件：`frontend/src/router/index.js`

```javascript
if (to.meta.requiresAuth && !userStore.token && !siteStore.allowGuestAccess) {
    next('/login')
}
```

### 4.4 软件列表页 — 根据权限显示

文件：`frontend/src/views/Software/List.vue`

下载按钮逻辑：
- 如果 `require_login=True`：游客看到"登录后下载"，登录用户直接下载
- 如果 `require_login=False`：游客可直接下载

### 4.5 软件详情页 — 版本上传 Tab 切换

文件：`frontend/src/views/Software/Detail.vue`

上传版本弹窗改为 Tab 切换：
```
[上传文件] | [提供下载地址]
```

- Tab 1：现有文件上传逻辑
- Tab 2：显示 `a-input` 让管理员输入 external_url

### 4.6 下载按钮/链接逻辑

文件：`frontend/src/views/Software/Detail.vue`

```javascript
const getDownloadLink = (version) => {
    if (version.original_download_url) {
        return version.original_download_url
    }
    return software.value.official_url  // fallback
}
```

---

## 5. 数据库迁移

启动时自动迁移（现有机制）已覆盖：
- Software 表添加 `require_login` 列
- SoftwareVersion 表添加 `original_download_url` 列

---

## 6. 配置默认值

| 配置 Key | 默认值 | 说明 |
|----------|--------|------|
| `allow_guest_access` | `true` | 默认允许游客访问 |
| `require_login` | `true` | 默认需要登录才能下载 |

---

## 7. 实施顺序

1. **后端模型** — 添加 `require_login` 和 `original_download_url` 字段
2. **后端 Schema** — 添加对应字段
3. **后端 API** — 软件列表/详情支持游客访问
4. **后端下载 API** — 实现 `require_login` 检查 + external_url
5. **后端站点 API** — 返回 `allow_guest_access`
6. **前端配置页** — 添加 `allow_guest_access` 开关
7. **前端 Store** — siteStore 新增 `allowGuestAccess`
8. **前端路由守卫** — 支持游客访问
9. **前端版本上传** — Tab 切换 + external_url
10. **前端下载逻辑** — external_url + fallback 逻辑
