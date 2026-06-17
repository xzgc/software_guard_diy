# 软件界面图（截图）功能设计

## 概述

为 Software Guard 添加软件界面图（运行截图）管理功能：

1. 每个软件最多 3 张界面图，可选 0 张
2. 在编辑软件弹窗中可上传本地图片或输入外部图片 URL（每张图独立管理）
3. 详情页版本列表下方展示界面图缩略图，点击放大预览
4. 游客可查看界面图（属于"展示"性质，与 Logo 同级）

参考现有 Logo 的双模式实现（`POST /{id}/logo` + `GET /{id}/logo/file/{filename}`）。

---

## 1. 数据模型

### 1.1 模型变更

文件：`backend/app/models/software.py`

`Software` 类新增 3 个字段：

```python
screenshot_url_1 = Column(String(500), nullable=True)  # 软件界面图 1
screenshot_url_2 = Column(String(500), nullable=True)  # 软件界面图 2
screenshot_url_3 = Column(String(500), nullable=True)  # 软件界面图 3
```

### 1.2 Schema 变更

文件：`backend/app/schemas/software.py`

- `SoftwareBase` 新增 `screenshot_url_1/2/3: Optional[str] = None`，复用现有 `validate_url` 校验（行 16-29）
- `SoftwareUpdate` 同样新增 3 个 Optional 字段
- `SoftwareResponse` 通过 `from_attributes=True` 自动包含
- `SoftwareListResponse` 也新增 3 个字段（列表摘要展示用）

### 1.3 数据库迁移

文件：`backend/main.py` lifespan 函数

参照现有 `require_login` 的 `ALTER TABLE software ADD COLUMN` 模式，追加 3 条自迁移 SQL：

```sql
ALTER TABLE software ADD COLUMN IF NOT EXISTS screenshot_url_1 VARCHAR(500);
ALTER TABLE software ADD COLUMN IF NOT EXISTS screenshot_url_2 VARCHAR(500);
ALTER TABLE software ADD COLUMN IF NOT EXISTS screenshot_url_3 VARCHAR(500);
```

---

## 2. API 设计

### 2.1 上传/设置单张截图

`POST /api/software/{software_id}/screenshots`

权限：`require_ops`

**Request（multipart/form-data）**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `slot` | int | 是 | 槽位编号 1/2/3 |
| `file` | UploadFile | 二选一 | 本地图片文件 |
| `url` | str | 二选一 | 外部图片 URL |

**文件模式**：
- 允许扩展名：`.png` `.jpg` `.jpeg` `.gif` `.svg` `.webp`（复用 logo 白名单去掉 ico）
- 大小限制：5MB（与 logo 一致）
- 存储路径：`storage/screenshots/{software_id}_s{slot}_{uuid8}{ext}`
- 更新字段为：`/api/software/{software_id}/screenshots/file/{filename}`

**URL 模式**：
- 直接更新字段为外部 URL
- 不下载、不存储
- 删除该槽位旧的本地文件（如果旧值是 `/api/software/.../screenshots/file/...` 路径）

**校验**：
- `slot` 必须在 1/2/3 范围内（FastAPI Query/Path 校验）
- `file` 和 `url` 必须提供其一

**Response**：

```json
{
  "screenshot_url": "/api/software/1/screenshots/file/xxx.png",
  "slot": 1,
  "message": "截图上传成功"
}
```

### 2.2 删除单张截图

`DELETE /api/software/{software_id}/screenshots/{slot}`

权限：`require_ops`

**行为**：
- `slot` 必须是 1/2/3
- 删除磁盘上的本地文件（如果字段值是 `/api/.../screenshots/file/...`）
- 字段置 NULL
- 不存在则静默成功

**Response**：204 No Content

### 2.3 获取截图文件

`GET /api/software/{software_id}/screenshots/file/{filename}`

权限：`get_optional_current_user`（游客可看）

**行为**：
- 仿照 `get_logo_file`（`backend/app/api/software.py` 行 436-457）
- 使用 `sanitize_filename` + `validate_path_within_dir` 防路径穿越
- 返回 `FileResponse`

### 2.4 现有端点补充

- `create_software`（行 130-173）：response 自动包含 3 个新字段
- `update_software`（行 176-241）：response 自动包含 3 个新字段
- `get_software`（行 95-127）：response 自动包含 3 个新字段
- `list_software`（行 34-81）：response 通过 `SoftwareListResponse` 自动包含

---

## 3. 前端设计

### 3.1 API Client 扩展

文件：`frontend/src/api/software.js`

新增 2 个方法：

```javascript
uploadScreenshot(softwareId, slot, formData) {
  return api.post(`/software/${softwareId}/screenshots`, formData)
}

deleteScreenshot(softwareId, slot) {
  return api.delete(`/software/${softwareId}/screenshots/${slot}`)
}
```

### 3.2 编辑软件弹窗（Detail.vue）

文件：`frontend/src/views/Software/Detail.vue`

在现有 Logo Tab 卡片（行 264-325）**下方**新增"软件界面图"管理卡片。

#### 3.2.1 状态变量

```javascript
const screenshotTabs = ref(['', '', ''])          // 每个 slot 当前激活的 tab: '' | 'upload' | 'url'
const screenshotUrlInputs = ref(['', '', ''])     // 每个 slot 的 URL 输入
const screenshotFileLists = ref([[], [], []])     // 每个 slot 的待上传文件
const screenshotLoading = ref([false, false, false])  // 每个 slot 的 loading
```

#### 3.2.2 布局

3 个 slot 横向排列（`<a-row :gutter="16">` + `<a-col :span="8">`），每列内：

```
┌─ Slot N ─────────────────┐
│ [当前图片预览 200×120]    │
│           [×] (删除按钮)  │
│                          │
│ ┌─上传图片─┬─输入URL─┐   │
│ │ 上传控件 │ URL输入  │   │
│ └─────────┴─────────┘   │
└──────────────────────────┘
```

空槽位显示占位图（虚线边框 + "+ 上传截图"文字）。

#### 3.2.3 交互细节

- **上传模式**：`<a-upload :beforeUpload>` 校验大小 ≤ 5MB + 扩展名白名单，通过后 `formData.append('file', file)` 并调用 API
- **URL 模式**：`<a-input>` + 旁边"应用"按钮，调用 API 时 `formData.append('url', url)`
- **删除按钮**：右上角悬浮 `<a-button shape="circle" icon="delete">`，仅在该 slot 有图时显示（`v-if="software.screenshot_url_N"`）
- **保存时机**：每张图独立保存，**无统一保存按钮**（与 logo 行为一致）
- **保存后**：调用 `await loadDetail()` 刷新当前详情
- **slot 编号**：前端数组索引 0/1/2 ↔ API 槽位 1/2/3，注意 +1

#### 3.2.4 模板片段

```vue
<a-card title="软件界面图（最多 3 张）" class="screenshot-card">
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
            <DeleteOutlined />
          </a-button>
        </div>
        <a-tabs v-model:activeKey="screenshotTabs[slot - 1]" size="small">
          <a-tab-pane key="upload" tab="上传图片">
            <a-upload
              :before-upload="(file) => beforeScreenshotUpload(file, slot)"
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

#### 3.2.5 关键方法

```javascript
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

const beforeScreenshotUpload = (file, slot) => {
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
  // 同步上传
  handleFileScreenshot(file, slot)
  return false  // 阻止 antdv 默认上传
}

const handleFileScreenshot = async (file, slot) => {
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
}
```

### 3.3 创建软件弹窗（List.vue）

文件：`frontend/src/views/Software/List.vue`

**不提供**截图上传（保持创建流程简洁）。

理由：避免在 List.vue 和 Detail.vue 重复实现截图管理 UI；用户创建软件后跳转详情页再编辑截图。

### 3.4 详情页查看（Detail.vue）

在 `<a-table>` 之后（行 115）、`</a-tab-pane>` 之前插入"软件界面"展示区。

#### 3.4.1 模板

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

#### 3.4.2 行为

- 仅在至少 1 张截图存在时显示（`v-if`）
- `a-image-preview-group` 包裹，点击任意一张可全屏预览并支持左右切换
- 缩略图宽度 240px，懒加载（Ant Design Vue 默认行为）

#### 3.4.3 CSS

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

---

## 4. 测试

### 4.1 后端手动测试（curl）

1. **上传文件模式**：
   ```bash
   curl -X POST http://localhost:8000/api/software/1/screenshots \
     -H "Authorization: Bearer <token>" \
     -F "slot=1" \
     -F "file=@/tmp/screenshot1.png"
   ```
   - 检查 DB `screenshot_url_1` 是否更新
   - 检查 `storage/screenshots/1_s1_xxxxxxxx.png` 是否存在

2. **URL 模式**：
   ```bash
   curl -X POST http://localhost:8000/api/software/1/screenshots \
     -H "Authorization: Bearer <token>" \
     -F "slot=2" \
     -F "url=https://example.com/img.png"
   ```
   - 检查 DB `screenshot_url_2` 是否为完整 URL

3. **删除**：
   ```bash
   curl -X DELETE http://localhost:8000/api/software/1/screenshots/1 \
     -H "Authorization: Bearer <token>"
   ```
   - 检查 DB 字段为 NULL
   - 检查磁盘文件已删除

4. **路径穿越防护**：
   ```bash
   curl "http://localhost:8000/api/software/1/screenshots/file/..%2F..%2Fetc%2Fpasswd"
   ```
   - 期望 400 或 404

5. **slot 越界**：
   ```bash
   curl -X POST http://localhost:8000/api/software/1/screenshots \
     -H "Authorization: Bearer <token>" \
     -F "slot=4"
   ```
   - 期望 422

6. **游客访问文件**：
   ```bash
   curl "http://localhost:8000/api/software/1/screenshots/file/1_s1_xxxxxxxx.png"
   ```
   - 无 token 期望 200

### 4.2 前端手动测试

1. 编辑弹窗 3 个 slot 独立上传/URL/删除
2. 详情页底部缩略图渲染
3. 点击缩略图全屏预览，可左右切换
4. 游客（未登录）访问详情页可见截图
5. 删除/上传后页面自动刷新

### 4.3 边界情况

- 用户上传 slot 1 后再上传 URL 模式 → slot 1 旧本地文件应被删除
- 用户上传 slot 1 后删除 slot 1 → 磁盘文件应被删除
- 用户输入空 URL → 前端阻止提交
- 3 个 slot 全部为空时，详情页不显示"软件界面"区域

---

## 5. 实施顺序

1. **数据库迁移**：模型 + main.py 自迁移 SQL → 重启验证
2. **后端 API**：3 个端点（POST/DELETE/GET file） → 用 curl 测试
3. **后端 Schema 扩展**：3 个字段加到 `SoftwareResponse` / `SoftwareListResponse`
4. **前端 API client**：新增 2 个方法
5. **前端编辑弹窗**：在 Detail.vue 添加截图管理卡片
6. **前端详情查看**：在版本列表下方插入截图展示区
7. **集成测试**：完整流程（上传 → 显示 → 删除 → 再次上传）
8. **Docker 部署**：`docker compose up -d --build` 验证

---

## 6. 配置默认值

无新增配置项。

---

## 7. 风险点

1. **磁盘文件孤儿**：slot 切换为 URL 模式时，旧本地文件会主动删除（与 logo 行为一致）。如需保留作备份请明示
2. **slot 编号混淆**：前端数组索引 0/1/2 ↔ API 槽位 1/2/3，注意 +1
3. **跨软件文件读取**：`/screenshots/file/{filename}` 必须用 `validate_path_within_dir` 防止读到其他软件的文件
4. **大图性能**：3 张 5MB 图片同时加载可能影响首屏，前端 `a-image` 默认懒加载可缓解

---

## 8. YAGNI（明确不做）

- ❌ 拖拽排序（用户如需调整顺序，删除后重新上传）
- ❌ 任意数量截图（写死 3 张）
- ❌ 截图水印/压缩处理
- ❌ 截图描述/标题
- ❌ 创建软件时同时上传截图（创建流程不引入截图 UI）
- ❌ 截图与版本绑定（截图属于软件而非某个版本）
- ❌ 截图审核/举报功能
- ❌ 游客无图/有图分别控制
