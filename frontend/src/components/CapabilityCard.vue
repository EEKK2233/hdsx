<script setup lang="ts">
defineProps<{name:string;version:string;description:string;tags?:string[]}>()
</script>
<template><article class="capability-card"><div><strong>{{name}}</strong><span class="badge">v{{version}}</span></div><p>{{description}}</p><div class="capability-tags"><span v-for="tag in tags" :key="tag">{{tag}}</span><span v-if="!tags?.length">无外部工具</span></div><slot/></article></template>
