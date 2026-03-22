import os
import torch
import numpy as np
from PIL import Image

def process_video_task(raw_frames_dir, output_frames_dir, predictor):
    """
    深度混合版：直接在循环内执行 PyTorch 张量转换和推理，确保与单张图像逻辑 100% 绝对一致。
    
    :param raw_frames_dir: FFmpeg 拆解出的无损原始帧目录
    :param output_frames_dir: AI 恢复后的帧存放目录
    :param predictor: UNetPredictor 实例 (提供模型、设备和转换器)
    """
    if not os.path.isdir(raw_frames_dir):
        return {"status": "error", "message": f"找不到原始帧目录: {raw_frames_dir}"}

    os.makedirs(output_frames_dir, exist_ok=True)

    # 获取所有 PNG 帧并严格排序
    raw_images = [f for f in os.listdir(raw_frames_dir) if f.lower().endswith('.png')]
    raw_images.sort()

    if not raw_images:
        return {"status": "error", "message": "没有找到需要处理的帧。"}

    print(f"🎬 开始视频帧处理，共 {len(raw_images)} 帧 (已将单图 Tensor 逻辑内嵌)...")

    saved_frames_paths = []
    
    for img_name in raw_images:
        img_path = os.path.join(raw_frames_dir, img_name)
        save_path = os.path.join(output_frames_dir, img_name)

        try:
            # ==========================================================
            # 以下逻辑完全 Copy 自 image_recovery.py 的 process_and_save
            # ==========================================================
            
            # 1. 加载图像并转换为 RGB
            with Image.open(img_path) as img_data:
                image = img_data.convert('RGB')
                
            # 2. 预处理 (ToTensor)
            try:
                input_tensor = predictor.transform(image).unsqueeze(0).to(predictor.device)
            except Exception as e:
                print(f"❌ 帧 {img_name} 预处理张量失败: {e}")
                continue

            # 3. 模型推理
            with torch.no_grad():
                output_tensor = predictor.model(input_tensor)
                output_tensor = torch.clamp(output_tensor, 0.0, 1.0)

            # 4. 后处理 (Tensor -> Numpy -> Image)
            pred_array = output_tensor[0].cpu().numpy().transpose(1, 2, 0)
            pred_img_uint8 = (np.clip(pred_array, 0, 1) * 255).astype(np.uint8)
            pred_pil = Image.fromarray(pred_img_uint8)

            # 5. 保存
            try:
                pred_pil.save(save_path)
                saved_frames_paths.append(save_path)
            except Exception as e:
                print(f"❌ 帧 {img_name} 保存到磁盘失败: {e}")
                continue

            # ==========================================================
            # 逻辑结束
            # ==========================================================

        except Exception as e:
            print(f"❌ 帧 {img_name} 处理崩溃: {str(e)}")
            continue

    if len(saved_frames_paths) == 0:
        return {"status": "error", "message": "所有帧均处理失败。"}

    return {
        "status": "success",
        "total_frames_processed": len(saved_frames_paths),
        "output_directory": output_frames_dir,
        "fps": None  
    }