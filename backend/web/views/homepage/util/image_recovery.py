import os
import torch
import numpy as np
from torchvision import transforms
from PIL import Image

# 引入你的模型架构
from web.views.homepage.util.UNet import UNet

# 1. 动态获取当前文件 (image_recovery.py) 所在的绝对文件夹路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. 拼接出模型文件的绝对路径
DEFAULT_MODEL_PATH = os.path.join(CURRENT_DIR, 'best_model_291_batch16.pth')

class UNetPredictor:
    # 👇 将 model_path 的默认值设为刚才定义的 DEFAULT_MODEL_PATH
    def __init__(self, model_path=DEFAULT_MODEL_PATH, device=None):
        """
        初始化预测器：加载模型和权重。
        ⚠️ 注意：在 Web 后端中，这个类应该作为单例在应用启动时初始化一次，不要在 View 里面反复实例化。
        """
        if device:
            self.device = device
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            
        print(f"🚀 Initializing UNetPredictor on {self.device}...")
        
        self.model = UNet(in_channels=3, out_channels=3).to(self.device)
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"❌ Model path not found: {model_path}")
            
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()
        print(f"✅ Model loaded successfully from: {model_path}")
        
        # =======================================================
        # 👇 核心修改点：加入 transforms.Resize((512, 512))
        # =======================================================
        self.transform = transforms.Compose([
            # transforms.Resize((512, 512)),  # 强制将图像缩放为 512x512
            transforms.ToTensor(),
        ])

    def process_and_save(self, image_data, save_path):
        """
        接收图像数据并直接保存到 View 指定的位置。
        
        :param image_data: 可以是文件绝对路径 (str)，也可以是前端传来的文件流对象 (File-like object)
        :param save_path: 由 View 指定的最终保存完整路径 (例如: '/var/www/media/results/user_123_restored.png')
        :return: 保存后的路径 (str) 或 None (失败时)
        """
        # 1. 加载图像 (直接支持 Web 框架的文件流)
        try:
            if isinstance(image_data, Image.Image):
                image = image_data.convert('RGB')
            else:
                # PIL.Image.open 可以直接读取 Django 的 UploadedFile 或 Flask 的 FileStorage
                image = Image.open(image_data).convert('RGB')
        except Exception as e:
            print(f"❌ Error loading image: {e}")
            return None

        # 2. 预处理 (这里会自动执行上面定义的 Resize 和 ToTensor)
        try:
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)
        except Exception as e:
            print(f"❌ Error during preprocessing: {e}")
            return None

        # 3. 模型推理
        with torch.no_grad():
            output_tensor = self.model(input_tensor)
            output_tensor = torch.clamp(output_tensor, 0.0, 1.0)

        # 4. 后处理 (Tensor -> Numpy -> Image)
        pred_array = output_tensor[0].cpu().numpy().transpose(1, 2, 0)
        pred_img_uint8 = (np.clip(pred_array, 0, 1) * 255).astype(np.uint8)
        pred_pil = Image.fromarray(pred_img_uint8)

        # 5. 确保保存目录存在并保存
        try:
            save_dir = os.path.dirname(save_path)
            if save_dir:
                os.makedirs(save_dir, exist_ok=True)
            
            pred_pil.save(save_path)
            print(f"💾 Prediction successfully saved to: {save_path}")
            return save_path
        except Exception as e:
            print(f"❌ Error saving image to {save_path}: {e}")
            return None