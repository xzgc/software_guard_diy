# 软件版本编辑功能设计

## 概述

为 Software Guard 添加软件版本编辑功能：
1. 在软件详情页版本表格中新增"编辑"按钮（仅 admin 可见）
2. 后端新增 PUT 接口支持编辑版本的全部字段
3. 支持编辑时上传新文件覆盖原文件，或修改外部下载地址
4. 文件不会被自动删除，除非用户显式触发

---

## 1. 数据模型

无需修改模型，复用现有 `SoftwareVersion` 模型的所有字段。

---

## 2. API 变更

### 2.1 Schema 新增

文件：`backend/app/schemas/software.py`

```python
class SoftwareVersionUpdate(BaseModel):
    """版本编辑的请求 Schema"""
    version: Optional[str] = None
    release_notes: Optional[str] = None
    external_url: Optional[str] = None
```

注：文件通过 multipart/form-data 上传，不在 Pydantic Schema 中体现。

### 2.2 新增 PUT 端点

文件：`backend/app/api/software.py`

```python
@router.put("/{software_id}/versions/{version_id}", response_model=SoftwareVersionResponse)
async def update_version(
    software_id: int,
    version_id: int,
    version: Optional[str] = Form(None),
    release_notes: Optional[str] = Form(None),
    external_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    delete_file: bool = Form(False),  # 显式删除文件标志
    current_user: User = Depends(require_admin),  # 仅 admin
    db: Session = Depends(get_db)
):
    """编辑软件版本（仅 admin）"""
    # 1. 验证软件和版本存在
    # 2. 如果修改了 version 字段，检查唯一性
    # 3. 如果上传新文件：覆盖原文件（复用 file_path），更新 file_size/file_hash
    # 4. 如果 delete_file=True：删除磁盘文件，file_path/file_size/file_hash 置空
    # 5. 如果提供 external_url：更新 original_download_url（允许空字符串清空）
    # 6. 更新其他元数据
    # 7. 下载计数 download_count 保持不变
```

### 2.3 权限：仅 admin

- 使用 `require_admin` 依赖（仅 `UserRole.ADMIN`）
- 与现有 `require_ops` 的上传版本不同，编辑版本更严格

### 2.4 文件覆盖策略

- **上传新文件**：使用原 `file_path` 路径覆盖写入，更新 `file_size`、`file_hash`、`file_name`
- **delete_file=True**：删除磁盘文件，`file_path/file_size/file_hash/file_name` 全部置空
- **不传 file 且 delete_file=False**：原文件保持不变

### 2.5 模式切换

- 允许从"文件模式"切换到"URL 模式"（不清除原文件，仅更新 `original_download_url`）
- 允许从"URL 模式"切换到"文件模式"（上传新文件）
- 原文件/原 URL 都保留在数据库中，直到显式清除

---

## 3. 前端变更

### 3.1 前端 API Client

文件：`frontend/src/api/software.js`

新增 `updateVersion(softwareId, versionId, formData)` 方法。

### 3.2 Detail.vue 版本表格

文件：`frontend/src/views/Software/Detail.vue`

**新增编辑按钮**：
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

**编辑弹窗**：复用现有的"上传版本"弹窗，扩展为支持编辑模式。

### 3.3 编辑弹窗状态

新增 ref：
- `isEditVersionMode = ref(false)` — 是否为编辑模式
- `editingVersionId = ref(null)` — 当前编辑的版本 ID

### 3.4 弹窗复用

将现有的 `showVersionModal` 弹窗改造为支持创建/编辑两种模式：

```
[标题] 上传新版本 / 编辑版本

模式选择（仅创建模式可见）: [上传文件 | 提供下载地址]

[创建/保存]
```

### 3.5 打开编辑弹窗

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
  showVersionModal.value = true
}
```

### 3.6 提交编辑

```javascript
const handleUpdateVersion = async () => {
  const formData = new FormData()
  if (versionForm.value.version) formData.append('version', versionForm.value.version)
  if (versionForm.value.release_notes !== undefined) {
    formData.append('release_notes', versionForm.value.release_notes || '')
  }
  if (versionForm.value.external_url) {
    formData.append('external_url', versionForm.value.external_url)
  }
  if (fileList.value.length > 0) {
    formData.append('file', fileList.value[0])
  }
  await softwareApi.updateVersion(route.params.id, editingVersionId.value, formData)
  message.success('版本更新成功')
  // 关闭弹窗、刷新详情
}
```

### 3.7 删除文件按钮

在文件 Tab 中，如果当前有文件（`editingVersionId` 对应版本有 `file_path`），显示"删除文件"按钮：

```vue
<a-button v-if="hasExistingFile" danger @click="onDeleteFile">
  删除文件
</a-button>
```

提交时附带 `delete_file=true`。

---

## 4. 实施顺序

1. **后端 Schema** — 添加 `SoftwareVersionUpdate`
2. **后端 API** — 添加 PUT 端点
3. **前端 API Client** — 添加 `updateVersion` 方法
4. **前端 Detail.vue** — 编辑按钮、编辑弹窗、删除文件按钮
5. **测试 + 部署**

---

## 5. 配置默认值

无新增配置项。

---

## 6. 风险点

1. **修改版本号** — 已下载用户可能找不到原版本，但用户明确要求支持
2. **文件覆盖** — 一旦上传新文件，原文件内容被覆盖（不可恢复）
3. **下载统计保留** — 编辑时 `download_count` 保持不变（保护历史数据）
4. **API 兼容性** — POST 接口保持不变，新接口为 PUT
