<script setup lang="ts">
import {computed,onMounted} from 'vue'
import {useAuthStore} from './stores/auth'
import {useRoute} from 'vue-router'
import AppBreadcrumb from './components/AppBreadcrumb.vue'
import AccountActions from './components/AccountActions.vue'
const auth=useAuthStore(),route=useRoute()
onMounted(()=>auth.load().catch(()=>{}))
const labels:{[key:string]:string}={admin:'管理员',teacher:'教师',student:'学生',parent:'家长'}
const allNav=[
  {to:'/',label:'总览',roles:['admin','teacher','student','parent']},{to:'/profile',label:'账号设置',roles:['admin','teacher','student','parent']},
  {to:'/courses',label:'课程',roles:['admin','teacher','student']},{to:'/knowledge',label:'知识库',roles:['admin','teacher','student']},
  {to:'/lesson',label:'智能备课',roles:['admin','teacher']},{to:'/assignments',label:'作业中心',roles:['admin','teacher','student']},
  {to:'/chat',label:'课堂答疑',roles:['admin','teacher','student']},{to:'/classroom-ops',label:'课堂运营',roles:['admin','teacher']},
  {to:'/analytics',label:'学情分析',roles:['admin','teacher','student']},{to:'/reports',label:'学习报告',roles:['admin','teacher','parent']},
  {to:'/notifications',label:'通知中心',roles:['admin','teacher','student','parent']},
  {to:'/agent-capabilities',label:'Agent 能力',roles:['admin']}
]
const nav=computed(()=>allNav.filter(n=>auth.user&&n.roles.includes(auth.user.role)))
const isPublic=computed(()=>['/login','/register'].includes(route.path))
const currentLabel=computed(()=>allNav.find(item=>item.to===route.path)?.label||'功能页面')
</script>
<template><div class="shell"><aside v-if="!isPublic"><div class="brand">Edu Agent<small>{{labels[auth.user?.role||'']}}工作台</small></div><router-link v-for="n in nav" :to="n.to" :key="n.to">{{n.label}}</router-link></aside><main><header v-if="!isPublic" class="topbar"><AppBreadcrumb :label="currentLabel"/><AccountActions :display-name="auth.user?.display_name" :role-label="labels[auth.user?.role||'']" @logout="auth.logout"/></header><router-view v-slot="{Component}"><keep-alive :max="16"><component :is="Component"/></keep-alive></router-view></main></div></template>
