<script setup lang="ts">
defineProps<{label:string}>()
</script>
<template><nav class="breadcrumb" aria-label="当前位置"><router-link to="/">工作台</router-link><span>›</span><strong>{{label}}</strong></nav></template>
