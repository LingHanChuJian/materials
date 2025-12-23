# nfp 算法实现
import pyclipper
from settings.settings import settings
from shapely.affinity import translate

class NFP:
    def __init__(self, poly_a, poly_b, gap=settings.spacing, scale=settings.nfp_scale):
        self.poly_a = poly_a
        self.poly_b = poly_b
        self.gap = gap
        self.scale = scale # 精度放缩

    def calculate_nfp(self):
        gap_scaled = max(1, int(round(self.gap * self.scale)))

        # 1. 对齐 B 参考点
        minx_b, miny_b, _, _ = self.poly_b.bounds
        poly_b_aligned = translate(self.poly_b, xoff=-minx_b, yoff=-miny_b)
        path_b = [(int(x*self.scale), int(y*self.scale)) for x, y in poly_b_aligned.exterior.coords]

        # 2. 注入 Gap：对 B 进行偏移
        co = pyclipper.PyclipperOffset()
        # 使用 JT_MITER 保持尖角，JT_ROUND 适合圆角
        co.AddPath(path_b, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)
        # 得到膨胀后的 B 路径
        paths = co.Execute(gap_scaled)
        path_b_offset = max(paths, key=pyclipper.Area)

        # 3. 反转 B 进行 Minkowski 运算
        path_b_inv = [(-x, -y) for x, y in path_b_offset]
        path_a = [(int(x*self.scale), int(y*self.scale)) for x, y in self.poly_a.exterior.coords]
        
        # 4. 执行 Minkowski Sum
        raw_paths = pyclipper.MinkowskiSum(path_a, path_b_inv, True)

        # 5. PolyTree 拓扑解析
        pc = pyclipper.Pyclipper()
        pc.AddPaths(raw_paths, pyclipper.PT_SUBJECT, True)
        poly_tree = pc.Execute2(pyclipper.CT_UNION, pyclipper.PFT_NONZERO)
        
        return {
            "tree": poly_tree,
            "ref_offset": (-minx_b, -miny_b),
            "gap": self.gap
        }


def is_position_valid(poly_tree, x, y, scale=settings.nfp_scale):
    """
    判断点 (x, y) 是否在 NFP 禁区内
    """
    pt = (int(x * scale), int(y * scale))

    # 使用 Clipper 提供的 PointInPolygon
    # 返回值：0-不在多边形内, 1-在多边形内, -1-在边界上

    def check_recursive(node):
        # res: 1(in), -1(on), 0(out)
        res = pyclipper.PointInPolygon(pt, node.Contour)
        if res != 0: # 只要触碰（包含边界 -1），就进入判断
            for child in node.Childs:
                if check_recursive(child):
                    return False # 在孔洞内，安全
            return True # 在实体内，碰撞
        return False

    # 根节点的 Childs 是所有的 Outer Contours
    for outer_node in poly_tree.Childs:
        if check_recursive(outer_node):
            return False # 落在任何一个 NFP 实体内，非法
            
    return True # 所有 NFP 之外，合法
