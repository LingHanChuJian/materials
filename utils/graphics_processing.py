from utils.pixel import pixel_to_mm
from settings.settings import settings
from shapely.geometry import Polygon

from shapely.geometry import Polygon
from shapely.affinity import translate, rotate

class GraphicsProcessing:
    def __init__(self, contour, original_image):
        self.contour = contour
        self.original_image = original_image

        # 角度缓存（两个版本）
        self.angle_cache = {}           # 膨胀后的多边形（用于排料碰撞检测）
        self.angle_cache_original = {}  # 原始多边形（用于可视化显示）

    def run_preprocessing(self):
        """执行主预处理流程并生成不同角度的缓存"""
        # 1. 基础预处理（得到 0 度多边形 - 原始版本）
        poly_0_original = self._process_base_original()
        
        if poly_0_original is None:
            return False

        # 2. 为每个角度生成两个版本的多边形
        for angle in settings.angles:
            # 原始版本（用于显示）
            poly_original = self._rotate_poly(poly_0_original, angle)
            self.angle_cache_original[angle] = poly_original
            
            # 膨胀版本（用于排料）
            if settings.spacing > 0:
                poly_expanded = poly_original.buffer(
                    settings.spacing / 2, 
                    join_style=2,  # Mitered join
                    cap_style=2,   # Flat cap
                    mitre_limit=5.0
                )
                # 如果 buffer 产生了 MultiPolygon，取最大的
                if poly_expanded.geom_type == 'MultiPolygon':
                    poly_expanded = max(poly_expanded.geoms, key=lambda a: a.area)
                # 重新对齐到原点
                poly_expanded = self._normalize_alignment(poly_expanded)
            else:
                poly_expanded = poly_original

            self.angle_cache[angle] = poly_expanded
            
        return True

    def get_poly(self, angle):
        """快速获取指定角度的多边形（供遗传算法直接调用）"""
        return self.angle_cache.get(angle)

    def _process_base_original(self):
        """处理原始多边形（不膨胀，用于显示）"""
        h, _ = self.original_image.shape[:2]
        h_mm = pixel_to_mm(h)

        points = []
        for point in self.contour:
            x, y = point[0]
            points.append((pixel_to_mm(x), h_mm - pixel_to_mm(y)))

        if len(points) < 3: 
            return None

        # 修复自相交
        poly = Polygon(points).buffer(0)
        
        # 简化多边形
        poly = poly.simplify(tolerance=settings.tolerance, preserve_topology=True)
        
        # 如果产生了多个多边形，取最大的
        if poly.geom_type == 'MultiPolygon':
            poly = max(poly.geoms, key=lambda a: a.area)

        # 标准化对齐到 (0,0)
        return self._normalize_alignment(poly)

    def _rotate_poly(self, poly, angle):
        poly = rotate(poly, angle, origin="centroid")
        return self._normalize_alignment(poly)
    
    def get_rotated_poly(self, angle):
        """快速获取指定角度的多边形（膨胀版本，用于排料碰撞检测）"""
        return self.angle_cache.get(angle)
    
    def get_rotated_poly_original(self, angle):
        """快速获取指定角度的原始多边形（未膨胀版本，用于可视化显示）"""
        return self.angle_cache_original.get(angle)

    def _normalize_alignment(self, poly):
        """统一的标准化函数：修复有效性并对齐原点"""
        if not poly.is_valid:
            poly = poly.buffer(0)
        mx, my, _, _ = poly.bounds
        poly = translate(poly, xoff=-mx, yoff=-my)
        return poly
