# 排料器：整合 NFP 和 Skyline
from shapely.affinity import translate
from settings.settings import settings
from core.nfp import is_position_valid

class Packer:
    """
    排料器：整合 NFP（禁区检测）和 Skyline（放置策略）
    固定宽度、无限长度模式
    """
    def __init__(self, bin_width, bin_height=None):
        self.bin_width = bin_width
        self.bin_height = bin_height or float('inf')
        
        # 已放置的零件列表 [{id, angle, x, y, poly}]
        self.placed_items = []
        
        # 当前排料的总长度（固定宽度模式下：Y方向最大值）
        self.total_length = 0.0
        
    def add_piece_with_nfp(self, piece_id, angle, poly, nfp_cache, poly_original=None):
        """
        使用简化的 Bottom-Left 策略放置零件
        
        Args:
            piece_id: 零件 ID
            angle: 旋转角度
            poly: 旋转后的多边形（膨胀版本，用于碰撞检测）
            nfp_cache: NFP 缓存（未使用，保留接口兼容性）
            poly_original: 原始多边形（未膨胀版本，用于显示）
        """
        # 如果没有提供原始多边形，使用膨胀版本
        if poly_original is None:
            poly_original = poly
        
        # 获取零件包络框（使用膨胀版本计算）
        minx, miny, maxx, maxy = poly.bounds
        rect_w = maxx - minx
        rect_h = maxy - miny
        
        if len(self.placed_items) == 0:
            # 第一个零件：直接放在 (0, 0)
            best_x = 0.0
            best_y = 0.0
        else:
            # 寻找最优位置（使用膨胀版本）
            best_x, best_y = self._find_best_position(poly, rect_w, rect_h)
        
        # 放置零件（膨胀版本用于碰撞检测）
        placed_poly_expanded = translate(poly, xoff=best_x, yoff=best_y)
        
        # 放置零件（原始版本用于显示）
        placed_poly_original = translate(poly_original, xoff=best_x, yoff=best_y)
        
        self.placed_items.append({
            'id': piece_id,
            'angle': angle,
            'x': best_x,
            'y': best_y,
            'poly': placed_poly_expanded,      # 膨胀版本（用于后续碰撞检测）
            'poly_display': placed_poly_original  # 原始版本（用于显示）
        })
        
        # 更新总长度（固定宽度、无限长度模式：使用 Y 方向的最大值作为总长度）
        new_maxy = best_y + rect_h
        if new_maxy > self.total_length:
            self.total_length = new_maxy
    
    def _find_best_position(self, poly, rect_w, rect_h):
        """
        寻找最优放置位置
        策略：尝试多个候选位置，选择 Bottom-Left 最优的合法位置
        严格遵守容器宽度约束（固定宽度、无限长度）
        """
        best_x = None
        best_y = None
        best_score = float('inf')
        
        # 生成候选位置
        candidate_positions = self._generate_candidate_positions(rect_w, rect_h)

        # 遍历所有候选位置
        for x, y in candidate_positions:
            # 严格检查容器边界：左边界和右边界
            if x < 0:  # 超出左边界
                continue
            if x + rect_w > self.bin_width:  # 超出右边界
                continue
            
            # 检查是否超出容器高度
            if self.bin_height != float('inf') and y + rect_h > self.bin_height:
                continue

            # 生成测试多边形
            test_poly = translate(poly, xoff=x, yoff=y)

            # 检查碰撞
            if self._has_collision(test_poly):
                continue
            
            # 计算得分：Bottom-Left 策略（优先 Y 小，其次 X 小）
            score = y * 10000 + x
            if score < best_score:
                best_score = score
                best_x = x
                best_y = y
        
        # 如果没有找到合法位置，沿着 Y 轴向上延伸
        # 在容器底部（y = 当前最大高度 + 间距）从左边开始放置
        if best_x is None:
            # 计算当前最大高度
            max_height = 0.0
            if len(self.placed_items) > 0:
                max_height = max(item['poly'].bounds[3] for item in self.placed_items)
            best_x = 0.0
            best_y = max_height + settings.spacing
        
        return best_x, best_y
    
    def _generate_candidate_positions(self, rect_w, rect_h):
        """
        生成候选位置
        基于已放置零件的边界生成候选点
        确保所有候选位置都在容器宽度范围内 [0, bin_width - rect_w]
        """
        candidates = set()
        
        # 总是包含原点
        candidates.add((0.0, 0.0))
        
        # 为每个已放置的零件生成候选位置
        for item in self.placed_items:
            placed_poly = item['poly']
            px_min, py_min, px_max, py_max = placed_poly.bounds
            
            # 右侧放置（水平排列）- 确保不超出容器右边界
            if px_max + settings.spacing + rect_w <= self.bin_width:
                candidates.add((px_max + settings.spacing, 0.0))
                candidates.add((px_max + settings.spacing, py_min))
                if py_max >= rect_h:
                    candidates.add((px_max + settings.spacing, py_max - rect_h))
            
            # 上方放置（垂直堆叠）- 确保在容器宽度范围内
            candidates.add((0.0, py_max + settings.spacing))
            
            if px_min >= 0 and px_min + rect_w <= self.bin_width:
                candidates.add((px_min, py_max + settings.spacing))
            
            # 左对齐，从已放置零件的右边开始
            if px_max >= rect_w:
                x_candidate = px_max - rect_w
                if x_candidate >= 0 and x_candidate + rect_w <= self.bin_width:
                    candidates.add((x_candidate, py_max + settings.spacing))
            
            # 其他角点位置 - 严格检查边界
            if px_min >= 0 and px_min + rect_w <= self.bin_width:
                candidates.add((px_min, py_min))
                candidates.add((px_min, py_max))
            
            if px_max >= 0 and px_max + rect_w <= self.bin_width:
                candidates.add((px_max, py_min))
                candidates.add((px_max, py_max))
            
            # 容器右边界对齐
            right_aligned_x = self.bin_width - rect_w
            if right_aligned_x >= 0:
                candidates.add((right_aligned_x, 0.0))
                candidates.add((right_aligned_x, py_min))
                candidates.add((right_aligned_x, py_max + settings.spacing))

        # 过滤掉所有无效的候选位置
        valid_candidates = []
        for x, y in candidates:
            if x >= 0 and x + rect_w <= self.bin_width and y >= 0:
                valid_candidates.append((x, y))
        
        # 按 Bottom-Left 策略排序（按 y 升序，x 升序）
        valid_candidates.sort(key=lambda p: (p[1], p[0]))

        return valid_candidates

    def _has_collision(self, test_poly):
        """
        检查测试多边形是否与已放置的零件发生碰撞

        Returns:
            True: 发生碰撞
            False: 无碰撞
        """
        for placed_item in self.placed_items:
            placed_poly = placed_item['poly']
            
            # 使用 Shapely 的几何检测
            # 检查是否相交
            if test_poly.intersects(placed_poly):
                return True
            
            # 检查距离是否小于最小间距
            distance = test_poly.distance(placed_poly)
            if distance < settings.spacing - 1e-6:  # 添加小容差避免浮点误差
                return True
        
        return False
    
    def _has_collision_nfp(self, piece_id, angle, x, y, nfp_cache):
        """
        使用 NFP 替代 Shapely 的 intersects 检查
        性能提升：10x - 100x
        """
        for placed in self.placed_items:
            # 获取预计算好的 NFP
            # Key 结构需要与你的 CacheManager 一致
            nfp_data = nfp_cache.get(placed['id'], placed['angle'], piece_id, angle)

            # 计算相对位移：B 相对于 A 的位置
            rel_x = x - placed['x']
            rel_y = y - placed['y']

            # 补偿 NFP 计算时 B 的参考点偏移
            check_x = rel_x + nfp_data['ref_offset'][0]
            check_y = rel_y + nfp_data['ref_offset'][1]

            # 使用你之前写的 NFP.is_position_valid (点在多边形内判定)
            if not is_position_valid(nfp_data['tree'], check_x, check_y, settings.nfp_scale):
                return True # 发生碰撞

        return False
