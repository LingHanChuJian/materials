class Settings:
    # 排料板宽度（mm）
    width: float = 3000.0

    # 排料板长度（mm，无限延伸时使用足够大的值）
    length: float = 10000.0

    # 图形之间的最小间距（mm）
    spacing: float = 5.0

    # 允许的旋转角度列表（可以根据需要增加更多角度，如 [0, 90, 180, 270]）
    angles: list[float] = [0.0, 90.0, 180.0, 270.0]

    # 图像DPI（像素/毫米），用于将像素转换为毫米
    dpi: float = 96.0

    # 多边形简化容差（mm）
    tolerance: float = 0.5

    # 多边形简化最大点数
    max_points: int = 300

    # NFP 精度放缩
    nfp_scale: int = 1000

settings = Settings()