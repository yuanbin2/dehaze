import os
import subprocess
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
except Exception as e:
    print(f"❌ 模型加载失败: {e}")
    predictor = None

TASK_STATUS = {}

def background_video_task(input_video_path, output_frames_dir, predictor_instance, task_id, client_fps):
    try:
        TASK_STATUS[task_id]['status'] = 'processing'
        
        # --- 步骤 1: 建立文件夹 ---
        raw_frames_dir = os.path.join(settings.MEDIA_ROOT, 'raw_frames', task_id)
        os.makedirs(raw_frames_dir, exist_ok=True)
        os.makedirs(output_frames_dir, exist_ok=True) 

        # --- 步骤 2: 纯净无损拆帧 ---
        extract_cmd = [
            'ffmpeg', '-y', 
            '-i', input_video_path,
            '-pix_fmt', 'rgb24',   # ★ 核心新增：强制转换为纯正 RGB24 给 AI 处理
            '-vsync', '0', 
            os.path.join(raw_frames_dir, 'frame_%05d.png')
        ]
        
        extract_res = subprocess.run(extract_cmd, capture_output=True, text=True)
        if extract_res.returncode != 0:
            raise Exception(f"FFmpeg 拆帧失败: {extract_res.stderr}")

        # --- 步骤 3: 调用模型处理 ---
        result = process_video_task(raw_frames_dir, output_frames_dir, predictor_instance)
        
        if result.get('status') == 'error':
            raise Exception(result.get('message', '未知错误'))

        generated_files = [f for f in os.listdir(output_frames_dir) if f.endswith('.png')]
        if not generated_files:
            raise Exception(f"模型处理完成，但输出目录 {output_frames_dir} 为空！")

        final_fps = client_fps or result.get('fps') or 10
        TASK_STATUS[task_id]['status'] = 'composing'
        
        # --- 步骤 4: 浏览器兼容的高画质合成 ---
        video_output_dir = os.path.join(settings.MEDIA_ROOT, 'restored_videos')
        os.makedirs(video_output_dir, exist_ok=True)
        output_mp4_path = os.path.join(video_output_dir, f"{task_id}.mp4")
        
        # ★ 核心修改：使用 yuv444p + bt709 防止变粉红且保留最高画质
        ffmpeg_cmd = [
            'ffmpeg', '-y', 
            '-framerate', str(final_fps), 
            '-start_number', '1',
            '-i', os.path.join(output_frames_dir, 'frame_%05d.png'),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv444p',          # 拒绝色度抽样
            '-colorspace', 'bt709',         # 固定色彩空间
            '-color_primaries', 'bt709',
            '-color_trc', 'bt709',
            '-crf', '18', 
            output_mp4_path
        ]
        
        res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"FFmpeg Error Output: {res.stderr}")
            raise Exception(f"FFmpeg 合成失败，错误码: {res.returncode}")
        
        TASK_STATUS[task_id]['status'] = 'completed'
        TASK_STATUS[task_id]['video_url'] = f"{settings.MEDIA_URL}restored_videos/{task_id}.mp4"

    except Exception as e:
        traceback.print_exc()
        TASK_STATUS[task_id]['status'] = 'error'
        TASK_STATUS[task_id]['message'] = str(e)
    finally:
        # 清理用户上传的源视频以节省服务器空间
        if os.path.exists(input_video_path):
            os.remove(input_video_path)

class RestoreVideoView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        if predictor is None:
            return Response({'result': '模型未加载'})

        video_file = request.FILES.get('video')
        # 获取前端传来的帧率设置
        client_fps = request.data.get('fps') 
        try:
            client_fps = int(client_fps) if client_fps else None
        except ValueError:
            client_fps = None

        if not video_file:
            return Response({'result': '请上传视频文件'})

        task_id = uuid.uuid4().hex
        
        # 存临时视频
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_videos')
        os.makedirs(temp_dir, exist_ok=True)
        fs = FileSystemStorage(location=temp_dir)
        temp_filename = fs.save(f"{task_id}_{video_file.name}", video_file)
        input_video_path = os.path.join(temp_dir, temp_filename)

        output_frames_dir = os.path.join(settings.MEDIA_ROOT, 'restored_frames', task_id)
        
        TASK_STATUS[task_id] = {
            'status': 'starting',
            'output_dir': output_frames_dir,
            'url_prefix': f"{settings.MEDIA_URL}restored_frames/{task_id}/"
        }

        thread = threading.Thread(
            target=background_video_task,
            args=(input_video_path, output_frames_dir, predictor, task_id, client_fps)
        )
        thread.start()

        return Response({
            'result': 'success',
            'task_id': task_id
        })

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
            'video_url': task_info.get('video_url', ''), 
            'message': task_info.get('message', '')
        })