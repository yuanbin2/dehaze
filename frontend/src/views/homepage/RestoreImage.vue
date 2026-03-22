<script setup>
import { ref } from "vue";
import api from "@/js/http/api.js";

// 定义状态变量
const selectedFile = ref(null);         // 实际上传的文件对象
const originalImageUrl = ref('');       // 前端预览原图的本地临时链接
const restoredImageUrl = ref('');       // 后端返回的恢复后的图像链接
const isLoading = ref(false);           // 是否正在请求后端的加载状态
const isDownloading = ref(false);       // 是否正在处理下载
const errorMessage = ref('');           // 错误信息提示

// 1. 处理用户选择文件的事件
const handleFileChange = (e) => {
  // 如果正在处理，禁止更换
  if (isLoading.value) return;

  const file = e.target.files[0];
  if (file) {
    selectedFile.value = file;
    originalImageUrl.value = URL.createObjectURL(file);
    
    restoredImageUrl.value = '';
    errorMessage.value = '';
  }
};

// 2. 发起 API 请求，恢复图像
async function handleRestore() {
  errorMessage.value = '';
  
  if (!selectedFile.value) {
    errorMessage.value = '请先选择一张图片';
    return;
  }

  isLoading.value = true;

  try {
    const formData = new FormData();
    formData.append('image', selectedFile.value);

    const res = await api.post('/api/restore_image/', formData);
    const data = res.data;
    
    if (data.result === 'success') {
      // 假设后端返回完整 URL，如果是相对路径需自行拼接
      restoredImageUrl.value = data.image_url; 
    } else {
      errorMessage.value = data.result || '图像恢复失败';
    }
  } catch (err) {
    errorMessage.value = '系统异常或网络错误，请稍后重试';
    console.error("恢复图片报错:", err);
  } finally {
    isLoading.value = false;
  }
}

// 3. 处理图片保存逻辑
async function handleDownload() {
  if (!restoredImageUrl.value) return;
  
  isDownloading.value = true;
  errorMessage.value = '';

  try {
    // 【关键】通过 fetch 获取 Blob，解决跨域图片无法强制下载的问题
    const response = await fetch(restoredImageUrl.value);
    if (!response.ok) throw new Error('网络请求失败，无法获取图像');
    const blob = await response.blob();
    
    // 生成默认文件名
    const defaultFilename = `restored_image_${Date.now()}.png`;

    // 方案 A: 尝试使用现代 File System Access API (让用户自主选择保存位置)
    if ('showSaveFilePicker' in window) {
      const opts = {
        suggestedName: defaultFilename,
        types: [{
          description: 'Images',
          accept: { 'image/png': ['.png'], 'image/jpeg': ['.jpg', '.jpeg'] },
        }],
      };
      
      // 弹出系统的“另存为”对话框
      const handle = await window.showSaveFilePicker(opts);
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      
      // 用户选择位置并保存成功后，可做轻量提示（如 Toast），这里用 alert 演示
      // alert('保存成功！'); 
      
    } else {
      // 方案 B: 降级方案 (传统 a 标签下载，默认存入浏览器的下载文件夹)
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = defaultFilename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  } catch (err) {
    // 如果用户在“另存为”对话框点了取消，会抛出 AbortError，不需要当做错误处理
    if (err.name !== 'AbortError') {
      console.error("保存图片报错:", err);
      errorMessage.value = '图片保存失败，请检查网络或跨域设置';
    }
  } finally {
    isDownloading.value = false;
  }
}
</script>

<template>
  <div class="flex flex-col items-center mt-10 p-4 min-h-screen bg-base-100">
    <h2 class="text-3xl font-black mb-8 text-primary">图像恢复工具</h2>

    <div class="card w-full max-w-xl bg-base-200 shadow-xl p-6 mb-10 border border-base-300">
      <div class="form-control w-full">
        <label class="label"><span class="label-text font-bold">选择需要恢复的图像</span></label>
        
        <input 
          type="file" 
          accept="image/*" 
          :disabled="isLoading"
          :class="['file-input file-input-bordered file-input-primary w-full mb-4', isLoading ? 'opacity-50 cursor-not-allowed' : '']" 
          @change="handleFileChange" 
        />
      </div>
      
      <p v-if="errorMessage" class="text-error text-sm mb-4 font-bold text-center">{{ errorMessage }}</p>
      
      <button 
        class="btn btn-primary w-full" 
        :disabled="!selectedFile || isLoading"
        @click="handleRestore"
      >
        <span v-if="isLoading" class="loading loading-spinner"></span>
        {{ isLoading ? 'AI 计算中...' : '开始恢复图像' }}
      </button>

      <button 
        v-if="restoredImageUrl" 
        class="btn btn-success w-full mt-4 text-white shadow-lg animate-in fade-in"
        :disabled="isDownloading"
        @click="handleDownload"
      >
        <span v-if="isDownloading" class="loading loading-spinner"></span>
        {{ isDownloading ? '正在保存...' : '保存恢复后的图像' }}
      </button>
    </div>

    <div class="flex flex-col md:flex-row gap-8 w-full max-w-6xl justify-center">
      
      <div class="flex-1 flex flex-col border border-base-300 rounded-3xl overflow-hidden shadow-lg bg-black">
        <div class="bg-base-300 p-3 text-center font-bold text-[10px] uppercase opacity-60 tracking-widest">原始图像</div>
        <div class="h-80 flex items-center justify-center bg-zinc-950 p-4 relative group">
          <img v-if="originalImageUrl" :src="originalImageUrl" class="max-h-full max-w-full object-contain" alt="原图预览" />
          <span v-else class="text-zinc-700 italic text-sm">Waiting for upload...</span>
        </div>
      </div>

      <div class="flex-1 flex flex-col border border-base-300 rounded-3xl overflow-hidden shadow-lg bg-black relative">
        <div class="bg-primary p-3 text-center font-bold text-[10px] text-primary-content uppercase tracking-widest flex justify-between px-6">
          <span>恢复结果</span>
        </div>
        
        <div class="h-80 flex items-center justify-center p-4 relative bg-zinc-900 group">
          
          <div v-if="isLoading" class="flex flex-col items-center text-primary">
            <span class="loading loading-infinity loading-lg mb-2"></span>
            <span class="text-[10px] uppercase font-bold">AI 正在努力计算...</span>
          </div>
          
          <img v-else-if="restoredImageUrl" :src="restoredImageUrl" class="max-h-full max-w-full object-contain transition-transform group-hover:scale-[1.02]" alt="恢复后图像" />
          
          <span v-else-if="!isLoading" class="text-zinc-700 italic text-sm">No data available...</span>

          <button 
            v-if="restoredImageUrl"
            @click="handleDownload"
            class="absolute bottom-4 right-4 btn btn-sm btn-circle btn-primary opacity-0 group-hover:opacity-100 transition-opacity shadow-xl"
            title="保存图片"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
          </button>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.file-input:disabled { background-color: hsl(var(--b3)); }
</style>