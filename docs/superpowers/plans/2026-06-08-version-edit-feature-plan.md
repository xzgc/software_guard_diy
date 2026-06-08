# 软件版本编辑功能实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为 Software Guard 添加软件版本的编辑功能，admin 可修改版本号、release_notes、external_url，并支持文件覆盖/删除

**架构：** 后端新增 PUT 端点（仅 admin）支持 multipart/form-data 接受新文件；前端版本表格新增编辑按钮，复用上传版本弹窗支持编辑模式

**技术栈：** FastAPI + SQLAlchemy + Vue 3 + Ant Design Vue

---

## 文件结构

| 职责 | 文件 |
|------|------|
| Schema | `backend/app/schemas/software.py` |
| 软件API | `backend/app/api/software.py` |
| 前端API Client | `frontend/src/api/software.js` |
| 软件详情页 | `frontend/src/views/Software/Detail.vue` |

---

## 任务清单

### 任务 1：后端 — Schema 添加 SoftwareVersionUpdate

**文件：**
- 修改：`backend/app/schemas/software.py:60-80`

- [ ] **步骤 1：查看现有 Schema 文件中版本相关定义**

运行：`grep -n "SoftwareVersion\|VersionInfo" /root/dockerProjectDir/software_guard/backend/app/schemas/software.py`

- [ ] **步骤 2：在 `SoftwareVersionCreate` 之后添加 `SoftwareVersionUpdate` 类**

```python
class SoftwareVersionUpdate(BaseModel):
    """版本编辑请求 Schema"""
    version: Optional[str] = Field(None, min_length=1, max_length=50)
    release_notes: Optional[str] = None
    external_url: Optional[str] = None
```

- [ ] **步骤 3：验证 Python 语法**

运行：`cd /root/dockerProjectDir/software_guard/backend && python -m py_compile app/schemas/software.py`
预期：编译通过，无输出

- [ ] **步骤 4：Commit**

```bash
git add backend/app/schemas/software.py
git commit -m "feat: 添加 SoftwareVersionUpdate Schema"
```

---

### 任务 2：后端 — 添加 PUT 版本编辑端点

**文件：**
- 修改：`backend/app/api/software.py`

- [ ] **步骤 1：查看 delete_software_version 函数的完整位置作为参考**

运行：`grep -n "delete_software_version\|@router.delete" /root/dockerProjectDir/software_guard/backend/app/api/software.py`

- [ ] **步骤 2：导入依赖项**

在文件顶部添加 `require_admin` 到现有导入：

```python
from ..core.deps import get_current_active_user, get_optional_current_user, require_ops, require_admin
```

- [ ] **步骤 3：在 delete_software_version 函数之前添加 update_version 端点**

```python
@router.put("/{software_id}/versions/{version_id}", response_model=SoftwareVersionResponse)
async def update_version(
    software_id: int,
    version_id: int,
    version: Optional[str] = Form(None),
    release_notes: Optional[str] = Form(None),
    external_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    delete_file: bool = Form(False),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """编辑软件版本（仅 admin）"""
    software = db.query(Software).filter(Software.id == software_id).first()
    if not software:
        raise HTTPException(status_code=404, detail="软件不存在")

    ver = db.query(SoftwareVersion).filter(
        SoftwareVersion.id == version_id,
        SoftwareVersion.software_id == software_id
    ).first()
    if not ver:
        raise HTTPException(status_code=404, detail="版本不存在")

    # 如果修改了版本号，检查唯一性
    if version and version != ver.version:
        existing = db.query(SoftwareVersion).filter(
            SoftwareVersion.software_id == software_id,
            SoftwareVersion.version == version,
            SoftwareVersion.id != version_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="版本号已被其他版本占用")
        ver.version = version

    # 更新 release_notes
    if release_notes is not None:
        ver.release_notes = release_notes

    # 处理文件
    if file:
        # 上传新文件：覆盖原文件
        file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ''
        if file_ext not in ALLOWED_UPLOAD_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}，允许的类型: {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}"
            )

        safe_filename = sanitize_filename(file.filename)
        storage_path = get_storage_path(db)
        software_dir = os.path.join(storage_path, str(software_id))
        os.makedirs(software_dir, exist_ok=True)
        file_path = validate_path_within_dir(os.path.join(software_dir, safe_filename), storage_path)

        sha256_hash = hashlib.sha256()
        file_size = 0
        chunk_size = 1024 * 1024
        async with aiofiles.open(file_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > get_max_upload_size(db):
                    await f.close()
                    os.remove(file_path)
                    raise HTTPException(status_code=400, detail="文件大小超过限制")
                sha256_hash.update(chunk)
                await f.write(chunk)

        ver.file_path = file_path
        ver.file_name = safe_filename
        ver.file_size = file_size
        ver.file_hash = sha256_hash.hexdigest()
    elif delete_file and ver.file_path:
        # 显式删除文件
        try:
            if os.path.exists(ver.file_path):
                os.remove(ver.file_path)
        except Exception:
            pass
        ver.file_path = ""
        ver.file_name = ""
        ver.file_size = 0
        ver.file_hash = ""

    # 更新 external_url
    if external_url is not None:
        url_value = external_url.strip() if external_url.strip() else None
        ver.original_download_url = url_value

    db.commit()
    db.refresh(ver)

    return SoftwareVersionResponse(
        id=ver.id,
        software_id=ver.software_id,
        version=ver.version,
        file_name=ver.file_name,
        file_size=ver.file_size,
        file_hash=ver.file_hash,
        upload_time=ver.upload_time,
        download_count=ver.download_count,
        release_notes=ver.release_notes,
        software_name=software.name
    )
```

- [ ] **步骤 4：验证 Python 语法**

运行：`cd /root/dockerProjectDir/software_guard/backend && python -m py_compile app/api/software.py`
预期：编译通过，无输出

- [ ] **步骤 5：Commit**

```bash
git add backend/app/api/software.py
git commit -m "feat: 添加 PUT 版本编辑端点（仅 admin）"
```

---

### 任务 3：前端 — API Client 添加 updateVersion 方法

**文件：**
- 修改：`frontend/src/api/software.js`

- [ ] **步骤 1：在 `deleteVersion` 之后添加 `updateVersion` 方法**

```javascript
// 编辑软件版本（仅 admin）
updateVersion(softwareId, versionId, formData, onUploadProgress) {
  return api.put(`/software/${softwareId}/versions/${versionId}`, formData, {
    timeout: 0,
    onUploadProgress
  })
},
```

- [ ] **步骤 2：验证文件存在（语法由 Vite 验证）**

运行：`cat /root/dockerProjectDir/software_guard/frontend/src/api/software.js | head -50`

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/api/software.js
git commit -m "feat: API client 添加 updateVersion 方法"
```

---

### 任务 4：前端 — Detail.vue 复用上传版本弹窗支持编辑模式

**文件：**
- 修改：`frontend/src/views/Software/Detail.vue`

- [ ] **步骤 1：添加 ref 变量**

在 `logoTab` 定义之后添加：

```javascript
const isEditVersionMode = ref(false)
const editingVersionId = ref(null)
```

- [ ] **步骤 2：在 script 区域添加 `openEditVersionModal` 和 `handleUpdateVersion` 函数**

```javascript
const openEditVersionModal = (version) => {
  isEditVersionMode.value = true
  editingVersionId.value = version.id
  versionForm.value = {
    version: version.version,
    release_notes: version.release_notes || '',
    external_url: version.original_download_url || ''
  }
  versionTab.value = version.original_download_url ? 'url' : 'upload'
  fileList.value = []
  uploadProgress.value = 0
  uploadStatus.value = 'active'
  uploadDetailText.value = ''
  showVersionModal.value = true
}

const handleUpdateVersion = async () => {
  if (!versionForm.value.version) {
    message.error('请填写版本号')
    return
  }

  uploadLoading.value = true
  try {
    const formData = new FormData()
    formData.append('version', versionForm.value.version)
    formData.append('release_notes', versionForm.value.release_notes || '')
    if (versionForm.value.external_url) {
      formData.append('external_url', versionForm.value.external_url)
    }
    if (fileList.value.length > 0) {
      formData.append('file', fileList.value[0])
    }

    await softwareApi.updateVersion(route.params.id, editingVersionId.value, formData)
    message.success('版本更新成功')
    showVersionModal.value = false
    resetUploadForm()
    isEditVersionMode.value = false
    editingVersionId.value = null
    loadDetail()
  } catch (error) {
    message.error('版本更新失败: ' + (error.response?.data?.detail || '未知错误'))
  } finally {
    uploadLoading.value = false
  }
}
```

- [ ] **步骤 3：修改模板中的弹窗标题为动态**

将弹窗的 `title` 属性改为：

```vue
<a-modal
  v-model:open="showVersionModal"
  :title="isEditVersionMode ? '编辑版本' : '上传新版本'"
  @ok="isEditVersionMode ? handleUpdateVersion : handleUploadVersion"
  :confirm-loading="uploadLoading"
  :ok-button-props="{ disabled: uploading }"
  :maskClosable="false"
  :keyboard="false"
  width="650px"
>
```

- [ ] **步骤 4：在版本表格的 actions 列中、删除按钮之前添加编辑按钮**

找到 actions 模板区域，添加：

```vue
<a-button
  v-if="userStore.isAdmin()"
  type="link"
  size="small"
  @click="openEditVersionModal(record)"
>
  <EditOutlined /> 编辑
</a-button>
```

- [ ] **步骤 5：Commit**

```bash
git add frontend/src/views/Software/Detail.vue
git commit -m "feat: Detail.vue 版本编辑按钮和编辑模式弹窗"
```

---

## 自检清单

- [x] 规格中每个需求都有对应任务
- [x] 无占位符
- [x] 字段名一致（SoftwareVersionUpdate, updateVersion, isEditVersionMode）
- [x] API 路由正确（PUT /api/software/{sw_id}/versions/{vid}）
- [x] 前端权限正确（userStore.isAdmin()）

---

## 执行选项

计划已完成并保存到 `docs/superpowers/plans/2026-06-08-version-edit-feature-plan.md`。

**推荐执行方式：内联执行**

由于只有 4 个任务且相对独立，建议：
- 当前会话中使用 `executing-plans` 批量执行
- 每个任务完成后立即 commit 验证
- 任务间无需复杂审查

**请选择执行方式：**
- **A. 子代理驱动** - 每个任务调度新子代理，任务间有审查
- **B. 内联执行** - 当前会话批量执行
