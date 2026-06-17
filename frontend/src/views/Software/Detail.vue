<template>
  <div v-if="loading">
    <a-spin />
  </div>
  <div v-else-if="software">
    <a-page-header
      :title="software.name"
      @back="$router.back()"
    >
      <template #extra>
        <a-space>
          <a-button v-if="userStore.isOps()" @click="openEditModal">
            <template #icon><EditOutlined /></template>
            编辑软件
          </a-button>
          <a-button v-if="userStore.isOps()" danger @click="handleDelete">
            <template #icon><DeleteOutlined /></template>
            删除
          </a-button>
          <a-button v-if="userStore.isOps()" @click="showVersionModal = true">
            <template #icon><UploadOutlined /></template>
            上传新版本
          </a-button>
          <a-button
            v-if="canDownloadLatest"
            type="primary"
            @click="downloadLatest"
          >
            <template #icon><DownloadOutlined /></template>
            下载最新版
          </a-button>
          <a-button v-else type="primary" @click="goLogin">
            <template #icon><LoginOutlined /></template>
            登录后下载
          </a-button>
        </a-space>
      </template>
      <template #footer>
        <a-tabs>
          <a-tab-pane key="versions" tab="版本列表">
            <a-table
              :columns="versionColumns"
              :data-source="software.versions"
              :pagination="false"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'version'">
                  <a-tag color="blue">{{ record.version }}</a-tag>
                </template>
                <template v-else-if="column.key === 'fileSize'">
                  {{ formatFileSize(record.file_size) }}
                </template>
                <template v-else-if="column.key === 'fileHash'">
                  <a-typography-text copyable :content="record.file_hash">
                    {{ record.file_hash?.slice(0, 16) }}...
                  </a-typography-text>
                </template>
                <template v-else-if="column.key === 'uploadTime'">
                  {{ formatDate(record.upload_time) }}
                </template>
                <template v-else-if="column.key === 'originalDownloadUrl'">
                  <a-tooltip v-if="record.original_download_url" :title="record.original_download_url">
                    <a :href="record.original_download_url" target="_blank" rel="noopener noreferrer">
                      <LinkOutlined />
                    </a>
                  </a-tooltip>
                  <span v-else>-</span>
                </template>
                <template v-else-if="column.key === 'actions'">
                  <a-space>
                    <a-button
                      v-if="canDownloadRecord"
                      type="link"
                      size="small"
                      @click="downloadVersion(record)"
                    >
                      <DownloadOutlined /> 下载
                    </a-button>
                    <a-button
                      v-else
                      type="link"
                      size="small"
                      @click="goLogin"
                    >
                      <LoginOutlined /> 登录后下载
                    </a-button>
                    <a-button
                      v-if="userStore.token"
                      type="link"
                      size="small"
                      @click="checkVulnerability(record)"
                    >
                      <SafetyOutlined /> 检查漏洞
                    </a-button>
                    <a-button
                      v-if="userStore.isAdmin()"
                      type="link"
                      size="small"
                      @click="openEditVersionModal(record)"
                    >
                      <EditOutlined /> 编辑
                    </a-button>
                    <a-button
                      v-if="userStore.isOps()"
                      type="link"
                      size="small"
                      danger
                      @click="handleDeleteVersion(record)"
                    >
                      <DeleteOutlined /> 删除
                    </a-button>
                  </a-space>
                </template>
              </template>
            </a-table>
          </a-tab-pane>
          <a-tab-pane key="downloads" tab="下载记录" v-if="userStore.isOps()">
            <a-table
              :columns="downloadColumns"
              :data-source="downloadLogs"
              :loading="loadingDownloads"
              :pagination="{ pageSize: 20 }"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'downloadTime'">
                  {{ formatDate(record.download_time) }}
                </template>
              </template>
            </a-table>
          </a-tab-pane>
        </a-tabs>
      </template>
    </a-page-header>

    <a-descriptions style="margin-top: 24px" :column="2">
      <a-descriptions-item label="描述">
        {{ software.description || '暂无描述' }}
      </a-descriptions-item>
      <a-descriptions-item label="分类">
        <a-tag>{{ software.category || '未分类' }}</a-tag>
      </a-descriptions-item>
      <a-descriptions-item label="官网">
        <a v-if="software.official_url" :href="software.official_url" target="_blank">
          {{ software.official_url }}
        </a>
        <span v-else>-</span>
      </a-descriptions-item>
      <a-descriptions-item label="下载权限">
        <a-tag v-if="!software.require_login" color="green">游客可下载</a-tag>
        <a-tag v-else color="orange">需登录下载</a-tag>
      </a-descriptions-item>
      <a-descriptions-item label="版本数">
        {{ software.versions.length }}
      </a-descriptions-item>
    </a-descriptions>

    <!-- 上传新版本弹窗（支持 Tab 切换） -->
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
      <a-tabs v-model:active-key="versionTab" :disabled="uploading">
        <a-tab-pane key="upload" tab="上传文件">
          <a-form :model="versionForm" layout="vertical" style="margin-top: 16px;">
            <a-form-item label="版本号" required>
              <a-input v-model:value="versionForm.version" placeholder="如: 1.0.0" :disabled="uploading" />
            </a-form-item>
            <a-form-item label="文件" required>
              <a-upload
                :before-upload="beforeUpload"
                :file-list="fileList"
                @remove="() => fileList = []"
                :disabled="uploading"
              >
                <a-button :disabled="uploading">
                  <UploadOutlined /> 选择文件
                </a-button>
              </a-upload>
            </a-form-item>
            <a-form-item label="文件名" help="留空则使用上传文件的原始文件名">
              <a-input v-model:value="versionForm.file_name" placeholder="如: setup.exe" :disabled="uploading" />
            </a-form-item>
            <a-form-item label="文件大小（字节）" help="留空则自动获取实际文件大小">
              <a-input-number v-model:value="versionForm.file_size" :min="0" :disabled="uploading" style="width: 100%;" placeholder="自动获取" />
            </a-form-item>
            <a-form-item label="更新说明">
              <a-textarea v-model:value="versionForm.release_notes" :rows="3" :disabled="uploading" />
            </a-form-item>
            <div v-if="uploadProgress > 0" style="margin-top: 16px;">
              <a-progress :percent="uploadProgress" :status="uploadStatus" />
              <p style="margin-top: 8px; color: #999; font-size: 12px;">{{ uploadDetailText }}</p>
            </div>
          </a-form>
        </a-tab-pane>
        <a-tab-pane key="url" tab="提供下载地址">
          <a-form :model="versionForm" layout="vertical" style="margin-top: 16px;">
            <a-form-item label="版本号" required>
              <a-input v-model:value="versionForm.version" placeholder="如: 1.0.0" :disabled="uploading" />
            </a-form-item>
            <a-form-item label="外部下载地址" help="如不填写，将使用软件官网地址">
              <a-input
                v-model:value="versionForm.external_url"
                placeholder="https://example.com/download/file.zip"
                :disabled="uploading"
              />
            </a-form-item>
            <a-form-item label="更新说明">
              <a-textarea v-model:value="versionForm.release_notes" :rows="3" :disabled="uploading" />
            </a-form-item>
            <a-alert
              v-if="!versionForm.external_url && software.official_url"
              type="info"
              show-icon
              style="margin-top: 8px;"
            >
              <template #message>
                未填写下载地址，将默认使用官网地址：{{ software.official_url }}
              </template>
            </a-alert>
          </a-form>
        </a-tab-pane>
      </a-tabs>
    </a-modal>

    <!-- 漏洞检查弹窗 -->
    <a-modal
      v-model:open="showVulnModal"
      title="漏洞检查结果"
      :footer="null"
    >
      <a-spin :spinning="checkingVuln">
        <div v-if="vulnerabilities.length === 0">
          <a-result status="success" title="未发现已知漏洞" />
        </div>
        <div v-else>
          <a-alert
            v-for="vuln in vulnerabilities"
            :key="vuln.id"
            :type="vuln.severity === 'critical' || vuln.severity === 'high' ? 'error' : 'warning'"
            style="margin-bottom: 12px"
          >
            <template #message>
              {{ vuln.title || vuln.cve_id }}
              <a-tag :color="getSeverityColor(vuln.severity)">
                {{ vuln.severity }}
              </a-tag>
            </template>
            <p>{{ vuln.description }}</p>
            <p v-if="vuln.fixed_version">
              修复版本: {{ vuln.fixed_version }}
            </p>
          </a-alert>
        </div>
      </a-spin>
    </a-modal>

    <!-- 编辑软件弹窗 -->
    <a-modal
      v-model:open="showEditModal"
      title="编辑软件"
      @ok="handleEdit"
      :confirm-loading="editLoading"
    >
      <a-form :model="editForm" layout="vertical">
        <a-form-item label="软件名称" required>
          <a-input v-model:value="editForm.name" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="editForm.description" :rows="3" />
        </a-form-item>
        <a-form-item label="分类">
          <a-select v-model:value="editForm.category">
            <a-select-option v-for="cat in categories" :key="cat" :value="cat">
              {{ cat }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="Logo">
          <a-tabs v-model:active-key="logoTab" size="small">
            <a-tab-pane key="upload" tab="上传图片">
              <a-upload
                :before-upload="beforeLogoUpload"
                :file-list="logoFileList"
                @remove="handleLogoRemove"
                list-type="picture"
                :max-count="1"
              >
                <a-button v-if="logoFileList.length === 0">
                  <UploadOutlined /> 选择Logo图片
                </a-button>
              </a-upload>
              <div style="margin-top: 4px; color: #999; font-size: 12px;">支持 png, jpg, jpeg, gif, svg, webp, ico 格式，最大5MB</div>
            </a-tab-pane>
            <a-tab-pane key="url" tab="输入图片URL">
              <a-input
                v-model:value="editForm.logo_url"
                placeholder="https://example.com/logo.png"
                @input="onLogoUrlInput"
              />
              <div style="margin-top: 4px; color: #999; font-size: 12px;">支持 png, jpg, jpeg, gif, svg, webp, ico 格式的 URL</div>
              <div v-if="editForm.logo_url" style="margin-top: 8px;">
                <img :src="editForm.logo_url" alt="预览" style="max-width: 80px; max-height: 80px; object-fit: contain; border: 1px solid #d9d9d9; border-radius: 4px;" @error="onLogoUrlError" />
              </div>
            </a-tab-pane>
          </a-tabs>
          <div v-if="(editForm.logo || editForm.icon_url) && logoFileList.length === 0 && !editForm.logo_url" style="margin-top: 8px;">
            <img :src="editForm.logo || editForm.icon_url" alt="当前Logo" style="max-width: 80px; max-height: 80px; object-fit: contain; border: 1px solid #d9d9d9; border-radius: 4px;" />
            <div style="margin-top: 4px; color: #999; font-size: 12px;">当前Logo</div>
          </div>
        </a-form-item>
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
        <a-form-item label="官网">
          <a-input v-model:value="editForm.official_url" />
        </a-form-item>
        <a-form-item label="需要登录下载">
          <a-switch v-model:checked="editForm.require_login" />
          <div style="margin-top: 4px; color: #999; font-size: 12px;">关闭后，游客无需登录即可下载该软件</div>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import {
  DownloadOutlined,
  UploadOutlined,
  SafetyOutlined,
  EditOutlined,
  DeleteOutlined,
  LinkOutlined,
  LoginOutlined
} from '@ant-design/icons-vue'
import { softwareApi } from '@/api/software'
import { uploadApi } from '@/api/upload'
import { vulnerabilityApi } from '@/api/vulnerability'
import { categoryApi } from '@/api/category'
import { useUserStore } from '@/stores/user'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(true)
const software = ref(null)
const showVersionModal = ref(false)
const versionTab = ref('upload')  // 'upload' | 'url'
const uploadLoading = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref('active')
const uploadDetailText = ref('')
let activeSessionId = null
const versionForm = ref({
  version: '',
  release_notes: '',
  external_url: '',
  file_name: '',
  file_size: null
})
const fileList = ref([])
const logoFileList = ref([])
const logoTab = ref('upload')  // 'upload' | 'url'

// 软件界面图状态（3 个槽位）
const screenshotTabs = ref(['', '', ''])  // 每个 slot 当前激活的 tab
const screenshotUrlInputs = ref(['', '', ''])  // 每个 slot 的 URL 输入
const screenshotLoading = ref([false, false, false])  // 每个 slot 的 loading

const isEditVersionMode = ref(false)
const editingVersionId = ref(null)

const showVulnModal = ref(false)
const checkingVuln = ref(false)
const vulnerabilities = ref([])

const showEditModal = ref(false)
const editLoading = ref(false)
const editForm = ref({
  name: '',
  description: '',
  category: '',
  logo: '',
  icon_url: '',
  logo_url: '',
  official_url: '',
  require_login: true
})

const categories = ref([])

const downloadLogs = ref([])
const loadingDownloads = ref(false)

const versionColumns = [
  { title: '版本', key: 'version', dataIndex: 'version' },
  { title: '文件名', key: 'fileName', dataIndex: 'file_name' },
  { title: '文件大小', key: 'fileSize' },
  { title: 'SHA256', key: 'fileHash', dataIndex: 'file_hash' },
  { title: '下载次数', key: 'downloadCount', dataIndex: 'download_count' },
  { title: '原始下载地址', key: 'originalDownloadUrl', dataIndex: 'original_download_url' },
  { title: '上传时间', key: 'uploadTime' },
  { title: '操作', key: 'actions' }
]

const downloadColumns = [
  { title: '用户名', key: 'username', dataIndex: 'username' },
  { title: '版本', key: 'version', dataIndex: 'version' },
  { title: '下载时间', key: 'downloadTime', dataIndex: 'download_time' },
  { title: 'IP地址', key: 'ip_address', dataIndex: 'ip_address' }
]

const latestVersion = computed(() => {
  return software.value?.versions?.[0]
})

// 是否可以下载最新版（无需登录或已登录）
const canDownloadLatest = computed(() => {
  if (!software.value) return false
  return !software.value.require_login || userStore.token
})

// 是否可以下载指定版本（用于版本列表中的下载按钮）
const canDownloadRecord = computed(() => {
  if (!software.value) return false
  return !software.value.require_login || userStore.token
})

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

const formatDate = (date) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

const loadDetail = async () => {
  loading.value = true
  try {
    software.value = await softwareApi.getDetail(route.params.id)
  } catch (error) {
    message.error('加载软件详情失败')
  } finally {
    loading.value = false
  }
}

const goLogin = () => {
  router.push('/login')
}

const downloadLatest = () => {
  if (latestVersion.value) {
    downloadVersion(latestVersion.value)
  }
}

const downloadVersion = async (version) => {
  try {
    message.loading({ content: '准备下载...', key: 'download' })

    // 使用 fetch 下载文件，token 是可选的（游客也可下载无需登录的软件）
    const token = localStorage.getItem('token')
    const headers = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`/api/downloads/${version.id}`, { headers })

    if (response.status === 401) {
      message.error({ content: '该软件需要登录后才能下载', key: 'download' })
      return
    }

    if (!response.ok) {
      throw new Error('下载失败')
    }

    // 检查是否是 JSON 响应（外部下载地址）
    const contentType = response.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
      const data = await response.json()
      if (data.is_external && data.download_url) {
        // 外部地址：fallback 到官网地址或提供的下载链接
        const finalUrl = data.download_url || software.value?.official_url
        if (finalUrl) {
          window.open(finalUrl, '_blank')
          message.success({ content: '已打开下载页面', key: 'download' })
        } else {
          message.error({ content: '未提供下载地址', key: 'download' })
        }
        return
      }
    }

    // 创建 blob URL（文件下载）
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = version.file_name
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    message.success({ content: '下载开始', key: 'download' })
  } catch (error) {
    message.error({ content: '下载失败', key: 'download' })
  }
}

const beforeUpload = (file) => {
  fileList.value = [file]
  return false
}

const beforeLogoUpload = (file) => {
  // 检查文件类型
  const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/svg+xml', 'image/webp', 'image/x-icon']
  const isAllowedType = allowedTypes.includes(file.type) || file.name.match(/\.(png|jpe?g|gif|svg|webp|ico)$/i)

  if (!isAllowedType) {
    message.error('只支持上传图片文件（png, jpg, jpeg, gif, svg, webp, ico）')
    return false
  }

  // 检查文件大小（5MB）
  const isLt5M = file.size / 1024 / 1024 < 5
  if (!isLt5M) {
    message.error('Logo文件大小不能超过5MB')
    return false
  }

  logoFileList.value = [file]
  return false
}

const handleLogoRemove = () => {
  logoFileList.value = []
}

// 当用户输入 Logo URL 时，清空已上传的文件
const onLogoUrlInput = () => {
  if (editForm.value.logo_url) {
    logoFileList.value = []
  }
}

// 校验 Logo URL 格式
const isValidLogoUrl = (url) => {
  if (!url) return true
  return /\.(png|jpe?g|gif|svg|webp|ico)(\?.*)?$/i.test(url)
}

const onLogoUrlError = () => {
  message.error('Logo URL 加载失败，请检查地址是否正确')
}

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

const openEditModal = () => {
  logoFileList.value = []
  showEditModal.value = true
}

const computeFileHash = async (file) => {
  const buffer = await file.arrayBuffer()
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer)
  return Array.from(new Uint8Array(hashBuffer)).map(b => b.toString(16).padStart(2, '0')).join('')
}

const resetUploadForm = () => {
  versionForm.value = { version: '', release_notes: '', external_url: '', file_name: '', file_size: null }
  fileList.value = []
  uploadProgress.value = 0
  uploadStatus.value = 'active'
  uploadDetailText.value = ''
  versionTab.value = 'upload'
  activeSessionId = null
}

const handleUploadVersion = async () => {
  if (!versionForm.value.version) {
    message.error('请填写版本号')
    return
  }

  if (versionTab.value === 'upload') {
    // 上传文件模式
    if (fileList.value.length === 0) {
      message.error('请选择文件')
      return
    }
    await handleFileUpload()
  } else {
    // 外部地址模式
    await handleUrlUpload()
  }
}

const handleFileUpload = async () => {
  const file = fileList.value[0]
  const CHUNK_THRESHOLD = 50 * 1024 * 1024

  if (file.size < CHUNK_THRESHOLD) {
    uploadLoading.value = true
    try {
      const formData = new FormData()
      formData.append('version', versionForm.value.version)
      formData.append('file', file)
      formData.append('release_notes', versionForm.value.release_notes || '')
      await softwareApi.uploadVersion(route.params.id, formData)
      message.success('上传成功')
      showVersionModal.value = false
      resetUploadForm()
      loadDetail()
    } catch (error) {
      message.error('上传失败')
    } finally {
      uploadLoading.value = false
    }
  } else {
    await handleChunkedUpload(file)
  }
}

const handleUrlUpload = async () => {
  uploadLoading.value = true
  try {
    const formData = new FormData()
    formData.append('version', versionForm.value.version)
    formData.append('release_notes', versionForm.value.release_notes || '')
    if (versionForm.value.external_url) {
      formData.append('external_url', versionForm.value.external_url)
    }
    await softwareApi.uploadVersion(route.params.id, formData)
    message.success('版本添加成功')
    showVersionModal.value = false
    resetUploadForm()
    loadDetail()
  } catch (error) {
    message.error('版本添加失败: ' + (error.response?.data?.detail || '未知错误'))
  } finally {
    uploadLoading.value = false
  }
}

const openEditVersionModal = (version) => {
  isEditVersionMode.value = true
  editingVersionId.value = version.id
  versionForm.value = {
    version: version.version,
    release_notes: version.release_notes || '',
    external_url: version.original_download_url || '',
    file_name: version.file_name || '',
    file_size: version.file_size || null
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
    // 手动设置的 file_name 和 file_size
    if (versionForm.value.file_name) {
      formData.append('file_name', versionForm.value.file_name)
    }
    if (versionForm.value.file_size !== null && versionForm.value.file_size !== undefined) {
      formData.append('file_size', versionForm.value.file_size)
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

const handleChunkedUpload = async (file) => {
  uploading.value = true
  uploadProgress.value = 1
  uploadStatus.value = 'active'
  activeSessionId = null

  const CHUNK_SIZE = uploadApi.CHUNK_SIZE
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE)

  try {
    uploadDetailText.value = '正在计算文件校验值...'
    const fileHash = await computeFileHash(file)

    uploadDetailText.value = '正在初始化上传...'
    const initResult = await uploadApi.init({
      software_id: parseInt(route.params.id),
      file_name: file.name,
      file_size: file.size,
      file_hash: fileHash,
      total_chunks: totalChunks,
      chunk_size: CHUNK_SIZE,
      version: versionForm.value.version,
      release_notes: versionForm.value.release_notes || ''
    })
    activeSessionId = initResult.session_id

    for (let i = 0; i < totalChunks; i++) {
      const start = i * CHUNK_SIZE
      const end = Math.min(start + CHUNK_SIZE, file.size)
      const chunk = file.slice(start, end)
      uploadDetailText.value = `正在上传分片 ${i + 1} / ${totalChunks}`

      await uploadApi.uploadChunk(activeSessionId, i, chunk, (e) => {
        const chunkPct = e.loaded / e.total
        uploadProgress.value = Math.round(((i + chunkPct) / totalChunks) * 100)
      })
      uploadProgress.value = Math.round(((i + 1) / totalChunks) * 100)
    }

    uploadDetailText.value = '正在合并文件...'
    uploadProgress.value = 100

    await uploadApi.complete(activeSessionId)
    uploadStatus.value = 'success'
    message.success('上传成功')
    showVersionModal.value = false
    resetUploadForm()
    loadDetail()
  } catch (error) {
    uploadStatus.value = 'exception'
    message.error('上传失败: ' + (error.response?.data?.detail || '未知错误'))
    if (activeSessionId) {
      try { await uploadApi.cancel(activeSessionId) } catch {}
    }
  } finally {
    uploading.value = false
  }
}

const checkVulnerability = async (version) => {
  showVulnModal.value = true
  checkingVuln.value = true
  try {
    vulnerabilities.value = await vulnerabilityApi.check(route.params.id, version.version)
  } catch (error) {
    console.error('检查漏洞失败:', error)
  } finally {
    checkingVuln.value = false
  }
}

const getSeverityColor = (severity) => {
  const colors = {
    critical: 'red',
    high: 'orange',
    medium: 'yellow',
    low: 'blue'
  }
  return colors[severity] || 'default'
}

const loadDownloadLogs = async () => {
  if (!userStore.isOps()) return
  loadingDownloads.value = true
  try {
    const versionIds = software.value?.versions?.map(v => v.id) || []
    const allLogs = []
    for (const vid of versionIds) {
      const logs = await softwareApi.getDownloadLogs(vid)
      if (Array.isArray(logs)) {
        allLogs.push(...logs)
      } else if (logs && Array.isArray(logs.items)) {
        allLogs.push(...(logs.items || []))
      }
    }
    downloadLogs.value = allLogs
  } catch (error) {
    console.error('加载下载记录失败:', error)
    downloadLogs.value = []
  } finally {
    loadingDownloads.value = false
  }
}

const handleEdit = async () => {
  if (!editForm.value.name) {
    message.error('请输入软件名称')
    return
  }
  // 校验 Logo URL（如有）
  if (editForm.value.logo_url && !isValidLogoUrl(editForm.value.logo_url)) {
    message.error('Logo URL 格式不正确，仅支持 png, jpg, jpeg, gif, svg, webp, ico')
    return
  }
  editLoading.value = true

  try {
    if (logoFileList.value.length > 0) {
      await softwareApi.uploadLogo(route.params.id, logoFileList.value[0])
    }

    const cleanedData = {
      name: editForm.value.name,
      description: editForm.value.description,
      category: editForm.value.category,
      icon_url: editForm.value.logo_url?.trim() || null,
      official_url: editForm.value.official_url?.trim() || null,
      require_login: editForm.value.require_login
    }

    await softwareApi.update(route.params.id, cleanedData)
    message.success('更新成功')
    showEditModal.value = false
    logoFileList.value = []
    editForm.value.logo_url = ''
    logoTab.value = 'upload'
    loadDetail()
  } catch (error) {
    if (error.response?.data?.detail) {
      const errorDetail = error.response.data.detail
      if (Array.isArray(errorDetail)) {
        const firstError = errorDetail[0]
        if (firstError.msg && firstError.msg.includes('URL')) {
          message.error('请输入有效的URL地址')
        } else {
          message.error(firstError.msg || '更新失败')
        }
      } else {
        message.error(errorDetail || '更新失败')
      }
    } else {
      message.error('更新失败，请检查输入信息')
    }
  } finally {
    editLoading.value = false
  }
}

const handleDelete = () => {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除软件"${software.value?.name}"吗？此操作不可恢复。`,
    onOk: () => {
      softwareApi.delete(route.params.id)
        .then(() => {
          message.success('删除成功')
          router.push('/software')
        })
        .catch(() => {
          message.error('删除失败')
        })
    }
  })
}

const handleDeleteVersion = (version) => {
  Modal.confirm({
    title: '确认删除版本',
    content: `确定要删除版本"${version.version}"吗？此操作不可恢复，文件将被永久删除。`,
    okText: '确认删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      try {
        await softwareApi.deleteVersion(route.params.id, version.id)
        message.success('版本删除成功')
        loadDetail()
      } catch (error) {
        message.error('删除失败: ' + (error.response?.data?.detail || '未知错误'))
      }
    }
  })
}

watch(software, () => {
  if (software.value) {
    editForm.value = {
      name: software.value.name,
      description: software.value.description || '',
      category: software.value.category || '',
      logo: software.value.logo || '',
      icon_url: software.value.icon_url || '',
      logo_url: '',
      official_url: software.value.official_url || '',
      require_login: software.value.require_login !== false
    }
    loadDownloadLogs()
  }
})

const loadCategories = async () => {
  try {
    categories.value = await categoryApi.getAllNames()
  } catch (error) {
    console.error('加载软件类型失败:', error)
  }
}

onMounted(() => {
  loadCategories()
  loadDetail()
})
</script>

<style scoped>
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
</style>
