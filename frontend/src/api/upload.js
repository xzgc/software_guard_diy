import api from './index'

const CHUNK_SIZE = 5 * 1024 * 1024  // 5MB

export const uploadApi = {
  CHUNK_SIZE,

  // 初始化分块上传会话
  init(data) {
    return api.post('/upload/init', data)
  },

  // 上传单个分片
  uploadChunk(sessionId, chunkIndex, chunk, onProgress) {
    const formData = new FormData()
    formData.append('chunk', chunk)
    return api.put(`/upload/${sessionId}/chunk/${chunkIndex}`, formData, {
      timeout: 0,
      onUploadProgress: onProgress
    })
  },

  // 完成上传
  complete(sessionId) {
    return api.post(`/upload/${sessionId}/complete`)
  },

  // 取消上传
  cancel(sessionId) {
    return api.post(`/upload/${sessionId}/cancel`)
  }
}
