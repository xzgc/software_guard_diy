import { defineStore } from 'pinia'
import axios from 'axios'

export const useSiteStore = defineStore('site', {
  state: () => ({
    name: 'Software Guard',
    description: '公司内网软件下载站',
    allowGuestAccess: true,  // 是否允许游客访问（默认 true）
    loaded: false
  }),
  actions: {
    async load() {
      if (this.loaded) return
      try {
        const res = await axios.get('/api/site/info')
        this.name = res.data.name
        this.description = res.data.description
        this.allowGuestAccess = res.data.allow_guest_access ?? true
        document.title = `${this.name} - ${this.description}`
      } catch {
        // 使用默认值
      } finally {
        this.loaded = true
      }
    },
    setName(name) {
      this.name = name
      document.title = `${this.name} - ${this.description}`
    },
    setDescription(desc) {
      this.description = desc
      document.title = `${this.name} - ${this.description}`
    },
    setAllowGuestAccess(allow) {
      this.allowGuestAccess = allow
    }
  }
})
