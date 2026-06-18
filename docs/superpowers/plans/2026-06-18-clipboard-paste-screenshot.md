# 软件界面图 - 剪贴板粘贴 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为 Software Guard 的"软件界面图"添加 Ctrl+V 剪贴板粘贴支持，让用户在编辑软件弹窗内可直接粘贴图片到 slot 1/2/3。

**架构：** 纯前端功能，监听 `document.paste` 事件，提取 `ClipboardEvent.clipboardData.items` 中 `image/*` 类型的 Blob，构造 File 对象，复用现有 `softwareApi.uploadScreenshot` API。沿用现有 loading 状态、错误处理、消息提示。后端无改动。

**技术栈：** Vue 3（ref / watch / onMounted / onBeforeUnmount）、Ant Design Vue（message）、浏览器原生 `paste` 事件 + `ClipboardEvent.clipboardData`。

**规格文档：** `docs/superpowers/specs/2026-06-18-clipboard-paste-screenshot-design.md`

---

## 文件结构

**修改的文件：**
- `frontend/src/views/Software/Detail.vue`
  - import 增加 `onBeforeUnmount`
  - 新增 `pasteActive` ref
  - 新增 `validateScreenshotFile(file)` 函数（DRY 重构）
  - 改造 `handleFileScreenshot` 调用 `validateScreenshotFile`
  - 新增 `getPasteTargetSlots(imageCount)` 函数
  - 新增 `handleClipboardPaste(event)` 函数
  - `onMounted` 末尾增加 `document.addEventListener('paste', ...)`
  - 新增 `onBeforeUnmount` 移除监听
  - 新增 `watch(showEditModal, ...)` 控制激活

**不创建的文件：**
- 不创建新组件（粘贴逻辑仅在 Detail.vue 内）
- 不创建新工具文件（`validateScreenshotFile` 保持私有）

---

## 任务 1：提取公共校验函数 validateScreenshotFile

**文件：**
- 修改：`frontend/src/views/Software/Detail.vue`

- [ ] **步骤 1：新增 `validateScreenshotFile` 函数**

打开 `frontend/src/views/Software/Detail.vue`，找到 `<script setup>` 中现有的 `handleFileScreenshot` 函数（约 line 691-716）。在它**之前**新增：

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

- [ ] **步骤 2：改造 `handleFileScreenshot` 调用公共函数**

将 `handleFileScreenshot` 改为：

```javascript
const handleFileScreenshot = async (file, slot) => {
  const error = validateScreenshotFile(file)
  if (error) {
    message.error(error)
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

- [ ] **步骤 3：Commit**

```bash
cd /root/dockerProjectDir/software_guard
git add frontend/src/views/Software/Detail.vue
git commit -m "refactor(frontend): 提取 validateScreenshotFile 公共校验函数"
```

---

## 任务 2：新增粘贴处理相关函数

**文件：**
- 修改：`frontend/src/views/Software/Detail.vue`

- [ ] **步骤 1：新增 `pasteActive` ref**

在 `screenshotLoading` ref 附近（约 line 431）追加：

```javascript
const pasteActive = ref(false)  // 仅在编辑弹窗打开时激活 Ctrl+V 粘贴
```

- [ ] **步骤 2：新增 `getPasteTargetSlots` 函数**

在 `validateScreenshotFile` 函数**之后**追加：

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

- [ ] **步骤 3：新增 `handleClipboardPaste` 函数**

在 `getPasteTargetSlots` 函数**之后**追加：

```javascript
const handleClipboardPaste = async (event) => {
  if (!pasteActive.value) return

  const items = event.clipboardData?.items
  if (!items) return

  // 收集所有 image/* Blob，构造 paste-{timestamp}.{ext} File
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

- [ ] **步骤 4：Commit**

```bash
cd /root/dockerProjectDir/software_guard
git add frontend/src/views/Software/Detail.vue
git commit -m "feat(frontend): 新增 handleClipboardPaste 剪贴板粘贴处理函数"
```

---

## 任务 3：生命周期与激活控制

**文件：**
- 修改：`frontend/src/views/Software/Detail.vue`

- [ ] **步骤 1：在 import 段增加 `onBeforeUnmount`**

找到 `<script setup>` 顶部的 `import { ... } from 'vue'`（约 line 412），在导入列表中追加 `onBeforeUnmount`：

```javascript
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
```

（注意：实际 import 列表以文件当前内容为准，可能 `computed` 未使用或 `nextTick` 名称不同。务必先 Read 当前 import 段，再补全 `onBeforeUnmount`。**不要删除**任何已有 import。）

- [ ] **步骤 2：在 `onMounted` 末尾注册 paste 监听**

找到现有的 `onMounted` 块（约 line 1080），在函数体末尾追加：

```javascript
onMounted(() => {
  loadCategories()
  loadDetail()
  document.addEventListener('paste', handleClipboardPaste)
})
```

- [ ] **步骤 3：新增 `onBeforeUnmount` 移除监听**

在 `onMounted` 之后追加：

```javascript
onBeforeUnmount(() => {
  document.removeEventListener('paste', handleClipboardPaste)
})
```

- [ ] **步骤 4：新增 `watch(showEditModal, ...)` 控制激活**

在 `onBeforeUnmount` 之后追加：

```javascript
watch(showEditModal, (newVal) => {
  pasteActive.value = newVal
})
```

- [ ] **步骤 5：Commit**

```bash
cd /root/dockerProjectDir/software_guard
git add frontend/src/views/Software/Detail.vue
git commit -m "feat(frontend): 编辑弹窗打开期间激活 Ctrl+V 粘贴监听"
```

---

## 任务 4：Vite HMR 验证

**文件：**
- 无（仅验证）

- [ ] **步骤 1：确认前端 dev server 在运行**

```bash
ps aux | grep -E "vite|node.*dev" | grep -v grep
```

预期：能看到 `pnpm dev` 或 `vite` 进程。如果没运行，启动：

```bash
cd /root/dockerProjectDir/software_guard/frontend && pnpm dev
```

- [ ] **步骤 2：浏览器硬刷新**

访问 `http://localhost:5173`，按 **Ctrl+Shift+R** / **Cmd+Shift+R** 硬刷新以加载最新代码（Vite HMR 通常自动应用，但保险起见硬刷新）。

- [ ] **步骤 3：手动验证 - 基本粘贴**

1. 用系统截图工具（macOS: Cmd+Shift+Ctrl+4；Windows: Snipping Tool；或任意截图工具）复制一张图
2. 进入任一软件详情页
3. 点击"编辑软件"
4. 按 **Ctrl+V**
5. **预期**：图片出现在第一个空 slot，顶部 message.success "已粘贴 1 张截图"

- [ ] **步骤 4：手动验证 - 全 slot 覆盖**

1. 让 3 个 slot 都有图（先手动上传 3 张）
2. 用截图工具复制第 4 张
3. 编辑弹窗打开，按 Ctrl+V
4. **预期**：替换 slot 1，message.success "已粘贴 1 张截图"

- [ ] **步骤 5：手动验证 - 多张图片粘贴**

1. 关闭编辑弹窗
2. 在文件管理器（macOS Finder / Windows Explorer）选 2-3 张图片，复制
3. 重新打开编辑弹窗
4. 按 Ctrl+V
5. **预期**：按顺序填入空 slot 1→2→3

- [ ] **步骤 6：手动验证 - 剪贴板是文本**

1. 复制一段文字
2. 编辑弹窗内按 Ctrl+V
3. **预期**：message.info "剪贴板中没有图片"，文本**未被吞**（如果在 input 内则正常粘贴到 input）

- [ ] **步骤 7：手动验证 - URL input 聚焦 + 剪贴板是图片**

1. 点击 slot 2 的"输入URL" Tab
2. 在 URL 输入框内点击获得焦点
3. 复制一张图片
4. 按 Ctrl+V
5. **预期**：图片上传到第一个空 slot，URL input 未被写入图片

- [ ] **步骤 8：手动验证 - 弹窗关闭后粘贴**

1. 关闭编辑弹窗
2. 在浏览器任意位置按 Ctrl+V
3. **预期**：完全无反应（不触发上传、不弹消息）

- [ ] **步骤 9：手动验证 - 超过 5MB**

1. 复制一张 6MB+ 图片（用大图工具或先在文件管理器复制）
2. 编辑弹窗打开，按 Ctrl+V
3. **预期**：message.error "图片大小不能超过 5MB"

- [ ] **步骤 10：手动验证 - 5 张图粘贴**

1. 在文件管理器选 5 张图复制
2. 编辑弹窗打开，按 Ctrl+V
3. **预期**：填满 3 个 slot，message.warning "剪贴板有 5 张图片，最多粘贴 3 张"

---

## 自检

**1. 规格覆盖度：**

| 规格章节 | 实现任务 |
|----------|----------|
| 1.1 后端无改动 | ✅（无任务） |
| 1.2 前端变更列表 | 任务 1-3 |
| 2. 数据流 | 任务 2 步骤 3 |
| 3.1 提取公共校验 | 任务 1 步骤 1 |
| 3.2 计算目标 slot | 任务 2 步骤 2 |
| 3.3 粘贴处理函数 | 任务 2 步骤 3 |
| 3.4 生命周期与激活 | 任务 3 |
| 3.5 handleFileScreenshot 改造 | 任务 1 步骤 2 |
| 4. UI 提示（不修改模板） | ✅（无任务） |
| 4.1 边界情况 | 由 3.3 函数逻辑覆盖 |
| 5.1 手动测试场景 1-8 | 任务 4 步骤 3-10 |
| 6. 实施顺序 | 任务 1-3 已按顺序排列 |
| 7. 风险点 | 在规格文档中记录 |
| 8. YAGNI（明确不做） | 全部跳过 ✅ |
| 9. 文件变更 | 任务 1-3 仅修改 Detail.vue ✅ |

**2. 占位符扫描：** 通过（无 TODO / 待定 / 模糊描述）

**3. 类型一致性：**
- `validateScreenshotFile` 在任务 1 步骤 1 定义、任务 1 步骤 2 复用、任务 2 步骤 3 复用 ✅
- `getPasteTargetSlots` 在任务 2 步骤 2 定义、任务 2 步骤 3 使用 ✅
- `handleClipboardPaste` 在任务 2 步骤 3 定义、任务 3 步骤 2 注册、步骤 3 移除、步骤 4 通过 pasteActive 控制 ✅
- `pasteActive` ref 在任务 2 步骤 1 定义、任务 3 步骤 4 控制 ✅
- `screenshotLoading[slot - 1]` 在任务 1 步骤 2 和任务 2 步骤 3 一致使用 ✅

**4. 关键检查点：**
- 任务 1 步骤 1：`validateScreenshotFile` 返回值类型为 `string | null`，任务 1 步骤 2 和任务 2 步骤 3 都用 `if (error)` 判断 ✅
- 任务 2 步骤 2：`getPasteTargetSlots` 使用 `software.value[...]` 访问响应式对象 — 因为 `software` 是 ref（用 `software.value`），与文件内现有访问方式一致 ✅
- 任务 3 步骤 1：import 段必须先 Read 当前内容再修改，避免覆盖 ✅

---

## 完成检查清单

- [ ] 任务 1-3 全部步骤执行完毕
- [ ] 任务 1-3 全部 commit 完成
- [ ] 任务 4 步骤 3-10 全部手动测试通过
- [ ] Vite HMR 实时生效无需重启容器
- [ ] 编辑弹窗外按 Ctrl+V 无反应（步骤 8）
- [ ] 文本粘贴不受影响（步骤 6）
- [ ] 至少 1 个 commit 已推送到 GitHub

---

## 执行选项

**计划已完成并保存到 `docs/superpowers/plans/2026-06-18-clipboard-paste-screenshot.md`。两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**
