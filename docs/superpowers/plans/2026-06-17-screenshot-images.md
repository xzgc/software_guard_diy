# 软件界面图（截图）功能 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为 Software Guard 添加软件界面图管理功能，每个软件最多 3 张图片，支持本地文件上传或外部 URL 输入，详情页版本列表下方展示缩略图。

**架构：** 在 Software 模型新增 3 个 String 字段，后端仿照 logo 端点新增 POST/DELETE/GET file 3 个端点，前端在编辑软件弹窗中提供 3 槽位独立管理 UI，详情页用 `a-image-preview-group` 展示缩略图。

**技术栈：** FastAPI（multipart/form-data）、SQLAlchemy（自动迁移）、Vue 3（Ant Design Vue、Pinia）、aiofiles（异步文件写入）。

**规格文档：** `docs/superpowers/specs/2026-06-17-screenshot-images-design.md`

---

## 任务 1：模型与数据库迁移

**文件：**
- 修改：`backend/app/models/software.py:7-27`
- 修改：`backend/main.py`（lifespan 函数中的 auto-migration 段）

- [ ] **步骤 1：在 Software 模型新增 3 个字段**

打开 `backend/app/models/software.py`，在 `Software` 类（约第 18 行 `require_login` 之后、第 19 行 `created_by` 之前）插入：

```python
    screenshot_url_1 = Column(String(500), nullable=True)  # 软件界面图 1
    screenshot_url_2 = Column(String(500), nullable=True)  # 软件界面图 2
    screenshot_url_3 = Column(String(500), nullable=True)  # 软件界面图 3
```

- [ ] **步骤 2：在 main.py lifespan 追加自迁移 SQL**

打开 `backend/main.py`，找到 lifespan 函数中已有的 `ALTER TABLE software ADD COLUMN IF NOT EXISTS require_login ...` 段（参考同文件内 `auth_source` / `token_version` 的迁移模式）。在 `require_login` 的 ALTER 之后追加 3 条：

```python
            # 软件界面图字段迁移
            conn.execute(text("ALTER TABLE software ADD COLUMN IF NOT EXISTS screenshot_url_1 VARCHAR(500)"))
            conn.execute(text("ALTER TABLE software ADD COLUMN IF NOT EXISTS screenshot_url_2 VARCHAR(500)"))
            conn.execute(text("ALTER TABLE software ADD COLUMN IF NOT EXISTS screenshot_url_3 VARCHAR(500)"))
            conn.commit()
```

（注意：具体位置需参考 main.py 现有迁移段结构——可能是用 `text()` + `conn.execute` 也可能是 `op.execute()`。按文件实际风格嵌入。）

- [ ] **步骤 3：Commit**

```bash
cd /root/dockerProjectDir/software_guard
git add backend/app/models/software.py backend/main.py
git commit -m "feat(model): 新增软件界面图字段 screenshot_url_1/2/3"
```

---

## 任务 2：Pydantic Schema 扩展

**文件：**
- 修改：`backend/app/schemas/software.py`

- [ ] **步骤 1：在 SoftwareBase 新增 3 个字段**

打开 `backend/app/schemas/software.py`，找到 `SoftwareBase` 类（约第 7-29 行），在 `require_login` 字段之后插入：

```python
    screenshot_url_1: Optional[str] = None  # 软件界面图 1
    screenshot_url_2: Optional[str] = None  # 软件界面图 2
    screenshot_url_3: Optional[str] = None  # 软件界面图 3
```

- [ ] **步骤 2：在 SoftwareUpdate 新增 3 个字段**

找到 `SoftwareUpdate` 类（约第 36-58 行），在 `require_login` 字段之后插入相同的 3 行。

- [ ] **步骤 3：在 SoftwareResponse 确认字段自动映射**

`SoftwareResponse` 继承 `SoftwareBase` 并设置 `from_attributes = True`，新增字段会自动出现在响应中。无需手动添加。

- [ ] **步骤 4：在 SoftwareListResponse 新增 3 个字段**

找到 `SoftwareListResponse` 类（约第 116-130 行），在 `require_login` 字段之后插入：

```python
    screenshot_url_1: Optional[str] = None
    screenshot_url_2: Optional[str] = None
    screenshot_url_3: Optional[str] = None
```

- [ ] **步骤 5：更新 list_software endpoint 返回这 3 个字段**

打开 `backend/app/api/software.py`，找到 `list_software` 函数（约第 67-79 行的 `SoftwareListResponse(...)` 构造），在 `require_login=...` 之后插入：

```python
            screenshot_url_1=sw.screenshot_url_1,
            screenshot_url_2=sw.screenshot_url_2,
            screenshot_url_3=sw.screenshot_url_3,
```

- [ ] **步骤 6：Commit**

```bash
cd /root/dockerProjectDir/software_guard
git add backend/app/schemas/software.py backend/app/api/software.py
git commit -m "feat(schema): Software Schema 新增 screenshot_url_1/2/3 字段"
```

---

## 任务 3：后端 API - 上传/设置截图端点

**文件：**
- 修改：`backend/app/api/software.py`

- [ ] **步骤 1：新增 POST /{software_id}/screenshots 端点**

在 `backend/app/api/software.py` 中找到 `upload_logo` 函数（约第 377-433 行）作为参考。在 `upload_logo` 之前（或文件末尾的合适位置）插入新端点：

```python
@router.post("/{software_id}/screenshots")
async def upload_screenshot(
    software_id: int,
    slot: int = Form(..., ge=1, le=3),
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    current_user: User = Depends(require_ops),
    db: Session = Depends(get_db)
):
    """上传/设置软件界面图（slot 1/2/3）"""
    software = db.query(Software).filter(Software.id == software_id).first()
    if not software:
        raise HTTPException(status_code=404, detail="软件不存在")

    if not file and not (url and url.strip()):
        raise HTTPException(status_code=400, detail="请提供文件或图片URL")

    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'}
    max_size = 5 * 1024 * 1024  # 5MB

    # 文件模式
    if file:
        file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ''
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的图片类型: {file_ext}，允许的类型: {', '.join(sorted(allowed_extensions))}"
            )

        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(status_code=400, detail="图片大小不能超过5MB")

        import uuid
        unique_filename = f"{software_id}_s{slot}_{uuid.uuid4().hex[:8]}{file_ext}"
        storage_path = get_storage_path(db)
        screenshot_dir = os.path.join(storage_path, "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        file_path = os.path.join(screenshot_dir, unique_filename)

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # 删除该槽位旧的本地文件（如果旧值是本地路径）
        old_url = getattr(software, f"screenshot_url_{slot}")
        if old_url and old_url.startswith("/api/software/"):
            old_filename = old_url.split("/")[-1]
            old_path = os.path.join(screenshot_dir, old_filename)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception:
                    pass

        new_url = f"/api/software/{software_id}/screenshots/file/{unique_filename}"
        setattr(software, f"screenshot_url_{slot}", new_url)
        db.commit()

        return {
            "screenshot_url": new_url,
            "slot": slot,
            "message": "截图上传成功"
        }

    # URL 模式
    url_value = url.strip()
    old_url = getattr(software, f"screenshot_url_{slot}")
    if old_url and old_url.startswith("/api/software/"):
        old_filename = old_url.split("/")[-1]
        storage_path = get_storage_path(db)
        old_path = os.path.join(storage_path, "screenshots", old_filename)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass

    setattr(software, f"screenshot_url_{slot}", url_value)
    db.commit()

    return {
        "screenshot_url": url_value,
        "slot": slot,
        "message": "截图URL设置成功"
    }
```

- [ ] **步骤 2：Commit**

```bash
cd /root/dockerProjectDir/software_guard
git add backend/app/api/software.py
git commit -m "feat(api): 新增 POST /software/{id}/screenshots 端点"
```

---

## 任务 4：后端 API - 删除截图端点

**文件：**
- 修改：`backend/app/api/software.py`

- [ ] **步骤 1：新增 DELETE /{software_id}/screenshots/{slot} 端点**

在 `upload_screenshot` 端点之后插入：

```python
@router.delete("/{software_id}/screenshots/{slot}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_screenshot(
    software_id: int,
    slot: int,
    current_user: User = Depends(require_ops),
    db: Session = Depends(get_db)
):
    """删除软件界面图（slot 1/2/3）"""
    if slot not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="slot 必须是 1/2/3")

    software = db.query(Software).filter(Software.id == software_id).first()
    if not software:
        raise HTTPException(status_code=404, detail="软件不存在")

    old_url = getattr(software, f"screenshot_url_{slot}")
    if old_url and old_url.startswith("/api/software/"):
        old_filename = old_url.split("/")[-1]
        storage_path = get_storage_path(db)
        screenshot_dir = os.path.join(storage_path, "screenshots")
        old_path = os.path.join(screenshot_dir, old_filename)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass

    setattr(software, f"screenshot_url_{slot}", None)
    db.commit()

    return None
```

- [ ] **步骤 2：Commit**

```bash
cd /root/dockerProjectDir/software_guard
git add backend/app/api/software.py
git commit -m "feat(api): 新增 DELETE /software/{id}/screenshots/{slot} 端点"
```

---

## 任务 5：后端 API - 获取截图文件端点

**文件：**
- 修改：`backend/app/api/software.py`

- [ ] **步骤 1：新增 GET /{software_id}/screenshots/file/{filename} 端点**

参考 `get_logo_file`（约第 436-457 行），在 `get_logo_file_direct` 之后插入：

```python
@router.get("/{software_id}/screenshots/file/{filename}")
async def get_screenshot_file(
    software_id: int,
    filename: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """获取界面图文件（支持游客访问）"""
    from fastapi.responses import FileResponse

    software = db.query(Software).filter(Software.id == software_id).first()
    if not software:
        raise HTTPException(status_code=404, detail="软件不存在")

    safe_name = sanitize_filename(filename)
    storage_path = get_storage_path(db)
    screenshot_dir = os.path.join(storage_path, "screenshots")
    file_path = validate_path_within_dir(os.path.join(screenshot_dir, safe_name), screenshot_dir)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="截图文件不存在")

    return FileResponse(file_path)
```

- [ ] **步骤 2：Commit**

```bash
cd /root/dockerProjectDir/software_guard
git add backend/app/api/software.py
git commit -m "feat(api): 新增 GET /software/{id}/screenshots/file/{filename} 端点"
```

---

## 任务 6：后端重启与 curl 测试

**文件：**
- 无（仅测试）

- [ ] **步骤 1：重启后端服务**

```bash
cd /root/dockerProjectDir/software_guard
docker compose restart app
```

或：

```bash
cd /root/dockerProjectDir/software_guard/backend
uv run python main.py
```

- [ ] **步骤 2：验证数据库字段已添加**

```bash
docker compose exec postgres psql -U postgres -d software_guard -c "\d software"
```

预期输出包含 `screenshot_url_1` / `screenshot_url_2` / `screenshot_url_3` 三个 VARCHAR(500) 列。

- [ ] **步骤 3：测试上传文件（替换 <TOKEN> 为 admin token）**

```bash
# 准备测试图片
echo "fake png content" > /tmp/test_screenshot.png

curl -X POST http://localhost:8000/api/software/1/screenshots \
  -H "Authorization: Bearer <TOKEN>" \
  -F "slot=1" \
  -F "file=@/tmp/test_screenshot.png"
```

预期：返回 `{"screenshot_url": "/api/software/1/screenshots/file/1_s1_xxxxxxxx.png", "slot": 1, "message": "截图上传成功"}`

- [ ] **步骤 4：验证磁盘文件已创建**

```bash
ls -la backend/storage/screenshots/ 2>/dev/null || docker compose exec app ls -la storage/screenshots/
```

预期：存在 `1_s1_xxxxxxxx.png` 文件。

- [ ] **步骤 5：测试 URL 模式**

```bash
curl -X POST http://localhost:8000/api/software/1/screenshots \
  -H "Authorization: Bearer <TOKEN>" \
  -F "slot=2" \
  -F "url=https://example.com/img.png"
```

预期：返回 `{"screenshot_url": "https://example.com/img.png", "slot": 2, "message": "截图URL设置成功"}`

- [ ] **步骤 6：测试删除**

```bash
curl -X DELETE http://localhost:8000/api/software/1/screenshots/1 \
  -H "Authorization: Bearer <TOKEN>" \
  -w "%{http_code}\n"
```

预期：返回 `204`

- [ ] **步骤 7：验证 DB 字段为 NULL、磁盘文件已删除**

```bash
docker compose exec postgres psql -U postgres -d software_guard -c "SELECT id, screenshot_url_1, screenshot_url_2, screenshot_url_3 FROM software WHERE id=1;"
```

预期：`screenshot_url_1` 为 NULL，其他字段保持。

- [ ] **步骤 8：测试 slot 越界**

```bash
curl -X POST http://localhost:8000/api/software/1/screenshots \
  -H "Authorization: Bearer <TOKEN>" \
  -F "slot=4"
```

预期：422 Unprocessable Entity

- [ ] **步骤 9：测试游客访问截图文件**

重新上传一张图（步骤 3），然后不带 token 访问：

```bash
curl -I http://localhost:8000/api/software/1/screenshots/file/1_s1_xxxxxxxx.png
```

预期：HTTP/1.1 200 OK

---

## 任务 7：前端 API Client 扩展

**文件：**
- 修改：`frontend/src/api/software.js`

- [ ] **步骤 1：新增 uploadScreenshot 方法**

打开 `frontend/src/api/software.js`，在 `uploadLogo` 方法之后追加：

```javascript
  // 上传/设置软件界面图
  uploadScreenshot(softwareId, slot, formData) {
    return api.post(`/software/${softwareId}/screenshots`, formData)
  },

  // 删除软件界面图
  deleteScreenshot(softwareId, slot) {
    return api.delete(`/software/${softwareId}/screenshots/${slot}`)
  }
```

（注意：把 `uploadLogo` 函数末尾的闭合 `}` 后的方法之间加上逗号，且 `uploadLogo` 改为不以逗号结尾，`uploadScreenshot` / `deleteScreenshot` 是 softwareApi 对象的最后两个属性。）

完整 `softwareApi` 对象结构参考：

```javascript
export const softwareApi = {
  list(params) { ... },
  getDetail(id) { ... },
  create(data) { ... },
  update(id, data) { ... },
  delete(id) { ... },
  uploadVersion(softwareId, data, onUploadProgress) { ... },
  deleteVersion(softwareId, versionId) { ... },
  updateVersion(softwareId, versionId, formData, onUploadProgress) { ... },
  getCategories() { ... },
  getDownloadLogs(versionId) { ... },
  uploadLogo(softwareId, file) { ... },
  uploadScreenshot(softwareId, slot, formData) { ... },
  deleteScreenshot(softwareId, slot) { ... }
}
```

- [ ] **步骤 2：Commit**

```bash
cd /root/dockerProjectDir/software_guard
git add frontend/src/api/software.js
git commit -m "feat(frontend): 新增 uploadScreenshot / deleteScreenshot API 方法"
```

---

## 任务 8：前端编辑弹窗 - 截图管理卡片

**文件：**
- 修改：`frontend/src/views/Software/Detail.vue`

- [ ] **步骤 1：新增 ref 状态变量**

打开 `frontend/src/views/Software/Detail.vue`，找到 `<script setup>` 中的现有 ref 声明区域（参考 `logoTab`、`logoUrlInput` 等 ref 的位置）。在 `logoTab` ref 附近追加：

```javascript
// 软件界面图状态（3 个槽位）
const screenshotTabs = ref(['', '', ''])  // 每个 slot 当前激活的 tab
const screenshotUrlInputs = ref(['', '', ''])  // 每个 slot 的 URL 输入
const screenshotLoading = ref([false, false, false])  // 每个 slot 的 loading
```

- [ ] **步骤 2：新增 3 个处理函数**

在 `handleFileUpload` / `handleUrlUpload` 等 logo 相关函数附近（参考 `frontend/src/views/Software/Detail.vue` 中现有的 logo 处理函数）追加：

```javascript
// ============= 软件界面图相关 =============

const handleDeleteScreenshot = async (slot) => {
  screenshotLoading.value[slot - 1] = true
  try {
    await softwareApi.deleteScreenshot(route.params.id, slot)
    message.success('截图已删除')
    await loadDetail()
  } catch (e) {
    message.error('删除失败：' + (e.response?.data?.detail || e.message))
  } finally {
    screenshotLoading.value[slot - 1] = false
  }
}

const handleUrlScreenshot = async (slot) => {
  const url = screenshotUrlInputs.value[slot - 1].trim()
  if (!url) {
    message.warning('请输入图片URL')
    return
  }
  screenshotLoading.value[slot - 1] = true
  try {
    const formData = new FormData()
    formData.append('slot', slot)
    formData.append('url', url)
    await softwareApi.uploadScreenshot(route.params.id, slot, formData)
    message.success('截图已设置')
    screenshotUrlInputs.value[slot - 1] = ''
    await loadDetail()
  } catch (e) {
    message.error('设置失败：' + (e.response?.data?.detail || e.message))
  } finally {
    screenshotLoading.value[slot - 1] = false
  }
}

const handleFileScreenshot = async (file, slot) => {
  const isImage = /\.(png|jpg|jpeg|gif|svg|webp)$/i.test(file.name)
  if (!isImage) {
    message.error('仅支持 png/jpg/jpeg/gif/svg/webp 格式')
    return false
  }
  const isLt5M = file.size / 1024 / 1024 < 5
  if (!isLt5M) {
    message.error('图片大小不能超过 5MB')
    return false
  }
  screenshotLoading.value[slot - 1] = true
  try {
    const formData = new FormData()
    formData.append('slot', slot)
    formData.append('file', file)
    await softwareApi.uploadScreenshot(route.params.id, slot, formData)
    message.success('截图上传成功')
    await loadDetail()
  } catch (e) {
    message.error('上传失败：' + (e.response?.data?.detail || e.message))
  } finally {
    screenshotLoading.value[slot - 1] = false
  }
  return false  // 阻止 antdv 默认上传
}
```

- [ ] **步骤 3：在编辑弹窗的 Logo 卡片下方插入截图管理卡片**

找到编辑弹窗中 Logo 卡片结束的 `</a-card>` 之后（参考 Detail.vue 行 264-325 的 logo 卡片结构），插入新卡片：

```vue
<a-card title="软件界面图（最多 3 张）" size="small" class="screenshot-card">
  <a-row :gutter="16">
    <a-col :span="8" v-for="slot in 3" :key="slot">
      <div class="screenshot-slot">
        <div class="screenshot-preview">
          <img
            v-if="software[`screenshot_url_${slot}`]"
            :src="software[`screenshot_url_${slot}`]"
            alt="界面图"
          />
          <div v-else class="screenshot-empty">+ 上传截图</div>
          <a-button
            v-if="software[`screenshot_url_${slot}`]"
            shape="circle"
            size="small"
            danger
            class="screenshot-delete"
            :loading="screenshotLoading[slot - 1]"
            @click="handleDeleteScreenshot(slot)"
          >
            <template #icon><DeleteOutlined /></template>
          </a-button>
        </div>
        <a-tabs v-model:activeKey="screenshotTabs[slot - 1]" size="small">
          <a-tab-pane key="upload" tab="上传图片">
            <a-upload
              :before-upload="(file) => handleFileScreenshot(file, slot)"
              :show-upload-list="false"
              accept="image/*"
            >
              <a-button size="small">选择图片</a-button>
            </a-upload>
          </a-tab-pane>
          <a-tab-pane key="url" tab="输入URL">
            <a-input
              v-model:value="screenshotUrlInputs[slot - 1]"
              placeholder="https://example.com/screenshot.png"
              size="small"
            >
              <template #suffix>
                <a-button
                  type="link"
                  size="small"
                  :loading="screenshotLoading[slot - 1]"
                  @click="handleUrlScreenshot(slot)"
                >应用</a-button>
              </template>
            </a-input>
          </a-tab-pane>
        </a-tabs>
      </div>
    </a-col>
  </a-row>
</a-card>
```

- [ ] **步骤 4：添加 CSS 样式**

找到 Detail.vue 的 `<style>` 段，在现有样式末尾追加：

```css
.screenshot-slot {
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  padding: 12px;
  background: #fafafa;
}

.screenshot-preview {
  position: relative;
  width: 100%;
  height: 120px;
  background: #fff;
  border: 1px dashed #d9d9d9;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  overflow: hidden;
}

.screenshot-preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.screenshot-empty {
  color: #999;
  font-size: 13px;
}

.screenshot-delete {
  position: absolute;
  top: 4px;
  right: 4px;
}
```

- [ ] **步骤 5：确认 DeleteOutlined 图标已导入**

检查 `<script setup>` 中是否有 `import { DeleteOutlined } from '@ant-design/icons-vue'` 或类似的图标导入。如未导入，在图标 import 段中加上。

- [ ] **步骤 6：Commit**

```bash
cd /root/dockerProjectDir/software_guard
git add frontend/src/views/Software/Detail.vue
git commit -m "feat(frontend): 编辑弹窗新增软件界面图管理卡片（3 槽位）"
```

---

## 任务 9：前端详情页 - 截图展示区

**文件：**
- 修改：`frontend/src/views/Software/Detail.vue`

- [ ] **步骤 1：在版本列表下方插入截图展示区**

找到 Detail.vue 中版本列表的 `<a-table>`（约行 41-115），在 `</a-table>` 之后、`</a-tab-pane>` 之前插入：

```vue
<div
  v-if="software.screenshot_url_1 || software.screenshot_url_2 || software.screenshot_url_3"
  class="software-screenshots-section"
>
  <h3 class="section-title">软件界面</h3>
  <a-image-preview-group>
    <a-space>
      <a-image
        v-if="software.screenshot_url_1"
        :src="software.screenshot_url_1"
        :width="240"
        alt="界面图 1"
      />
      <a-image
        v-if="software.screenshot_url_2"
        :src="software.screenshot_url_2"
        :width="240"
        alt="界面图 2"
      />
      <a-image
        v-if="software.screenshot_url_3"
        :src="software.screenshot_url_3"
        :width="240"
        alt="界面图 3"
      />
    </a-space>
  </a-image-preview-group>
</div>
```

- [ ] **步骤 2：添加展示区 CSS**

在 `<style>` 段末尾追加：

```css
.software-screenshots-section {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.software-screenshots-section .section-title {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 16px;
  color: rgba(0, 0, 0, 0.85);
}
```

- [ ] **步骤 3：Commit**

```bash
cd /root/dockerProjectDir/software_guard
git add frontend/src/views/Software/Detail.vue
git commit -m "feat(frontend): 详情页版本列表下方展示软件界面图缩略图"
```

---

## 任务 10：Docker 构建与集成测试

**文件：**
- 无（仅部署与测试）

- [ ] **步骤 1：重新构建并启动容器**

```bash
cd /root/dockerProjectDir/software_guard
docker compose --env-file .env.docker up -d --build
```

预期：构建成功，容器正常启动。

- [ ] **步骤 2：浏览器硬刷新（Ctrl+Shift+R / Cmd+Shift+R）**

访问 http://localhost:5173 详情页，确保加载最新 JS。

- [ ] **步骤 3：手动测试 - 上传截图**

1. 以 admin 身份登录
2. 进入任一软件详情页
3. 点击"编辑软件"
4. 找到"软件界面图"卡片
5. 在 slot 1 选择一张本地图片上传
6. 验证：图片预览出现，刷新页面后仍存在

- [ ] **步骤 4：手动测试 - URL 模式**

1. 在 slot 2 的"输入URL" tab 输入 `https://example.com/img.png`
2. 点击"应用"
3. 验证：slot 2 显示该 URL 对应的图片（如果网络可达）

- [ ] **步骤 5：手动测试 - 删除**

1. 点击 slot 1 右上角的删除按钮
2. 验证：slot 1 恢复为"+"占位符，磁盘文件被删除

- [ ] **步骤 6：手动测试 - 详情页展示**

1. 关闭编辑弹窗，回到详情页
2. 在版本列表下方看到"软件界面"区域
3. 3 张缩略图横向排列（slot 1 有图，slot 2 有图，slot 3 为空）
4. 点击任一缩略图，弹出全屏预览，可左右切换

- [ ] **步骤 7：手动测试 - 游客访问**

1. 退出登录（或打开无痕窗口）
2. 访问同一软件详情页
3. 验证：仍能看到"软件界面"缩略图

- [ ] **步骤 8：手动测试 - 边界情况**

1. 输入空 URL → 提示"请输入图片URL"，不发送请求
2. 上传 6MB 大图 → 提示"图片大小不能超过 5MB"
3. 上传 .bmp 文件 → 提示"仅支持 png/jpg/jpeg/gif/svg/webp 格式"
4. 3 个 slot 全部删除 → 详情页"软件界面"区域隐藏

---

## 自检

**1. 规格覆盖度：**

| 规格章节 | 实现任务 |
|----------|----------|
| 1. 数据模型（3 字段） | 任务 1 |
| 1.2 Schema 扩展（4 个 Schema） | 任务 2 |
| 1.3 数据库迁移 | 任务 1 |
| 2.1 POST 端点 | 任务 3 |
| 2.2 DELETE 端点 | 任务 4 |
| 2.3 GET file 端点 | 任务 5 |
| 2.4 现有端点补充 | 任务 2 步骤 5（list_software） |
| 3.1 API client | 任务 7 |
| 3.2 编辑弹窗 UI | 任务 8 |
| 3.3 创建时不提供截图 | 不实现（YAGNI 明确） |
| 3.4 详情页展示 | 任务 9 |
| 4. 测试 | 任务 6 + 任务 10 |
| 8. YAGNI（明确不做） | 全部跳过 ✅ |

**2. 占位符扫描：** 通过（无 TODO / 待定 / 模糊描述）

**3. 类型一致性：**
- `screenshot_url_1/2/3` 字段名贯穿任务 1-9 ✅
- `slot` 参数（int 1/2/3）在任务 3/4/8 保持一致 ✅
- `handleFileScreenshot(file, slot)` 在任务 8 内部使用一致 ✅
- `screenshotLoading[slot - 1]` 索引 0/1/2 ↔ slot 1/2/3 在任务 8 步骤 1/2 一致 ✅

**4. 发现并修复的问题：**
- 任务 2 步骤 1 中 `SoftwareBase` 的 `require_login` 字段当前是 `bool = True`（必填），新增的 3 个 `Optional[str]` 在其下方不会与现有 `validate_url` 校验冲突（`validate_url` 允许空字符串返回 None）✅
- 任务 3 步骤 1 中需要先确认 main.py 迁移段使用 `text()` 还是 `op.execute()`——已在步骤 2 中以注释说明 ✅

---

## 完成检查清单

- [ ] 所有 10 个任务的步骤都执行完毕
- [ ] 每个任务都有对应的 commit
- [ ] curl 测试 9 个用例全部通过
- [ ] 手动测试 8 个场景全部通过
- [ ] 浏览器硬刷新后界面正常
- [ ] 游客可访问截图
- [ ] 至少 1 个 commit 已推送到 GitHub

---

## 执行选项

**计划已完成并保存到 `docs/superpowers/plans/2026-06-17-screenshot-images.md`。两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**
