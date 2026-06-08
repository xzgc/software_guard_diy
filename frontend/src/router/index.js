import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useSiteStore } from '@/stores/site'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  // 主应用布局（顶部导航栏）
  {
    path: '/',
    component: () => import('@/views/AppLayout.vue'),
    meta: { requiresAuth: false, allowGuest: true },  // 允许游客访问
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('@/views/Software/List.vue'),
        meta: { requiresAuth: false, allowGuest: true }
      },
      {
        path: 'software',
        name: 'SoftwareList',
        component: () => import('@/views/Software/List.vue'),
        meta: { requiresAuth: false, allowGuest: true }
      },
      {
        path: 'software/:id',
        name: 'SoftwareDetail',
        component: () => import('@/views/Software/Detail.vue'),
        meta: { requiresAuth: false, allowGuest: true }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/Profile.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'requests',
        name: 'Requests',
        component: () => import('@/views/Requests.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'my-downloads',
        name: 'MyDownloads',
        component: () => import('@/views/MyDownloads.vue'),
        meta: { requiresAuth: true }
      }
    ]
  },
  // 管理后台布局（左侧边栏）
  {
    path: '/admin',
    component: () => import('@/views/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    redirect: '/admin/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'AdminDashboard',
        component: () => import('@/views/Admin/Dashboard.vue')
      },
      {
        path: 'requests',
        name: 'AdminRequests',
        component: () => import('@/views/Admin/Requests.vue')
      },
      {
        path: 'vulnerabilities',
        name: 'AdminVulnerabilities',
        component: () => import('@/views/Admin/Vulnerabilities.vue')
      },
      {
        path: 'categories',
        name: 'AdminCategories',
        component: () => import('@/views/Admin/Categories.vue')
      },
      {
        path: 'config',
        name: 'AdminConfig',
        component: () => import('@/views/Admin/Config.vue')
      },
      {
        path: 'users',
        name: 'AdminUsers',
        component: () => import('@/views/Admin/Users.vue'),
        meta: { requiresSuperAdmin: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  const siteStore = useSiteStore()

  // 1. 检查需要登录的页面
  if (to.meta.requiresAuth && !userStore.token) {
    next('/login')
    return
  }

  // 2. 检查允许游客的页面（如果配置不允许游客访问且未登录，跳转登录）
  if (to.meta.allowGuest && !userStore.token && !siteStore.allowGuestAccess) {
    next('/login')
    return
  }

  // 3. 检查管理员权限
  if (to.meta.requiresAdmin && !userStore.isOps()) {
    next('/')
    return
  }

  // 4. 检查超级管理员权限
  if (to.meta.requiresSuperAdmin && !userStore.isAdmin()) {
    next('/admin')
    return
  }

  // 5. 已登录访问登录页时跳转首页
  if (to.path === '/login' && userStore.token) {
    next('/')
    return
  }

  next()
})

export default router
