import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import router from './router'
import App from './App.vue'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(Antd)

// 同步加载站点配置，确保路由守卫可以正确判断
import { useSiteStore } from './stores/site'
const siteStore = useSiteStore()
siteStore.load().then(() => {
  app.mount('#app')
})
