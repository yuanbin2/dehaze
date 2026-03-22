import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import cat
from torch.cuda.amp import autocast, GradScaler  # 添加AMP支持

# ------------------------------ 基础卷积块 ------------------------------
class DoubleConv(nn.Module):
    def __init__(self, in_ch, out_ch, dropout=0):
        super(DoubleConv, self).__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.LeakyReLU(inplace=True),
            nn.Dropout2d(p=dropout)
        )
    def forward(self, x):
        return self.conv(x)

# ------------------------------ 下采样模块 ------------------------------
class Down(nn.Module):
    def __init__(self, in_ch, out_ch, dropout=0):
        super(Down, self).__init__()
        self.conv = DoubleConv(in_ch, out_ch, dropout)
        self.pool = nn.MaxPool2d(2)
    def forward(self, x):
        x1 = self.conv(x)
        x2 = self.pool(x1)
        return x2, x1

# ------------------------------ 上采样模块 ------------------------------
class Up(nn.Module):
    def __init__(self, in_ch, out_ch, dropout=0):
        super(Up, self).__init__()
        self.up = nn.ConvTranspose2d(
            in_ch, out_ch, kernel_size=3, stride=2, padding=1, output_padding=1)
        self.conv = DoubleConv(out_ch * 2, out_ch, dropout)
    def forward(self, x, skip):
        x = self.up(x)
        # 保证尺寸匹配
        if x.size() != skip.size():
            diffY = skip.size()[2] - x.size()[2]
            diffX = skip.size()[3] - x.size()[3]
            x = F.pad(x, [diffX // 2, diffX - diffX // 2,
                          diffY // 2, diffY - diffY // 2])
        x = cat((skip, x), dim=1)
        return self.conv(x)

# ------------------------------ 输出层 ------------------------------
class OutConv(nn.Module):
    def __init__(self, in_ch, out_ch):
        super(OutConv, self).__init__()
        self.conv = nn.Conv2d(in_ch, out_ch, kernel_size=1)
    def forward(self, x):
        return self.conv(x)

# ------------------------------ 主网络：普通U-Net ------------------------------
class UNet(nn.Module):
    def __init__(self, in_channels=3, out_channels=3, layer=32, dropout=0.1):
        super(UNet, self).__init__()
        self.down1 = Down(in_channels, layer, dropout)
        self.down2 = Down(layer, layer * 2, dropout)
        self.down3 = Down(layer * 2, layer * 4, dropout)
        self.down4 = Down(layer * 4, layer * 8, dropout)

        self.bottom = DoubleConv(layer * 8, layer * 16, dropout)

        self.up1 = Up(layer * 16, layer * 8, dropout)
        self.up2 = Up(layer * 8, layer * 4, dropout)
        self.up3 = Up(layer * 4, layer * 2, dropout)
        self.up4 = Up(layer * 2, layer, dropout)

        self.outc = OutConv(layer, out_channels)

    def forward(self, x):
        x1_down, x1 = self.down1(x)
        x2_down, x2 = self.down2(x1_down)
        x3_down, x3 = self.down3(x2_down)
        x4_down, x4 = self.down4(x3_down)

        x5 = self.bottom(x4_down)

        x6 = self.up1(x5, x4)
        x7 = self.up2(x6, x3)
        x8 = self.up3(x7, x2)
        x9 = self.up4(x8, x1)

        out = self.outc(x9)
        return out