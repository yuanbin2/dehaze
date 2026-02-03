<script setup>

import {ref} from "vue";
import {useUserStore} from "@/stores/user.js";
import {useRouter} from "vue-router";
import api from "@/js/http/api.js";

const username = ref('')
const password = ref('')
const errorMessage = ref('')

const user = useUserStore()
const router = useRouter()

async function handleLogin(){
  errorMessage.value = ''
  if(!username.value.trim()){
    errorMessage.value = '用户名不能为空'
  }else if(!password.value.trim()){
    errorMessage.value = '密码不能为空'
  }else{
    try{
      const res = await api.post('/api/user/account/login/', {
        username: username.value,
        password: password.value
      })
      const data = res.data
      if(data.result === 'success'){
        console.log(data)
        user.setAccessToken(data.access)
        user.setUserInfo(data)
        await router.push({
          name: 'homepage-index'
        })
      }else{
        errorMessage.value = data.result
      }
    }catch(err){
      console.log(err)
    }
  }

}
</script>

<template>
  <div class="flex justify-center mt-30">
    <form @submit.prevent="handleLogin" class="fieldset bg-base-200 border-base-300 rounded-box w-xs border p-4">
      <legend class="fieldset-legend">Login</legend>

      <label class="label">用户名</label>
      <input v-model="username" class="input" placeholder="Username" />

      <label class="label">密码</label>
      <input v-model="password" type="password" class="input" placeholder="Password" />
      <p v-if="errorMessage" class="text-base text-red-500">{{errorMessage}}</p>
      <button class="btn btn-neutral mt-4">Login</button>
      <RouterLink :to="{name: 'user-account-register-index'}" class="flex justify-end text-base">注册</RouterLink>
    </form>
  </div>

</template>

<style scoped>

</style>