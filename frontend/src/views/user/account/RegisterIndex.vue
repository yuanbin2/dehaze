<script setup>

import {useUserStore} from "@/stores/user.js";
import {useRouter} from "vue-router";
import {ref} from "vue";
import api from "@/js/http/api.js";

const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const errorMessage = ref('')

const user = useUserStore()
const router = useRouter()

async function handleRegister(){
  errorMessage.value = ''
  if(!username.value.trim()){
    errorMessage.value = '用户名不能为空'
  }else if(!password.value.trim()){
    errorMessage.value = '密码不能为空'
  }else if(password.value !== confirmPassword.value){
    errorMessage.value = '两次密码不一致'
  }else{
    try {
      const res = await api.post('/api/user/account/register/', {
        username: username.value,
        password: password.value,
      })

      const data = res.data
      if(data.result === 'success'){
        user.setAccessToken(data.access)
        user.setUserInfo(data)
        await router.push({name: 'user-account-login-index'})

      }else{
        errorMessage.value = data.result
      }
    }catch (err){
      errorMessage.value = err
      // console.log(err)
    }
  }
}

</script>

<template>
<div class="flex justify-center mt-30">
    <form @submit.prevent="handleRegister" class="fieldset bg-base-200 border-base-300 rounded-box w-xs border p-4">
      <legend class="fieldset-legend">register</legend>

      <label class="label">用户名</label>
      <input v-model="username" type="text" class="input" placeholder="Username" />

      <label class="label">密码</label>
      <input v-model="password" type="password" class="input" placeholder="Password" />

      <label class="label">确认密码</label>
      <input v-model="confirmPassword" type="password" class="input" placeholder="ConfirmPassword" />
      <p v-if="errorMessage"  class="text-base text-red-500">{{errorMessage}}</p>
      <button class="btn btn-neutral mt-4">register</button>
      <RouterLink :to="{name: 'user-account-login-index'}" class="flex justify-end text-base">登录</RouterLink>

    </form>
  </div>
</template>

<style scoped>

</style>