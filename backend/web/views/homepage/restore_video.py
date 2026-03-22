import os
import subprocess  # 用于调用 ffmpeg
import uuid
import threading
import traceback
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser 

from web.views.homepage.util.image_recovery import UNetPredictor
from web.views.homepage.util.video_recovery import process_video_task

try:
    predictor = UNetPredictor()
except Exception:
    predictor = None

# 临时用字典存储每个任务的进度（真实生产环境建议存在 Redis 或数据库里）
TASK_STATUS = {}

def background_video_task(input_video_path, output_frames_dir, predictor_instance, task_id):
    """后台运行：1. 逐帧修复 -> 2. 合成视频"""
    try:
        TASK_STATUS[task_id]['status'] = 'processing'
        
        # 1. 运行原有的逐帧修复函数
        # 假设该函数返回结果包含 fps 属性，如果没有，我们默认用 30
        result = process_video_task(input_video_path, output_frames_dir, predictor_instance)
        fps = result.get('fps', 30) 
        
        TASK_STATUS[task_id]['status'] = 'composing' # 状态更新为：正在合成视频
        
        # 2. 调用 FFmpeg 合成视频
        # 构造输出视频路径：media/restored_videos/task_id.mp4
        video_output_dir = os.path.join(settings.MEDIA_ROOT, 'restored_videos')
        os.makedirs(video_output_dir, exist_ok=True)
        output_mp4_path = os.path.join(video_output_dir, f"{task_id}.mp4")
        
        # FFmpeg 命令说明：
        # -r: 帧率
        # -i: 输入图片格式 (假设你的图片名是 frame_00001.png)
        # -c:v libx264: 使用 H264 编码
        # -pix_fmt yuv420p: 提高播放器兼容性
        ffmpeg_cmd = [
            'ffmpeg', '-y', 
            '-r', str(fps), 
            '-i', os.path.join(output_frames_dir, 'frame_%05d.png'),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            output_mp4_path
        ]
        
        # 执行合成
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        
        # 3. 任务彻底完成
        TASK_STATUS[task_id]['status'] = 'completed'
        TASK_STATUS[task_id]['video_url'] = f"{settings.MEDIA_URL}restored_videos/{task_id}.mp4"
        TASK_STATUS[task_id]['total'] = result.get('total_frames_processed', 0)

    except Exception as e:
        print(f"Error in task {task_id}: {traceback.format_exc()}")
        TASK_STATUS[task_id]['status'] = 'error'
        TASK_STATUS[task_id]['message'] = str(e)
    finally:
        # 清理原始上传的临时视频
        if os.path.exists(input_video_path):
            os.remove(input_video_path)

class RestoreVideoView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        if predictor is None:
            return Response({'result': '模型未加载'})

        video_file = request.FILES.get('video')
        if not video_file:
            return Response({'result': '请上传视频文件'})

        task_id = uuid.uuid4().hex
        
        # 存视频
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_videos')
        os.makedirs(temp_dir, exist_ok=True)
        fs = FileSystemStorage(location=temp_dir)
        temp_filename = fs.save(f"{task_id}_{video_file.name}", video_file)
        input_video_path = os.path.join(temp_dir, temp_filename)

        output_frames_dir = os.path.join(settings.MEDIA_ROOT, 'restored_frames', task_id)
        
        # 初始化任务状态
        TASK_STATUS[task_id] = {
            'status': 'starting',
            'output_dir': output_frames_dir,
            'url_prefix': f"{settings.MEDIA_URL}restored_frames/{task_id}/"
        }

        # ★ 核心操作：开一个新线程去跑模型，主线程立刻返回 JSON 给前端 ★
        thread = threading.Thread(
            target=background_video_task,
            args=(input_video_path, output_frames_dir, predictor, task_id)
        )
        thread.start()

        # 瞬间返回 task_id
        return Response({
            'result': 'success',
            'task_id': task_id
        })


# VideoProgressView 的修改：让它返回 video_url
class VideoProgressView(APIView):
    def get(self, request):
        task_id = request.GET.get('task_id')
        if not task_id or task_id not in TASK_STATUS:
            return Response({'result': '找不到该任务'})
            
        task_info = TASK_STATUS[task_id]
        
        processed_count = 0
        if os.path.exists(task_info['output_dir']):
            processed_count = len([f for f in os.listdir(task_info['output_dir']) if f.endswith('.png')])

        return Response({
            'result': 'success',
            'status': task_info['status'], 
            'processed_count': processed_count,
            'frames_url_prefix': task_info['url_prefix'],
            'video_url': task_info.get('video_url', ''), # 完成后会包含视频链接
            'message': task_info.get('message', '')
        })