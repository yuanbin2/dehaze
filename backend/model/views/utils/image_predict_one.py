import os
import torch
import numpy as np
from torchvision import transforms
from PIL import Image
# 假设你的目录结构没变，保留这个引用
from model.views.model.UNet import UNet


class UNetPredictor:
    def __init__(self, model_path, device=None):
        """
        初始化预测器：加载模型和权重，只需执行一次。
        """
        # 1. 设置设备
        if device:
            self.device = device
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        print(f"🚀 Initializing UNetPredictor on {self.device}...")

        # 2. 初始化模型架构
        # 注意：这里假设你的模型输入输出都是3通道 (RGB)
        self.model = UNet(in_channels=3, out_channels=3).to(self.device)

        # 3. 加载权重
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"❌ Model path not found: {model_path}")

        # map_location 确保在 CPU 机器上也能加载 GPU 训练的权重
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()  # 切换到评估模式
        print(f"✅ Model loaded successfully from: {model_path}")

        # 4. 定义预处理变换
        self.transform = transforms.Compose([
            transforms.ToTensor(),
        ])

    def predict_single_image(self, image_path, save_dir):
        """
        推理单张图片。
        :param image_path: 输入图片的绝对路径或相对路径
        :param save_dir: 结果保存的文件夹路径
        :return: 保存后的图片路径 (str)
        """
        if not os.path.exists(image_path):
            print(f"❌ Error: Input image not found: {image_path}")
            return None

        # 1. 准备保存路径
        os.makedirs(save_dir, exist_ok=True)
        file_name = os.path.basename(image_path)  # 获取文件名 (e.g., "test.jpg")
        base_name = os.path.splitext(file_name)[0]
        save_path = os.path.join(save_dir, f'{base_name}_pred.png')

        # 2. 图像预处理
        try:
            image = Image.open(image_path).convert('RGB')
            input_tensor = self.transform(image)  # [C, H, W]
            input_tensor = input_tensor.unsqueeze(0)  # 增加 Batch 维度 -> [1, C, H, W]
            input_tensor = input_tensor.to(self.device)
        except Exception as e:
            print(f"❌ Error loading image: {e}")
            return None

        # 3. 推理
        with torch.no_grad():
            output_tensor = self.model(input_tensor)
            output_tensor = torch.clamp(output_tensor, 0.0, 1.0)  # 限制范围

        # 4. 后处理 (Tensor -> Numpy -> Image)
        # 去掉 Batch 维度 [1, C, H, W] -> [C, H, W] -> [H, W, C]
        pred_array = output_tensor[0].cpu().numpy().transpose(1, 2, 0)

        # 转为 uint8 并保存
        pred_img_uint8 = (np.clip(pred_array, 0, 1) * 255).astype(np.uint8)
        pred_pil = Image.fromarray(pred_img_uint8)

        pred_pil.save(save_path)
        print(f"💾 Prediction saved to: {save_path}")

        return save_path


# ===================== 本地测试代码 / 使用示例 =====================
if __name__ == "__main__":
    # 1. 定义模型路径
    MODEL_PATH = '../model/weights_UNet/best_model_291_batch16.pth'

    # 2. 实例化预测器 (在程序启动时做一次即可)
    predictor = UNetPredictor(model_path=MODEL_PATH)

    # 3. 测试单张图片调用
    test_img_path = '../../../media/model/test/sample.png'  # 替换为你的一张真实图片路径
    save_directory = '../../../media/model/predict_result/'

    # 检查一下测试文件是否存在，避免报错
    if os.path.exists(test_img_path):
        result_path = predictor.predict_single_image(test_img_path, save_directory)
        print(f"Result returned: {result_path}")
    else:
        print("⚠️ Test image not found, please check path for testing.")