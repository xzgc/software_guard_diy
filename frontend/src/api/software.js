import api from './index'

export const softwareApi = {
  // 获取软件列表
  list(params) {
    return api.get('/software', { params })
  },

  // 获取软件详情
  getDetail(id) {
    return api.get(`/software/${id}`)
  },

  // 创建软件
  create(data) {
    return api.post('/software', data)
  },

  // 更新软件
  update(id, data) {
    return api.put(`/software/${id}`, data)
  },

  // 删除软件
  delete(id) {
    return api.delete(`/software/${id}`)
  },

  // 上传软件版本
  uploadVersion(softwareId, data, onUploadProgress) {
    return api.post(`/software/${softwareId}/versions`, data, {
      timeout: 0,
      onUploadProgress
    })
  },

  // 删除软件版本
  deleteVersion(softwareId, versionId) {
    return api.delete(`/software/${softwareId}/versions/${versionId}`)
  },

  // 编辑软件版本（仅 admin）
  updateVersion(softwareId, versionId, formData, onUploadProgress) {
    return api.put(`/software/${softwareId}/versions/${versionId}`, formData, {
      timeout: 0,
      onUploadProgress
    })
  },

  // 获取分类列表
  getCategories() {
    return api.get('/software/categories')
  },

  // 获取版本的下载记录
  getDownloadLogs(versionId) {
    return api.get(`/downloads/logs?version_id=${versionId}`)
  },

  // 上传Logo
  uploadLogo(softwareId, file) {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/software/${softwareId}/logo`, formData)
  },

  // 上传/设置软件界面图
  uploadScreenshot(softwareId, slot, formData) {
    return api.post(`/software/${softwareId}/screenshots`, formData)
  },

  // 删除软件界面图
  deleteScreenshot(softwareId, slot) {
    return api.delete(`/software/${softwareId}/screenshots/${slot}`)
  }
}
