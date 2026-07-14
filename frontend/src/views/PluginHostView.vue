<script setup lang="ts">
import{onActivated,ref}from'vue'
import{useRoute}from'vue-router'
import{api}from'../api/client'
const route=useRoute(),plugin=ref<any>(),error=ref('')
async function load(){const rows=(await api.get('/plugins')).data as any[];plugin.value=rows.find(x=>x.id===route.params.pluginId);if(!plugin.value)error.value='插件未启用、没有界面或当前账号无权访问。'}
onActivated(()=>load().catch((e:any)=>error.value=e.message))
</script>
<template><div class="page"><div class="page-title"><div><h1>{{plugin?.name||'插件功能'}}</h1><p>{{plugin?.description}}</p></div></div><p v-if="error" class="notice error">{{error}}</p><iframe v-if="plugin?.has_ui" class="plugin-frame" :src="plugin.ui_url" :title="plugin.name"></iframe><div v-else-if="plugin&&!plugin.has_ui" class="card empty">该插件只提供 API，没有独立页面。</div></div></template>
