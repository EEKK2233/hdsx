<script setup lang="ts">
import{computed,onActivated,ref}from'vue'
import{useRoute}from'vue-router'
import{api}from'../api/client'
import{renderMarkdown}from'../utils/markdown'
const route=useRoute(),item=ref<any>(),error=ref('')
const markdown=computed(()=>{const value=item.value?.content?.text||item.value?.content||'';return typeof value==='string'?value:JSON.stringify(value,null,2)})
const html=computed(()=>renderMarkdown(markdown.value))
const back=computed(()=>route.query.from==='favorites'?'/lesson/favorites':'/lesson')
async function load(){item.value=(await api.get(`/lesson-resources/${route.params.resourceId}`)).data}
async function download(){const response=await api.get(`/lesson-resources/${item.value.id}/download`,{responseType:'blob'});const url=URL.createObjectURL(response.data),link=document.createElement('a');link.href=url;link.download=`${item.value.title}.md`;link.click();URL.revokeObjectURL(url)}
onActivated(()=>load().catch((e:any)=>error.value=e.message))
</script>
<template><div class="page"><div class="page-title"><div><span class="eyebrow">{{item?.course_name}}</span><h1>{{item?.title||'备课文件预览'}}</h1><p>Markdown 已按最终阅读效果渲染；下载仍保留原始 Markdown 内容。</p></div><div class="inline-actions"><router-link class="button-link secondary" :to="back">← 返回{{route.query.from==='favorites'?'收藏':'智能备课'}}</router-link><button v-if="item" @click="download">下载 Markdown</button></div></div><p v-if="error" class="notice error">{{error}}</p><article v-if="item" class="card markdown-preview" v-html="html"></article></div></template>
