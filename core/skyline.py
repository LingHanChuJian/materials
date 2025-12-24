# skyline 算法实现
from shapely.affinity import translate

class SkylineNode:
    def __init__(self, x, y, width):
        self.x = x
        self.y = y
        self.width = width
    
    def __repr__(self) -> str:
        return f"SkylineNode(x={self.x}, y={self.y}, width={self.width})"

class SkylinePacker:
    def __init__(self, bin_w, bin_h):
        self.bin_w = bin_w
        self.bin_h = bin_h
        # 初始状态：一条位于底部(y=0)、宽度为容器宽度的线段
        self.skyline = [SkylineNode(0, 0, bin_w)]
        self.placed_polygons = []

    def find_best_score(self, rect_w, rect_h):
        """
        在整个天际线中寻找最佳位置
        策略：BL (Bottom-Left) -> 优先 Y 小，Y 相同则 X 小
        """
        best_y = float('inf')
        best_x = float('inf')
        best_index = -1

        for i in range(len(self.skyline)):
            node = self.skyline[i]
            y = self.get_placement_y_at_x(node.x, rect_w)
            
            if y is not None:
                # 这里的 y 是该零件放置后的底部高度
                # 我们可以根据 y + rect_h 是否超过 bin_h 过滤（如果有上限）
                if y + rect_h <= self.bin_h:
                    if y < best_y:
                        best_y = y
                        best_index = i
                        best_x = node.x
                    elif y == best_y: # Y 一样，选 X 小的
                        if node.x < best_x:
                            best_index = i
                            best_x = node.x

        return best_index, best_x, best_y

    def get_placement_y_at_x(self, x_start, rect_w):
        """
        加固版：支持在任意 x 坐标开始检测宽度
        不再依赖 index，而是通过坐标定位
        """
        x_end = x_start + rect_w
        if x_end > self.bin_w:
            return None

        max_y = 0
        # 1. 找到包含 x_start 的起始节点索引
        curr_idx = self._find_node_index_at(x_start)
        if curr_idx is None:
            return None
        
        # 2. 遍历直到覆盖完 x_end
        while curr_idx < len(self.skyline):
            node = self.skyline[curr_idx]
            if node.x >= x_end:
                break
            
            max_y = max(max_y, node.y)
            curr_idx += 1
            
        return max_y
    
    def _find_node_index_at(self, x):
        """
        找到包含 x 的 skyline 节点 index
        要满足: node.x <= x < node.x + node.width
        """
        EPSILON = 1e-6
        for i, node in enumerate(self.skyline):
            if node.x - EPSILON <= x < (node.x + node.width) + EPSILON:
                return i
        return None

    def add_rect(self, poly, rect_w, rect_h):
        """将多边形及其包络框放入 Skyline"""
        idx, best_x, best_y = self.find_best_score(rect_w, rect_h)
        
        if idx == -1:
            return False # 装不下了
            
        best_x = self.skyline[idx].x
        
        # 1. 移动 Shapely 多边形到目标位置
        # 注意：我们的 poly 已经在预处理中对齐到了 (0,0)
        placed_poly = translate(poly, xoff=best_x, yoff=best_y)
        self.placed_polygons.append(placed_poly)
        
        # 2. 更新天际线
        self._update_skyline(best_x, best_y + rect_h, rect_w)
        return True

    def _update_skyline(self, x, y, w):
        """
        核心加固：将节点更新逻辑抽象为“区域重写”
        
        """
        x_end = x + w
        new_nodes = []
        inserted = False

        for node in self.skyline:
            # 情况 1：完全在更新区域左侧 -> 保留
            if node.x + node.width <= x:
                new_nodes.append(node)
            
            # 情况 2：完全在更新区域右侧 -> 保留
            elif node.x >= x_end:
                if not inserted:
                    new_nodes.append(SkylineNode(x, y, w))
                    inserted = True
                new_nodes.append(node)
                
            # 情况 3：有重叠（复杂分裂区）
            else:
                # 3.1 左侧有剩余 -> 切出左段保留
                if node.x < x:
                    new_nodes.append(SkylineNode(node.x, node.y, x - node.x))
                
                # 3.2 插入新节点（仅执行一次）
                if not inserted:
                    new_nodes.append(SkylineNode(x, y, w))
                    inserted = True
                    
                # 3.3 右侧有剩余 -> 切出右段保留
                if node.x + node.width > x_end:
                    new_nodes.append(SkylineNode(x_end, node.y, (node.x + node.width) - x_end))

        if not inserted:
            new_nodes.append(SkylineNode(x, y, w))

        self.skyline = new_nodes

        self._merge_skyline() # 紧接着进行相同高度合并

    def _merge_skyline(self):
        i = 0
        while i < len(self.skyline) - 1:
            if self.skyline[i].y == self.skyline[i+1].y:
                self.skyline[i].width += self.skyline[i+1].width
                self.skyline.pop(i+1)
            else:
                i += 1
