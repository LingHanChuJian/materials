import os
from pathlib import Path
from utils.extract_graphics import extract_graphics
from utils.graphics_processing import GraphicsProcessing
from utils.visualization import visualize_packing_result
from core.ga import GA
from core.packer import Packer
from settings.settings import settings

def main():
    """
    完整的排料流程：
    1. 加载图像并提取轮廓
    2. 预处理零件（旋转缓存）
    3. 运行遗传算法优化排料
    4. 输出每次迭代结果到 test 文件夹
    """
    print("=" * 60)
    print("开始排料流程")
    print("=" * 60)
    
    # 1. 加载所有零件图像
    print("\n[1/4] 加载零件图像...")
    assets_path = [Path("assets") / f for f in os.listdir("assets") if f.endswith(".png")]

    pieces = []
    for i, image_path in enumerate(assets_path):
        print(f"  处理 {image_path.name}... ", end="")
        contour, image = extract_graphics(image_path)
        graphics_processing = GraphicsProcessing(contour, image)

        # 预处理并生成角度缓存
        if graphics_processing.run_preprocessing():
            pieces.append(graphics_processing)
            print(f"OK (ID: {i})")
        else:
            print("Skip")
    
    if len(pieces) == 0:
        print("\n错误：没有找到有效的零件！")
        return
    
    print(f"\n成功加载 {len(pieces)} 个零件")
    
    # 2. 初始化 NFP 缓存
    print("\n[2/4] 初始化 NFP 缓存...")
    nfp_cache = {}
    
    # 3. 配置遗传算法参数
    print("\n[3/4] 配置遗传算法参数...")
    pop_size = 40
    generations = 100
    visualize_interval = 5  # 每 5 代输出一次可视化
    
    print(f"  种群大小: {pop_size}")
    print(f"  迭代次数: {generations}")
    print(f"  可视化间隔: 每 {visualize_interval} 代")
    print(f"  容器宽度: {settings.width}mm")
    print(f"  允许角度: {settings.angles}")
    print(f"  零件间距: {settings.spacing}mm")
    
    # 4. 定义可视化回调函数
    def visualization_callback(generation, genome, packer):
        """每次迭代时调用，保存可视化结果"""
        output_path = visualize_packing_result(
            packer, 
            generation, 
            output_dir="test", 
            bin_width=settings.width
        )
        print(f"  → 已保存第 {generation} 代可视化结果: {output_path}")

    # 5. 运行遗传算法
    print("\n[4/4] 运行遗传算法优化排料...")
    print("-" * 60)
    
    ga = GA(
        pieces=pieces,
        packer_class=lambda w: Packer(w, settings.length),
        nfp_cache=nfp_cache,
        allowed_angles=settings.angles,
        pop_size=pop_size,
        generations=generations
    )
    
    best_genome = ga.run(
        visualization_callback=visualization_callback,
        visualize_interval=visualize_interval
    )
    
    # 6. 输出最优解
    print("-" * 60)
    print("\n排料完成！")
    print("=" * 60)
    
    # 重新计算最优解的详细信息
    final_packer = Packer(settings.width, settings.length)
    for item in best_genome:
        poly = pieces[item['id']].get_rotated_poly(item['angle'])
        poly_original = pieces[item['id']].get_rotated_poly_original(item['angle'])
        final_packer.add_piece_with_nfp(item['id'], item['angle'], poly, nfp_cache, poly_original)

    print(f"\n最优排料结果 (固定宽度: {settings.width}mm):")
    print(f"  总高度: {final_packer.total_length:.2f}mm")
    print(f"  零件数: {len(final_packer.placed_items)}")
    
    # 计算材料利用率（使用原始未膨胀多边形的面积）
    if len(final_packer.placed_items) > 0:
        total_area = sum(item.get('poly_display', item['poly']).area for item in final_packer.placed_items)
        container_area = settings.width * final_packer.total_length
        utilization = (total_area / container_area * 100) if container_area > 0 else 0
        print(f"  材料利用率: {utilization:.2f}%")
    
    print(f"\n零件放置详情:")
    for item in final_packer.placed_items:
        print(f"  零件 {item['id']}: 位置=({item['x']:.2f}, {item['y']:.2f})mm, 角度={item['angle']}°")
    
    print(f"\n所有迭代结果已保存到 test 文件夹")
    print("=" * 60)


if __name__ == "__main__":
    main()
