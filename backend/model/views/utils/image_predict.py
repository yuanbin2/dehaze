import os
import torch
import numpy as np
import matplotlib.pyplot as plt
from torchvision import transforms
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm
from PIL import Image
from model.views.model.UNet import UNet



# ===================== InferenceDataset (只加载输入图片) =====================
class InferenceDataset(Dataset):
    def __init__(self, image_dir, transform=None):
        if not os.path.exists(image_dir):
            raise FileNotFoundError(f"Image directory not found: {image_dir}")
        self.image_dir = image_dir
        self.transform = transform
        # 获取所有图片文件名
        self.image_names = sorted([f for f in os.listdir(image_dir) if os.path.isfile(os.path.join(image_dir, f))])

    def __len__(self):
        return len(self.image_names)

    def __getitem__(self, idx):
        img_name = self.image_names[idx]
        image_path = os.path.join(self.image_dir, img_name)

        # 加载图片
        image = Image.open(image_path).convert('RGB')

        if self.transform:
            image = self.transform(image)
        else:
            image = transforms.ToTensor()(image)

        # 返回图片张量和文件名（用于保存预测结果时命名）
        return image, img_name


# ===================== 实时显示函数 (Input vs Prediction) =====================
def display_prediction_real_time(inputs, outputs, base_name, fig_size=(12, 6), pause_duration=1.0):
    inp_img = inputs[0].cpu().numpy().transpose(1, 2, 0)
    out_img = outputs[0].cpu().numpy().transpose(1, 2, 0)

    fig, axes = plt.subplots(1, 2, figsize=fig_size)

    # 显示输入
    axes[0].imshow(np.clip(inp_img, 0, 1))
    axes[0].set_title('Input RGB')
    axes[0].axis('off')

    # 显示预测
    axes[1].imshow(np.clip(out_img, 0, 1))
    axes[1].set_title('Prediction RGB')
    axes[1].axis('off')

    plt.suptitle(f'{base_name}')
    plt.tight_layout()
    plt.show(block=False)
    plt.pause(pause_duration)
    plt.close(fig)


# ===================== 推理并保存函数 =====================
def predict_and_save(model, dataloader, device, vis_save_dir, fig_size=(12, 6), pause_duration=0.5):
    model.eval()

    # 确保保存目录存在
    os.makedirs(vis_save_dir, exist_ok=True)

    with torch.no_grad():
        for inputs, img_names in tqdm(dataloader, desc="Predicting"):
            inputs = inputs.to(device)

            # 模型推理
            outputs = model(inputs)
            outputs = torch.clamp(outputs, 0.0, 1.0)  # 限制范围在 0-1

            # 遍历 batch (通常测试时 batch_size=1)
            for i in range(len(inputs)):
                # 获取当前样本的预测结果和文件名
                pred = outputs[i].cpu().numpy().transpose(1, 2, 0)
                file_name = img_names[i]
                base_name = os.path.splitext(file_name)[0]

                # 保存预测图像
                pred_img_uint8 = (np.clip(pred, 0, 1) * 255).astype(np.uint8)
                pred_pil = Image.fromarray(pred_img_uint8)

                save_path = os.path.join(vis_save_dir, f'{base_name}_pred.png')
                pred_pil.save(save_path)

                print(f"Saved: {save_path}")

                # 实时显示 (如果需要关闭显示，注释掉下面这一行即可)
                # display_prediction_real_time(inputs[i:i+1], outputs[i:i+1], base_name, fig_size, pause_duration)

    print(f"\n✅ All predictions saved to: {vis_save_dir}")


# ===================== 主函数 =====================
if __name__ == "__main__":
    # 1. 参数设置
    batch_size = 1  # 推理通常设为1
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # 2. 路径设置
    # 请确保这里的路径是正确的
    model_path = '../model/weights_UNet/best_model_291_batch16.pth'

    # 输入图片的文件夹
    test_image_dir = '../../../media/model/test/'

    # 结果保存文件夹
    vis_save_dir = '../../../media/model/predict_result/'

    # 3. 数据预处理
    transform = transforms.Compose([
        transforms.ToTensor(),
    ])

    # 4. 加载数据集 (不再需要 Label 目录)
    inference_dataset = InferenceDataset(test_image_dir, transform=transform)
    inference_loader = DataLoader(inference_dataset, batch_size=batch_size, shuffle=False)

    # 5. 加载模型
    model = UNet(in_channels=3, out_channels=3).to(device)
    if os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path, map_location=device))
        print(f"✅ Model loaded from: {model_path}")
    else:
        print(f"❌ Model path not found: {model_path}")
        exit()

    # 6. 执行预测与保存
    predict_and_save(
        model,
        inference_loader,
        device,
        vis_save_dir,
        fig_size=(12, 6),
        pause_duration=0.1  # 设置为 0 可快速跑完不暂停
    )