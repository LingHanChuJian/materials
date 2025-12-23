# 遗传算法实现
import random
import numpy as np
import copy
from settings.settings import settings

class GA:
    def __init__(self, pieces, packer_class, nfp_cache, allowed_angles=settings.angles, pop_size=40, generations=100):
        self.pieces = pieces
        self.pop_size = pop_size
        self.generations = generations
        self.nfp_cache = nfp_cache
        self.packer_class = packer_class
        self.allowed_angles = allowed_angles
        
        # 4️⃣ 修复：Fitness Cache (显著提升计算速度)
        self.fitness_cache = {}

        # 计算每个零件的面积并按降序排列（大料优先）
        piece_areas = []
        for idx, piece in enumerate(pieces):
            # 使用 Shapely 的 area 属性计算面积
            poly = piece.get_rotated_poly(0)  # 使用0度角度计算面积
            area = poly.area
            piece_areas.append((idx, area))
        
        # 按面积降序排列
        piece_areas.sort(key=lambda x: x[1], reverse=True)
        sorted_indices = [idx for idx, area in piece_areas]
        
        # 1️⃣ 修复：支持外部传入角度 + 大料优先策略
        self.population = []
        for i in range(pop_size):
            genome = []
            # 前 20% 的个体：严格按面积降序（精英贪心策略）
            if i < pop_size * 0.2:
                indices = sorted_indices.copy()
            # 中间 60% 的个体：在面积降序基础上引入轻微扰动
            elif i < pop_size * 0.8:
                indices = sorted_indices.copy()
                # 随机交换 2-5 个位置，保持大体有序
                num_swaps = random.randint(2, 5)
                for _ in range(num_swaps):
                    idx1, idx2 = random.sample(range(len(indices)), 2)
                    indices[idx1], indices[idx2] = indices[idx2], indices[idx1]
            # 后 20% 的个体：完全随机（保持种群多样性）
            else:
                indices = list(range(len(pieces)))
                random.shuffle(indices)
            
            for idx in indices:
                genome.append({
                    'id': idx, 
                    'angle': random.choice(self.allowed_angles)
                })
            self.population.append(genome)

    def calculate_fitness(self, genome):
        # 4️⃣ 修复：缓存 key 序列化
        key = tuple((item['id'], item['angle']) for item in genome)
        if key in self.fitness_cache:
            return self.fitness_cache[key]

        packer = self.packer_class(settings.width)
        for item in genome:
            # 获取膨胀版本（用于碰撞检测）
            poly = self.pieces[item['id']].get_rotated_poly(item['angle'])
            # 获取原始版本（用于显示）
            poly_original = self.pieces[item['id']].get_rotated_poly_original(item['angle'])
            # 调用 NFP + Skyline 放置逻辑
            packer.add_piece_with_nfp(item['id'], item['angle'], poly, self.nfp_cache, poly_original)
        
        # 3️⃣ 修复：数值稳定性，使用负长度。追求越大的值越好
        # 增加一个基准值避免负数（如果后续需要做轮盘赌）
        score = -packer.total_length 
        
        self.fitness_cache[key] = score
        return score

    def crossover(self, parent1, parent2):
        """修复 2️⃣：解决 OX 交叉中的共享引用 Bug"""
        size = len(parent1)
        start, end = sorted(random.sample(range(size), 2))
        
        child = [None] * size
        # 使用深拷贝切片，切断与父代的联系
        child[start:end] = copy.deepcopy(parent1[start:end])
        
        # 提取已有的 ID 集合以便快速查找
        existing_ids = {item['id'] for item in child if item is not None}

        p2_ptr = 0
        for i in range(size):
            if child[i] is None:
                while parent2[p2_ptr]['id'] in existing_ids:
                    p2_ptr += 1
                # 必须深拷贝单个 dict
                child[i] = copy.deepcopy(parent2[p2_ptr])
                existing_ids.add(child[i]['id'])

        return child

    def mutate(self, genome):
        """变异：引入多态变异"""
        if random.random() < 0.2: # 交换变异
            idx1, idx2 = random.sample(range(len(genome)), 2)
            genome[idx1], genome[idx2] = genome[idx2], genome[idx1]
        
        if random.random() < 0.1: # 角度变异（从传入的角度集中选）
            idx = random.randint(0, len(genome)-1)
            genome[idx]['angle'] = random.choice(self.allowed_angles)

    def run(self, visualization_callback=None, visualize_interval=10):
        """
        主循环：5️⃣ 强化选择压力与精英策略
        
        Args:
            visualization_callback: 可视化回调函数，接受 (generation, genome, packer) 参数
            visualize_interval: 可视化间隔（每隔多少代输出一次）
        """
        for gen in range(self.generations):
            # 1. 计算适应度
            fitness_scores = [self.calculate_fitness(g) for g in self.population]
            
            # 2. 5️⃣ 强化精英保留：保留前 10% 的个体
            elite_count = max(2, self.pop_size // 10)
            sorted_indices = np.argsort(fitness_scores)[::-1] # 降序排列
            
            best_score = fitness_scores[sorted_indices[0]]
            best_genome = self.population[sorted_indices[0]]
            print(f"Gen {gen}: Best Height = {-best_score:.2f}mm, Cache Size = {len(self.fitness_cache)}")
            
            # 可视化当前最优解
            if visualization_callback and (gen % visualize_interval == 0 or gen == self.generations - 1):
                # 重新计算最优解的排料结果用于可视化
                packer = self.packer_class(settings.width)
                for item in best_genome:
                    poly = self.pieces[item['id']].get_rotated_poly(item['angle'])
                    poly_original = self.pieces[item['id']].get_rotated_poly_original(item['angle'])
                    packer.add_piece_with_nfp(item['id'], item['angle'], poly, self.nfp_cache, poly_original)
                visualization_callback(gen, best_genome, packer)
            
            # 初始下一代：填入深拷贝的精英
            new_population = [copy.deepcopy(self.population[i]) for i in sorted_indices[:elite_count]]
            
            # 3. 填充剩余个体
            while len(new_population) < self.pop_size:
                # 锦标赛选择
                p1, p2 = self.select_parents(fitness_scores)
                child = self.crossover(p1, p2)
                self.mutate(child)
                new_population.append(child)
            
            self.population = new_population

        return self.population[0] # 返回最优解

    def select_parents(self, scores):
        # 增加锦标赛规模可以提升选择压力
        tournament_size = 3
        competitors = random.sample(range(self.pop_size), tournament_size)
        idx1 = competitors[np.argmax([scores[i] for i in competitors])]
        
        competitors = random.sample(range(self.pop_size), tournament_size)
        idx2 = competitors[np.argmax([scores[i] for i in competitors])]
        
        return self.population[idx1], self.population[idx2]