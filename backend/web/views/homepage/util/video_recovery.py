import cv2
import os
from PIL import Image

def process_video_task(input_video_path, output_frames_dir, predictor, skip_rate=2):
    """
    后端专用的视频处理任务：读取指定的视频文件，按比例抽帧恢复。
    
    :param input_video_path: 视频路径
    :param output_frames_dir: 输出目录
    :param predictor: 模型实例
    :param skip_rate: 抽帧率。默认2代表每2帧处理1帧(即保留1/2的帧数，30fps变15fps)。设为3即保留1/3。
    """
    if not os.path.exists(input_video_path):
        return {"status": "error", "message": "Input video not found"}

    os.makedirs(output_frames_dir, exist_ok=True)

    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        return {"status": "error", "message": "Failed to open video file."}

    original_fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"🎬 原视频 FPS: {original_fps}，当前设置抽帧率: 1/{skip_rate}")

    read_frame_count = 0  # 记录读了多少帧
    saved_frame_count = 0 # 记录实际保存了多少帧
    saved_frames_paths = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break  # 视频流结束

        read_frame_count += 1
        
        # ==========================================
        # ★ 核心优化：跳帧逻辑
        # 如果当前帧号不能被 skip_rate 整除，就直接跳过不处理
        # ==========================================
        if read_frame_count % skip_rate != 0:
            continue
            
        saved_frame_count += 1
        
        # BGR 转 RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)

        # ⚠️ 注意：这里的文件名一定要用 saved_frame_count (1,2,3...)，
        # 否则序号断层(1,3,5...)会导致前端按顺序轮询时找不到图片报 404
        filename = f"frame_{saved_frame_count:05d}.png"
        save_path = os.path.join(output_frames_dir, filename)

        # 调用预测器
        result_path = predictor.process_and_save(pil_img, save_path)
        if result_path:
            saved_frames_paths.append(result_path)

    cap.release()
    
    if len(saved_frames_paths) == 0:
        return {"status": "error", "message": "No frames were successfully processed."}

    return {
        "status": "success",
        "total_frames_processed": len(saved_frames_paths),
        "output_directory": output_frames_dir,
        "frames_list": saved_frames_paths
    }