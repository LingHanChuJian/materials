# 提取图像中的
import cv2
import numpy as np
import matplotlib.pyplot as plt

def extract_graphics(image_path: str) -> tuple[list[np.ndarray], np.ndarray]:
    image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"Failed to load image from {image_path}")

    # 轮廓提取处理
    if len(image.shape) == 3 and image.shape[2] == 4:
        image_gray = image[:, :, 3]
    elif len(image.shape) == 3:
        # 灰度图
        image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        image_gray = image

    plt.figure(figsize=(15, 10))

    # 二值化 - 如果图像是黑色背景白色图案，需要反转
    # 使用 THRESH_BINARY_INV 让白色图案变成前景（255），黑色背景变成背景（0）
    # 或者如果阈值较低，可以这样处理：
    _, binary = cv2.threshold(image_gray, 1, 255, cv2.THRESH_BINARY_INV)

    unique_values = np.unique(binary)
    print(f"二值化后的唯一值: {unique_values}, 图像形状: {binary.shape}")

    # 使用 RETR_EXTERNAL 找外部轮廓（独立元素）
    # 如果元素之间有连接，可以改用 RETR_TREE 或 RETR_LIST 找所有轮廓
    contours, _ = cv2.findContours(
        binary,
        cv2.RETR_EXTERNAL,  # 只找外部轮廓，每个独立区域一个轮廓
        cv2.CHAIN_APPROX_NONE
    )

    print(f"找到 {len(contours)} 个独立元素")

    return max(contours, key=cv2.contourArea), image
