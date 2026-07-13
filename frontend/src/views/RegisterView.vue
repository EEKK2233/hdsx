<script setup lang="ts">
import{ref}from'vue'
import{useRouter}from'vue-router'
import{api}from'../api/client'
const router=useRouter(),form=ref({username:'',display_name:'',email:'',password:'',confirm:''}),error=ref(''),success=ref(''),loading=ref(false)
async function submit(){error.value='';if(form.value.password!==form.value.confirm){error.value='两次输入的密码不一致';return}loading.value=true;try{await api.post('/auth/register',{username:form.value.username,display_name:form.value.display_name,email:form.value.email||null,password:form.value.password});success.value='注册成功，即将前往登录';setTimeout(()=>router.push('/login'),800)}catch(e:any){error.value=e.message}finally{loading.value=false}}
</script>
<template><div class="login card"><h1>注册学生账号</h1><p>注册后可申请加入课程，审批通过后查看课程资料和作业。</p><form @submit.prevent="submit"><label>用户名<input v-model="form.username" required placeholder="字母、数字、下划线"></label><label>姓名<input v-model="form.display_name" required></label><label>邮箱（可选）<input type="email" v-model="form.email"></label><label>密码<input type="password" minlength="8" v-model="form.password" required></label><label>确认密码<input type="password" v-model="form.confirm" required></label><p class="error">{{error}}</p><p class="success">{{success}}</p><button :disabled="loading">{{loading?'注册中…':'注册'}}</button> <router-link to="/login">已有账号，返回登录</router-link></form></div></template>
