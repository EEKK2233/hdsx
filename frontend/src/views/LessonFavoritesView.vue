<script setup lang="ts">
import{onActivated,ref}from'vue'
import{api}from'../api/client'
const items=ref<any[]>([]),preview=ref<any>(),message=ref('')
async function load(){items.value=((await api.get('/lesson-resources')).data as any[]).filter(x=>x.is_saved)}
function text(item:any){const value=item?.content?.text||item?.content||'';return typeof value==='string'?value:JSON.stringify(value,null,2)}
async function unFavorite(item:any){await api.patch(`/lesson-resources/${item.id}/save?saved=false`);message.value='已取消收藏';await load()}
async function remove(item:any){if(!confirm(`确定删除《${item.title}》吗？`))return;await api.delete(`/lesson-resources/${item.id}`);preview.value=undefined;await load()}
async function download(item:any){const response=await api.get(`/lesson-resources/${item.id}/download`,{responseType:'blob'});const url=URL.createObjectURL(response.data),link=document.createElement('a');link.href=url;link.download=`${item.title}.md`;link.click();URL.revokeObjectURL(url)}
onActivated(()=>load())
</script>
<template><div class="page"><div class="page-title"><div><h1>备课收藏</h1><p>预览、下载、取消收藏或删除已收藏的备课内容。</p></div><router-link class="button-link secondary" to="/lesson">← 返回智能备课</router-link></div><p v-if="message" class="notice success-box">{{message}}</p><div v-if="!items.length" class="card empty">暂无收藏内容</div><div class="lesson-favorite-grid"><article v-for="item in items" :key="item.id" class="card"><span class="history-star saved">★ 已收藏</span><h2>{{item.title}}</h2><p class="muted">{{item.course_name}} · {{new Date(item.created_at).toLocaleString()}}</p><div class="lesson-actions"><button @click="preview=item">预览</button><button class="favorite-button" @click="unFavorite(item)">☆ 取消收藏</button><button class="secondary" @click="download(item)">下载</button><button class="danger" @click="remove(item)">删除</button></div></article></div><div v-if="preview" class="modal-backdrop" @click.self="preview=undefined"><article class="modal wide"><button class="modal-close" @click="preview=undefined">×</button><h2>{{preview.title}}</h2><div class="lesson-text">{{text(preview)}}</div></article></div></div></template>
