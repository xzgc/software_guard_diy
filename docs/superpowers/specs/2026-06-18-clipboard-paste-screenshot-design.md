# 软件界面图 - 剪贴板粘贴功能设计

## 概述

为 Software Guard 的"软件界面图"添加剪贴板粘贴支持：

1. 用户在编辑软件弹窗打开时按 Ctrl+V
2. 系统读取剪贴板中的图片数据（PNG/JPEG/GIF/SVG/WebP）
3. 按顺序填充到第一个空 slot（1→2→3），全填满则覆盖 slot 1
4. 沿用现有 `upload_screenshot` API，无需改后端
5. 完全复用现有 loading 状态、错误处理、消息提示

不修改后端代码，不引入新 UI 元素。

---

## 1. 架构

### 1.1 后端

**无任何改动。** 现有 `POST /software/{software_id}/screenshots` 端点已能处理任意 `File` / `Blob`：
- 路由：`backend/app/api/software.py:389`
- 签名：`async def upload_screenshot(software_id, slot=Form(ge=1,le=3), file=File(None), url=Form(None), ...)`
- 校验：5MB + png/jpg/jpeg/gif/svg/webp 白名单
- 鉴权：`require_ops`

### 1.2 前端

文件：`frontend/src/views/Software/Detail.vue`

变更范围：
1. **重构**：提取 `validateScreenshotFile(file)` 公共校验函数（DRY 改造）
2. **新增**：`getPasteTargetSlots(imageCount)` 工具函数
3. **新增**：`handleClipboardPaste(event)` 全局 paste 处理函数
4. **生命周期**：`onMounted` 注册 / `onBeforeUnmount` 移除 / `watch(showEditModal)` 控制激活
5. **改造**：`handleFileScreenshot` 调用 `validateScreenshotFile`（去掉重复代码）

---

## 2. 数据流

```
用户在编辑弹窗内按 Ctrl+V
  ↓
document 触发 paste 事件
  ↓
handleClipboardPaste(event) 被调用
  ↓
if (pasteActive.value === false) return  ← 编辑弹窗未打开
  ↓
遍历 event.clipboardData.items
  ↓
收集所有 image/* 的 Blob，构造 paste-{timestamp}.{ext} File
  ↓
if 数量为 0:
  message.info('剪贴板中没有图片')   ← 用户主动反馈
  return
  ↓
计算目标 slot 列表（getPasteTargetSlots）：
  - 优先找空 slot（1→2→3）
  - 不够就追加到已有 slot（从 1 开始）
  - 截断到 imageFiles.length 个
  ↓
if imageFiles.length > 3:
  message.warning('剪贴板有 N 张图片，最多粘贴 3 张')
  ↓
串行上传（await 循环）：
  for i in range(min(imageFiles.length, 3)):
    slot = targetSlots[i]
    file = imageFiles[i]
    err = validateScreenshotFile(file)
    if err: message.error(`slot ${slot}: ${err}`); continue
    screenshotLoading[slot-1] = true
    try:
      formData.append('slot', slot)
      formData.append('file', file)
      await softwareApi.uploadScreenshot(...)
      successCount++
    finally:
      screenshotLoading[slot-1] = false
  ↓
if successCount > 0:
  await loadDetail()
  message.success(`已粘贴 ${successCount} 张截图`)
```

---

## 3. 前端 API/工具函数

### 3.1 提取公共校验函数

```javascript
const validateScreenshotFile = (file) => {
  const isImage = /\.(png|jpg|jpeg|gif|svg|webp)$/i.test(file.name)
  if (!isImage) {
    return '仅支持 png/jpg/jpeg/gif/svg/webp 格式'
  }
  const isLt5M = file.size / 1024 / 1024 < 5
  if (!isLt5M) {
    return '图片大小不能超过 5MB'
  }
  return null  // 校验通过
}
```

### 3.2 计算目标 slot 列表

```javascript
const getPasteTargetSlots = (imageCount) => {
  const slots = []
  // 优先找空 slot
  for (let i = 1; i <= 3; i++) {
    if (!software.value[`screenshot_url_${i}`]) {
      slots.push(i)
      if (slots.length === imageCount) return slots
    }
  }
  // 不够就追加（按 slot 1 → 2 → 3 顺序，覆盖最早的）
  let next = 1
  while (slots.length < imageCount && next <= 3) {
    if (!slots.includes(next)) slots.push(next)
    next++
  }
  return slots.slice(0, Math.min(imageCount, 3))
}
```

### 3.3 粘贴处理函数

```javascript
const handleClipboardPaste = async (event) => {
  if (!pasteActive.value) return

  const items = event.clipboardData?.items
  if (!items) return

  // 收集所有 image/* Blob，构造 paste-{ts}.{ext} File
  const imageFiles = []
  for (const item of items) {
    if (item.kind === 'file' && item.type.startsWith('image/')) {
      const blob = item.getAsFile()
      if (blob) {
        const ext = (blob.type.split('/')[1] || 'png').toLowerCase()
        const filename = `paste-${Date.now()}.${ext}`
        imageFiles.push(new File([blob], filename, { type: blob.type }))
      }
    }
  }

  if (imageFiles.length === 0) {
    message.info('剪贴板中没有图片')
    return
  }

  if (imageFiles.length > 3) {
    message.warning(`剪贴板有 ${imageFiles.length} 张图片，最多粘贴 3 张`)
  }

  const targetSlots = getPasteTargetSlots(imageFiles.length)
  let successCount = 0

  for (let i = 0; i < targetSlots.length; i++) {
    const slot = targetSlots[i]
    const file = imageFiles[i]

    const error = validateScreenshotFile(file)
    if (error) {
      message.error(`slot ${slot}：${error}`)
      continue
    }

    screenshotLoading.value[slot - 1] = true
    try {
      const formData = new FormData()
      formData.append('slot', slot)
      formData.append('file', file)
      await softwareApi.uploadScreenshot(route.params.id, slot, formData)
      successCount++
    } catch (e) {
      message.error(`slot ${slot} 上传失败：${e.response?.data?.detail || e.message}`)
    } finally {
      screenshotLoading.value[slot - 1] = false
    }
  }

  if (successCount > 0) {
    await loadDetail()
    message.success(`已粘贴 ${successCount} 张截图`)
  }
}
```

### 3.4 生命周期与激活控制

```javascript
import { onMounted, onBeforeUnmount, watch, ref } from 'vue'  // 新增 onBeforeUnmount

const pasteActive = ref(false)

onMounted(() => {
  document.addEventListener('paste', handleClipboardPaste)
  // ... 现有逻辑（loadCategories、loadDetail）
})

onBeforeUnmount(() => {
  document.removeEventListener('paste', handleClipboardPaste)
})

watch(showEditModal, (newVal) => {
  pasteActive.value = newVal
})
```

### 3.5 handleFileScreenshot 改造

将原内联校验改为调用公共函数：

```javascript
const handleFileScreenshot = async (file, slot) => {
  const error = validateScreenshotFile(file)
  if (error) {
    message.error(error)
    return false
  }
  // ... 原上传逻辑保持不变
}
```

---

## 4. UI 提示

**不修改模板。** 完全复用现有 UI：
- 粘贴后 `loadDetail()` 刷新 `software` 对象
- 现有 3 个 slot 缩略图自动更新（v-if 重新求值）
- 顶部 `message.success` 提示"已粘贴 N 张截图"
- 现有 `screenshotLoading[slot-1]` 显示每个 slot 的 spinner

不引入 banner、toast、hint 文字等新元素。

### 4.1 边界情况

| 场景 | 行为 |
|------|------|
| 编辑弹窗未打开 | `pasteActive=false` → 直接 return |
| 剪贴板是文本 | `imageFiles=[]` → `message.info('剪贴板中没有图片')` |
| 剪贴板是图片 + 文本混合 | 仅处理 image/* item，文本忽略 |
| 剪贴板有 5 张图 | 截断到 3 张 + `message.warning` |
| 粘贴的不是允许的格式 | `message.error('仅支持 png/jpg/jpeg/gif/svg/webp 格式')` |
| 粘贴 6MB 大图 | `message.error('图片大小不能超过 5MB')` |
| 用户在 URL input 聚焦 + 剪贴板是图片 | input 不接受图片，document 监听读取 → 上传图片 |
| 用户在 URL input 聚焦 + 剪贴板是文本 | input 默认粘贴文本，document 监听无 image/* → `message.info` |
| 上传过程中弹窗关闭 | `pasteActive` 变 false，当前 await 仍会完成 |
| 软件不存在 / 后端 404 | `message.error` 显示后端 detail |

---

## 5. 测试

### 5.1 手动测试场景（需用户浏览器验证）

1. **基本粘贴**：用截图工具复制一张图 → 编辑弹窗 → Ctrl+V → 出现在第一个空 slot
2. **全 slot 覆盖**：3 个 slot 都有图 → 复制新图 → Ctrl+V → 替换 slot 1
3. **多张图片粘贴**：文件管理器选 2-3 张图复制 → Ctrl+V → 按顺序填入空 slot
4. **剪贴板是文本**：复制文字 → 编辑弹窗内 Ctrl+V → `message.info` 提示，文本未受影响
5. **URL input 聚焦 + 图片**：点击 URL input → 复制图片 → Ctrl+V → 上传到 slot 1，input 未写入
6. **弹窗关闭后粘贴**：关闭编辑弹窗 → 任意位置 Ctrl+V → 完全无反应
7. **超过 5MB**：复制 6MB 图片 → Ctrl+V → `message.error`
8. **5 张图粘贴**：复制 5 张图 → Ctrl+V → 填满 3 slot + warning 提示

### 5.2 边界情况测试

- 浏览器兼容：Chrome/Edge/Firefox/Safari（macOS 13.1+ / iOS 13.4+）
- 多 tab 切换
- 重复连续 Ctrl+V

---

## 6. 实施顺序

1. **重构**：提取 `validateScreenshotFile` 函数
2. **改造**：`handleFileScreenshot` 调用公共校验
3. **新增**：`getPasteTargetSlots` + `handleClipboardPaste` + `pasteActive` ref
4. **生命周期**：`onMounted` 注册 / `onBeforeUnmount` 移除 / `watch(showEditModal)` 激活
5. **Vite HMR 验证**：浏览器实际操作

无后端代码改动。

---

## 7. 风险点

1. **Safari 兼容性**：macOS Safari 13.1+ / iOS 13.4+ 完整支持剪贴板图片粘贴
2. **HTTPS 要求**：`paste` 事件 + `clipboardData.items` **无需 HTTPS**（与 `navigator.clipboard.read()` 不同）
3. **多 tab 切换**：paste 事件绑定到当前 document，切到其他 tab 不触发
4. **重复粘贴**：连续按 Ctrl+V 会触发多次上传，串行执行 + 后端幂等可容忍

---

## 8. YAGNI 清单

- ❌ 拖拽上传
- ❌ 粘贴时显示预览缩略图（已有上传完成后的缩略图）
- ❌ 全局快捷键（不仅限于编辑弹窗）
- ❌ 上传进度条（沿用现有 loading spinner）
- ❌ 支持非图片格式（PDF、视频帧）
- ❌ 粘贴后弹出确认对话框
- ❌ 剪贴板变化监听（仅响应 paste 事件，不主动轮询）
- ❌ 防抖（连续 Ctrl+V 串行处理足够）
- ❌ 后端代码改动
- ❌ 新增 UI 元素

---

## 9. 文件变更

仅修改 1 个文件：

- `frontend/src/views/Software/Detail.vue`
  - import 增加 `onBeforeUnmount`
  - 新增 `pasteActive` ref
  - 新增 `validateScreenshotFile` 函数
  - 新增 `getPasteTargetSlots` 函数
  - 新增 `handleClipboardPaste` 函数
  - 改造 `handleFileScreenshot` 使用 `validateScreenshotFile`
  - `onMounted` 末尾增加 `document.addEventListener('paste', ...)`
  - 新增 `onBeforeUnmount` 移除监听
  - 新增 `watch(showEditModal, ...)` 控制激活
