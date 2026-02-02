<script setup>

</script>

<template>
<div class="flex justify-center mt-30">
    <fieldset class="fieldset bg-base-200 border-base-300 rounded-box w-xs border p-4">
      <legend class="fieldset-legend">register</legend>

      <label class="label">用户名</label>
      <input type="email" class="input" placeholder="Username" />

      <label class="label">密码</label>
      <input type="password" class="input" placeholder="Password" />

      <label class="label">确认密码</label>
      <input type="password" class="input" placeholder="ConfirmPassword" />

      <button class="btn btn-neutral mt-4">register</button>
      <RouterLink :to="{name: 'user-account-login-index'}" class="flex justify-end text-base">登录</RouterLink>

    </fieldset>
  </div>
</template>

<style scoped>

</style>