<script setup lang="ts">
defineProps<{displayName?:string;roleLabel?:string}>()
defineEmits<{logout:[]}>()
</script>
<template><div class="account-actions"><span>{{displayName}} · {{roleLabel}}</span><button class="logout-button" @click="$emit('logout')">退出登录</button></div></template>
