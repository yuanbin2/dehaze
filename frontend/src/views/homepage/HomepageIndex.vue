<script setup>
import { ref } from "vue";
import RestoreImage from "@/views/homepage/RestoreImage.vue";
import RestoreVideo from "@/views/homepage/RestoreVideo.vue";

// 定义当前激活的选项卡，默认为 'image'
const activeTab = ref('image'); 
</script>

<template>
  <div class="min-h-screen bg-base-100 p-6">
    
    <div class="flex flex-col items-center mb-8">
      <h1 class="text-3xl font-bold mb-6">AI 多媒体恢复中心</h1>
      
      <div class="tabs tabs-boxed bg-base-200 p-1">
        <a 
          class="tab text-lg px-8 transition-all" 
          :class="{ 'tab-active bg-primary text-white': activeTab === 'image' }"
          @click="activeTab = 'image'"
        >
          🖼️ 恢复图片
        </a>
        <a 
          class="tab text-lg px-8 transition-all" 
          :class="{ 'tab-active bg-primary text-white': activeTab === 'video' }"
          @click="activeTab = 'video'"
        >
          🎬 恢复视频
        </a>
      </div>
    </div>

    <div class="w-full transition-opacity duration-300">
      <RestoreImage v-if="activeTab === 'image'" />
      
      <RestoreVideo v-if="activeTab === 'video'" />
    </div>
    
  </div>
</template>

<style scoped>
/* 如果你需要覆盖 DaisyUI 的默认 tab 颜色，可以在这里写 */
</style>