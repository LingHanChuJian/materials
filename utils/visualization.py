import matplotlib.pyplot as plt
from shapely.affinity import rotate, translate
from pathlib import Path
import matplotlib.patches as patches

def visualize_poly(poly, title="Processed Polygon"):
    plt.close('all')

    fig, ax = plt.subplots(figsize=(8, 8))
    
    # 1. 提取外环坐标
    # poly.exterior.xy 返回 (x_array, y_array)
    x, y = poly.exterior.xy
    
    # 2. 绘制填充区域
    ax.fill(x, y, alpha=0.3, fc='blue', ec='black', label='Buffered Poly')
    
    # 3. 绘制坐标点（可选，用于检查简化效果）
    ax.scatter(x, y, s=10, color='red', zorder=3)
    
    # 设置等比例坐标轴（非常重要，否则图形会变形）
    ax.set_aspect('equal')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.set_title(f"{title} (Points: {len(x)})")
    ax.set_xlabel("Width (mm)")
    ax.set_ylabel("Height (mm)")
    
    plt.show()

def debug_rotation_0_180(poly):
    """
    传入一个 Shapely Polygon 对象
    自动展示其 0 度和 180 度（对齐原点后）的效果
    """
    plt.close('all')

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
    
    # --- 处理 0 度 ---
    # 对齐到 (0,0)
    mx0, my0, _, _ = poly.bounds
    p0 = translate(poly, xoff=-mx0, yoff=-my0)
    
    x0, y0 = p0.exterior.xy
    ax1.fill(x0, y0, alpha=0.5, fc='cyan', ec='k', label='Original')
    ax1.plot(0, 0, 'ro') # 标记原点
    ax1.set_title(f"0 Degree\nBounds: {p0.bounds}")
    ax1.set_aspect('equal')
    ax1.grid(True)

    # --- 处理 180 度 ---
    # 绕质心旋转
    p180_raw = rotate(poly, 180, origin='centroid')
    # 旋转后必须重新对齐到 (0,0)
    mx180, my180, _, _ = p180_raw.bounds
    p180 = translate(p180_raw, xoff=-mx180, yoff=-my180)
    
    x180, y180 = p180.exterior.xy
    ax2.fill(x180, y180, alpha=0.5, fc='orange', ec='k', label='Rotated')
    ax2.plot(0, 0, 'ro') # 标记原点
    ax2.set_title(f"180 Degree\nBounds: {p180.bounds}")
    ax2.set_aspect('equal')
    ax2.grid(True)
    
    plt.tight_layout()
    plt.show()

def visualize_packing_result(packer, generation, output_dir="test", bin_width=None):
    """
    可视化排料结果并保存到文件
    
    Args:
        packer: Packer 对象，包含已放置的零件
        generation: 当前迭代次数
        output_dir: 输出目录
        bin_width: 容器宽度（用于绘制边界）
    """
    plt.close('all')
    
    # 确保输出目录存在
    Path(output_dir).mkdir(exist_ok=True)
    
    # 创建图形
    fig, ax = plt.subplots(figsize=(16, 10))
    
    # 设置颜色列表
    colors = plt.cm.tab20(range(20))
    
    # 绘制每个已放置的零件（使用原始未膨胀版本）
    for i, item in enumerate(packer.placed_items):
        # 使用原始版本绘图（如果有的话）
        poly_display = item.get('poly_display', item['poly'])
        piece_id = item['id']
        angle = item['angle']
        
        # 提取多边形坐标
        x, y = poly_display.exterior.xy
        
        # 绘制填充区域
        color = colors[piece_id % 20]
        ax.fill(x, y, alpha=0.6, fc=color, ec='black', linewidth=1.5)
        
        # 在零件中心标注 ID 和角度
        centroid = poly_display.centroid
        ax.text(centroid.x, centroid.y, f"ID:{piece_id}\n{angle}°", 
                ha='center', va='center', fontsize=8, 
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # 绘制容器边界（固定宽度、无限长度模式）
    if bin_width and packer.placed_items:
        # 使用显示版本计算高度
        total_height = max(item.get('poly_display', item['poly']).bounds[3] for item in packer.placed_items)
        # 绘制左右边界线（表示固定宽度）
        ax.axvline(x=0, color='red', linewidth=2, linestyle='--', label='Container Left')
        ax.axvline(x=bin_width, color='red', linewidth=2, linestyle='--', label='Container Right')
        # 绘制容器矩形框（用于参考）
        rect = patches.Rectangle((0, 0), bin_width, total_height, 
                                  linewidth=2, edgecolor='red', 
                                  facecolor='none', linestyle='--', alpha=0.5)
        ax.add_patch(rect)
    
    # 设置坐标轴
    ax.set_aspect('equal')
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.set_xlabel("Width (mm)", fontsize=12)
    ax.set_ylabel("Height (mm)", fontsize=12)
    
    # 设置标题（固定宽度、无限长度模式）
    utilization = 0.0
    if bin_width and packer.placed_items:
        total_height = packer.total_length  # 使用 Y 方向的总长度
        # 计算材料利用率时使用原始多边形的面积
        total_area = sum(item.get('poly_display', item['poly']).area for item in packer.placed_items)
        container_area = bin_width * total_height
        utilization = (total_area / container_area * 100) if container_area > 0 else 0
    
    title = f"Generation {generation} | Height: {packer.total_length:.2f}mm (Width: {bin_width:.0f}mm)"
    if utilization > 0:
        title += f" | Utilization: {utilization:.2f}%"
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    # 设置坐标轴范围（使用显示版本计算）
    if packer.placed_items:
        all_x = []
        all_y = []
        for item in packer.placed_items:
            poly_display = item.get('poly_display', item['poly'])
            all_x.extend([coord[0] for coord in poly_display.exterior.coords])
            all_y.extend([coord[1] for coord in poly_display.exterior.coords])
        margin = 50
        ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
        ax.set_ylim(min(all_y) - margin, max(all_y) + margin)
    
    # 保存图像
    output_path = Path(output_dir) / f"generation_{generation:04d}.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return str(output_path)
