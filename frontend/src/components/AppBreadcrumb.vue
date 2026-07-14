<script setup lang="ts">
import{computed}from'vue'
import{useRoute}from'vue-router'
const props=defineProps<{label:string}>(),route=useRoute()
const parts=computed(()=>{const values:any[]=[{label:props.label,to:route.params.courseId?`/${String(route.path).split('/')[1]}`:undefined}];if(route.params.courseId)values.push({label:String(route.query.courseName||`课程 ${route.params.courseId}`),to:route.params.assignmentId?route.path.replace(/\/assignment\/.*$/,''):undefined});if(route.params.assignmentId)values.push({label:String(route.query.assignmentTitle||`作业 ${route.params.assignmentId}`)});if(route.path==='/lesson/favorites')values.push({label:'收藏'});return values})
</script>
<template><nav class="breadcrumb" aria-label="当前位置"><router-link to="/">工作台</router-link><template v-for="part in parts"><span>›</span><router-link v-if="part.to" :to="{path:part.to,query:{courseName:route.query.courseName}}">{{part.label}}</router-link><strong v-else>{{part.label}}</strong></template></nav></template>
