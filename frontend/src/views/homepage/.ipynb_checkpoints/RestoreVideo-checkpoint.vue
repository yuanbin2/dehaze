<script setup>
import { ref, onUnmounted, computed } from "vue";
import api from "@/js/http/api.js";

// ================= 状态变量 =================
const selectedFile = ref(null);         // 实际上传的视频文件
const originalVideoUrl = ref('');       // 前端预览原视频的本地链接
const isLoading = ref(false);           // 是否正在请求或轮询处理中
const isCompleted = ref(false);         // 任务是否彻底完成
const isDownloading = ref(false);       // 【新增】是否正在处理下载
const errorMessage = ref('');           // 错误信息提示
const restoredVideoUrl = ref('');       // 后端合成后的 MP4 链接
const statusText = ref('');             // 具体的进度文本

// 视频帧播放相关状态（用于处理中的预览）
const restoredFrames = ref([]);         // 存储所有已恢复帧的 URL 数组
const currentFrameIndex = ref(0);       // 当前播放到了第几帧
const isPlaying = ref(false);           // 播放状态
const isZoomed = ref(false);            // 控制放大模态框
let playbackTimer = null;               // 播放引擎定时器
let pollTimer = null;                   // 轮询后端进度的定时器

// ================= 计算属性 =================
const currentFrameUrl = computed(() => {
  return restoredFrames.value.length > 0 ? restoredFrames.value[currentFrameIndex.value] : '';
});

// ================= 文件选择 =================
const handleFileChange = (e) => {
  // 如果正在处理，严禁更改文件逻辑
  if (isLoading.value) return;

  const file = e.target.files[0];
  if (file) {
    selectedFile.value = file;
    // 生成本地预览地址
    originalVideoUrl.value = URL.createObjectURL(file);

    // 重置所有状态，准备新任务
    restoredFrames.value = [];
    currentFrameIndex.value = 0;
    errorMessage.value = '';
    isCompleted.value = false;
    restoredVideoUrl.value = '';
    stopAllTimers();
  }
};

// ================= 发起恢复请求 =================
async function handleRestore() {
  errorMessage.value = '';
  if (!selectedFile.value) {
    errorMessage.value = '请先选择一个视频文件';
    return;
  }

  // 开始任务，锁定 UI
  isLoading.value = true;
  isCompleted.value = false;
  restoredFrames.value = [];
  currentFrameIndex.value = 0;
  statusText.value = '正在上传并启动 AI 修复...';
  stopAllTimers();

  try {
    const formData = new FormData();
    formData.append('video', selectedFile.value);

    const res = await api.post('/api/restore_video/', formData);
    const data = res.data;

    if (data.result === 'success') {
      startPolling(data.task_id);
      playFrames(); // 启动图片序列预览
    } else {
      errorMessage.value = data.result || '视频上传失败';
      isLoading.value = false;
    }
  } catch (err) {
    errorMessage.value = '系统异常或网络错误，请稍后重试';
    isLoading.value = false;
  }
}

// ================= 轮询进度逻辑 =================
const startPolling = (taskId) => {
  pollTimer = setInterval(async () => {
    try {
      const res = await api.get(`/api/video_progress/?task_id=${taskId}`);
      const data = res.data;

      if (data.result === 'success') {
        // 更新预览帧数组
        const urlPrefix = data.frames_url_prefix;
        const processedCount = data.processed_count;
        const frames = [];
        for (let i = 1; i <= processedCount; i++) {
          const frameName = `frame_${String(i).padStart(5, '0')}.png`;
          frames.push(urlPrefix + frameName);
        }
        restoredFrames.value = frames;

        // 处理不同的后端状态
        if (data.status === 'completed') {
          // 彻底完成：停止轮询，显示视频
          clearInterval(pollTimer);
          pollTimer = null;
          stopAllTimers(); 
          
          restoredVideoUrl.value = data.video_url; 
          isLoading.value = false;
          isCompleted.value = true;
          statusText.value = '修复与合成已全部完成！';
        } else if (data.status === 'composing') {
          statusText.value = '逐帧修复完成，正在合成 MP4 视频...';
        } else if (data.status === 'error') {
          clearInterval(pollTimer);
          errorMessage.value = data.message || '处理中断发生错误';
          isLoading.value = false;
        } else {
          statusText.value = `AI 正在修复第 ${processedCount} 帧...`;
        }
      }
    } catch (err) {
      console.error("轮询报错:", err);
    }
  }, 1000);
};

// ================= 序列帧播放控制 =================
const playFrames = () => {
  isPlaying.value = true;
  playbackTimer = setInterval(() => {
    if (restoredFrames.value.length > 0) {
      if (currentFrameIndex.value < restoredFrames.value.length - 1) {
        currentFrameIndex.value++;
      } else if (isCompleted.value) {
        currentFrameIndex.value = 0;
      }
    }
  }, 50); 
};

const stopAllTimers = () => {
  isPlaying.value = false;
  if (playbackTimer) { clearInterval(playbackTimer); playbackTimer = null; }
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
};

const togglePlay = () => isPlaying.value ? stopAllTimers() : playFrames();
const toggleZoom = () => isZoomed.value = !isZoomed.value;

// ================= 【更新】视频下载逻辑 =================
async function downloadVideo() {
  if (!restoredVideoUrl.value) return;
  
  isDownloading.value = true;
  errorMessage.value = '';

  try {
    // 1. 获取视频的 Blob 数据
    const response = await fetch(restoredVideoUrl.value);
    if (!response.ok) throw new Error('网络请求失败，无法获取视频数据');
    const blob = await response.blob();
    
    const defaultFilename = `restored_video_${Date.now()}.mp4`;

    // 2. 尝试使用现代 File System Access API
    if ('showSaveFilePicker' in window) {
      const opts = {
        suggestedName: defaultFilename,
        types: [{
          description: 'Video File',
          accept: { 'video/mp4': ['.mp4'] },
        }],
      };
      
      const handle = await window.showSaveFilePicker(opts);
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      
    } else {
      // 3. 降级方案：传统 a 标签强制下载
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
    if (err.name !== 'AbortError') {
      console.error("保存视频报错:", err);
      errorMessage.value = '视频保存失败，请检查网络或跨域设置';
    }
  } finally {
    isDownloading.value = false;
  }
}

onUnmounted(() => stopAllTimers());
</script>

<template>
  <div class="flex flex-col items-center mt-10 p-4 bg-base-100 min-h-screen">
    <h2 class="text-3xl font-black mb-8 text-primary uppercase tracking-tighter italic">AI Video Restorer</h2>

    <div class="card w-full max-w-xl bg-base-200 shadow-xl p-6 mb-10 border border-base-300">
      <div class="form-control w-full">
        <label class="label">
          <span class="label-text font-bold">
            {{ isLoading ? '⚠️ 任务进行中，暂不可更换视频' : '选择待修复视频' }}
          </span>
        </label>
        <input 
          type="file" 
          accept="video/*" 
          :disabled="isLoading"
          :class="['file-input file-input-bordered file-input-primary w-full', isLoading ? 'opacity-50 cursor-not-allowed' : '']" 
          @change="handleFileChange" 
        />
      </div>

      <p v-if="errorMessage" class="text-error text-sm mt-4 text-center font-bold">{{ errorMessage }}</p>

      <button class="btn btn-primary w-full mt-6" :disabled="!selectedFile || isLoading" @click="handleRestore">
        <span v-if="isLoading" class="loading loading-spinner"></span>
        {{ isLoading ? statusText : '开始 AI 修复任务' }}
      </button>

      <div v-if="isCompleted" class="flex gap-2 mt-4 animate-in fade-in slide-in-from-top-2 duration-500">
        <button class="btn btn-success flex-1 text-white" :disabled="isDownloading" @click="downloadVideo">
          <span v-if="isDownloading" class="loading loading-spinner"></span>
          {{ isDownloading ? '正在保存视频...' : '保存修复后的视频' }}
        </button>
        <button class="btn btn-outline btn-success flex-1" @click="toggleZoom">大屏对比预览</button>
      </div>
    </div>

    <div class="flex flex-col lg:flex-row gap-8 w-full max-w-6xl justify-center">
      
      <div class="flex-1 flex flex-col border border-base-300 rounded-3xl overflow-hidden shadow-lg bg-black">
        <div class="bg-base-300 p-3 text-center font-bold text-[10px] uppercase opacity-60 tracking-widest">Original Input</div>
        <div class="h-80 flex items-center justify-center bg-zinc-950">
          <video v-if="originalVideoUrl" :src="originalVideoUrl" controls class="max-h-full max-w-full"></video>
          <span v-else class="text-zinc-700 italic text-sm">Waiting for upload...</span>
        </div>
      </div>

      <div class="flex-1 flex flex-col border border-base-300 rounded-3xl overflow-hidden shadow-lg bg-black relative group">
        <div class="bg-primary p-3 text-center font-bold text-[10px] text-primary-content uppercase tracking-widest">Restored Result</div>

        <div class="h-80 flex items-center justify-center relative bg-zinc-900">
          <video v-if="isCompleted && restoredVideoUrl" :src="restoredVideoUrl" controls class="max-h-full max-w-full"></video>

          <img v-else-if="restoredFrames.length > 0" :src="currentFrameUrl" class="max-h-full max-w-full object-contain" />

          <div v-else-if="isLoading" class="flex flex-col items-center">
            <span class="loading loading-infinity loading-lg text-primary"></span>
            <span class="text-[10px] text-zinc-500 mt-2 uppercase font-bold">{{ statusText }}</span>
          </div>

          <span v-else class="text-zinc-700 italic text-sm">No data available...</span>
          
          <button 
            v-if="isCompleted"
            @click="downloadVideo"
            :disabled="isDownloading"
            class="absolute bottom-4 right-4 btn btn-sm btn-circle btn-primary opacity-0 group-hover:opacity-100 transition-opacity shadow-xl z-10"
            title="保存视频"
          >
            <span v-if="isDownloading" class="loading loading-spinner loading-xs"></span>
            <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
          </button>
        </div>

        <div v-if="!isCompleted && restoredFrames.length > 0" class="bg-base-200 p-2 flex items-center gap-3">
          <button class="btn btn-xs btn-circle btn-ghost" @click="togglePlay">{{ isPlaying ? 'II' : '▶' }}</button>
          <input type="range" min="0" :max="restoredFrames.length - 1" :value="currentFrameIndex" @input="e => currentFrameIndex = Number(e.target.value)" class="range range-xs range-primary flex-1" />
          <span class="text-[10px] font-mono opacity-60">{{ currentFrameIndex + 1 }}/{{ restoredFrames.length }}</span>
        </div>
      </div>
    </div>

    <div v-if="isZoomed" class="fixed inset-0 z-50 bg-black/98 flex flex-col items-center justify-center p-6 backdrop-blur-md">
      <button @click="toggleZoom" class="absolute top-8 right-8 btn btn-circle btn-ghost text-white text-2xl hover:rotate-90 transition-transform">✕</button>
      <div class="w-full max-w-7xl">
        <h3 class="text-white text-center mb-8 font-black text-2xl italic tracking-tighter text-primary">CINEMATIC PREVIEW</h3>
        <div class="rounded-3xl overflow-hidden shadow-2xl bg-black border border-white/5 relative group">
           <video v-if="restoredVideoUrl" :src="restoredVideoUrl" controls autoplay class="w-full max-h-[75vh]"></video>
           
           <button 
             v-if="restoredVideoUrl"
             @click="downloadVideo"
             :disabled="isDownloading"
             class="absolute top-4 right-4 btn btn-sm btn-primary opacity-0 group-hover:opacity-100 transition-opacity shadow-xl"
           >
             <span v-if="isDownloading" class="loading loading-spinner loading-xs"></span>
             {{ isDownloading ? '保存中...' : '下载高清源文件' }}
           </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.range-xs { height: 0.75rem; }
.file-input:disabled { background-color: hsl(var(--b3)); }
</style>