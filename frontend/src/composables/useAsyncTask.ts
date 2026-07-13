import {ref} from 'vue'
export function useAsyncTask(){const loading=ref(false),error=ref('');async function run<T>(task:()=>Promise<T>):Promise<T|undefined>{loading.value=true;error.value='';try{return await task()}catch(reason){error.value=reason instanceof Error?reason.message:'请求失败'}finally{loading.value=false}}return{loading,error,run}}
