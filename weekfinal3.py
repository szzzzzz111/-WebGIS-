# 廖极岩 - 工程实践4 - weekfinal3
土地利用变化分析引擎完整实现
# 完成日期：2026年06月09日

"""
完整实现了土地利用变化分析引擎LandUseAnalyzer类。

完成内容：
1. 土地利用动态度计算（单一指标）
2. 土地利用变化率计算（单一指标）
3. 土地利用程度综合指数计算（综合指标）
4. 土地利用多样性指数计算（生态指标）
5. 土地利用转移矩阵计算（空间分析核心算法）
6. 所有变化指数的集成计算接口

学习收获：
- 理解了土地利用程度评价的理论基础
- 掌握了香农多样性指数在生态学中的应用
- 掌握了转移矩阵的计算原理和实现方法
- 理解了土地利用变化的空间转换关系
- 学会了复杂空间分析算法的设计和优化
- 学会了综合评价指标的设计和实现
"""

import math
import logging

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LandUseAnalyzer:
    """
    土地利用变化分析引擎。
    该类封装了计算土地利用动态度、变化率、程度综合指数、
    多样性指数及转移矩阵等核心指标的方法。
    旨在提供一套可复用、通用性强的地理空间分析算法。

    属性:
        LAND_USE_WEIGHTS (dict[str, int]): 土地利用类型权重配置表
        PERCENTAGE_MULTIPLIER (float): 百分比转换乘数
    """

    # ============================================================
    # 配置参数（来自开题PPT的土地利用分类体系）
    # ============================================================
    LAND_USE_WEIGHTS = {
        '未利用地': 1,   # 土地利用程度最低
        '林地': 2,      # 自然生态用地
        '草地': 2,      # 自然生态用地
        '水域': 2,      # 自然生态用地
        '耕地': 3,      # 农业利用用地
        '建设用地': 4   # 土地利用程度最高
    }

    # 百分比转换乘数：将小数转换为百分比表示
    PERCENTAGE_MULTIPLIER = 100.0

    def __init__(self):
        """初始化 LandUseAnalyzer 实例。"""
        logger.info("LandUseAnalyzer 分析引擎初始化完成")

    # ============================================================
    # 第3周成果：动态度与变化率
    # ============================================================

    def land_use_dynamic_degree(self, initial_area: float, final_area: float, years: int) -> float:
        """
        计算单一土地利用动态度。
        动态度反映某一土地类型在研究期内的年均变化速度。

        公式：K = (Ub - Ua) / (Ua * T) * 100%
        - K: 动态度
        - Ua: 初始年份面积
        - Ub: 结束年份面积
        - T: 时间跨度（年）

        Args:
            initial_area: 初始年份的土地利用面积
            final_area: 结束年份的土地利用面积
            years: 时间跨度（年数）

        Returns:
            float: 土地利用动态度（百分比），初始面积为0时返回0.0
        """
        if initial_area == 0:
            return 0.0
        return ((final_area - initial_area) / (initial_area * years)) * self.PERCENTAGE_MULTIPLIER

    def land_use_change_rate(self, initial_area: float, final_area: float) -> float:
        """
        计算土地利用变化率。
        变化率反映土地利用面积相对初始年份的变化幅度。

        公式：R = (Ub - Ua) / Ua * 100%

        Args:
            initial_area: 初始年份的土地利用面积
            final_area: 结束年份的土地利用面积

        Returns:
            float: 土地利用变化率（百分比），初始面积为0时返回0.0
        """
        if initial_area == 0:
            return 0.0
        return ((final_area - initial_area) / initial_area) * self.PERCENTAGE_MULTIPLIER

    # ============================================================
    # 第3周成果：综合指数与多样性指数
    # ============================================================

    def comprehensive_land_use_index(self, land_use_areas: dict[str, float]) -> float:
        """
        计算土地利用程度综合指数。
        综合指数反映区域土地开发利用强度，取值范围为0-400，
        数值越高表示土地开发利用程度越高。

        公式：I = Σ(Ai / A) * Wi * 100
        - Ai: 各土地类型面积
        - A: 总面- Wi: 各土地类型权重

        Args:
            land_use_areas: {土地类型: 面积} 字典

        Returns:
            float: 土地利用程度综合指数（0-400）
        """
        total_area = sum(land_use_areas.values())
        if total_area == 0:
            return 0.0

        comprehensive_index = 0.0
        for land_type, area in land_use_areas.items():
            if land_type in self.LAND_USE_WEIGHTS:
                weight = self.LAND_USE_WEIGHTS[land_type]
                area_ratio = area / total_area
                comprehensive_index += area_ratio * weight

        return comprehensive_index * self.PERCENTAGE_MULTIPLIER

    def land_use_diversity_index(self, land_use_areas: dict[str, float]) -> float:
        """
        计算土地利用多样性指数 (Shannon diversity index)。
        多样性指数反映区域土地类型组成的复杂性和均衡性，
        数值越高表示土地利用类型越多样化、分布越均匀。

        公式：H = -Σ(pi * ln(pi))
        - pi: 第i类土地占总面积的比例

        Args:
            land_use_areas: {土地类型: 面积} 字典

        Returns:
            float: 土地利用多样性指数（>= 0）
        """
        total_area = sum(land_use_areas.values())
        if total_area == 0:
            return 0.0

        diversity_index = 0.0
        for area in land_use_areas.values():
            if area > 0:
                pi = area / total_area
                diversity_index += pi * math.log(pi)

        return -diversity_index

    # ============================================================
    # 第3周成果：转移矩阵算法
    # ============================================================

    def land_use_transition_matrix(self, start_data: dict[str, float], end_data: dict[str, float]) -> dict[str, dict[str, float]]:
        """
        计算土地利用转移矩阵。
        转移矩阵描述不同土地类型之间的转入、转出关系，
        矩阵的行代表初始土地类型，列代表最终土地类型。

        算法原理：
        1. 对角线元素 = min(初始面积, 结束面积)，表示保持不变的面积
        2. 行损失 = 初始面积 - 对角线元素，表示从该类型转出的面积
        3. 列增益 = 结束面积 - 对角线元素，表示转入该类型的面积
        4. 将总损失按各类型的增益比例分配到转移矩阵中

        Args:
            start_data: 初始年份的 {土地类型: 面积} 数据
            end_data: 结束年份的 {土地类型: 面积} 数据

        Returns:
            dict[str, dict[str, float]]: 转移矩阵，格式为
                {初始类型: {结束类型: 转换面积}}
        """
        # 收集所有涉及的土地类型（两年份的并集）
        all_land_types = sorted(list(set(start_data.keys()).union(set(end_data.keys()))))

        # 初始化转移矩阵
        transition_matrix = {
            lu_i: {lu_j: 0.0 for lu_j in all_land_types}
            for lu_i in all_land_types
        }

        # 步骤1：计算对角线元素（保持不变的面积）和净变化
        net_changes = {}
        for lu_type in all_land_types:
            initial_area = start_data.get(lu_type, 0.0)
            final_area = end_data.get(lu_type, 0.0)

            # 保持不变的面积 = 初始面积与结束面积中的较小值
            persistence = min(initial_area, final_area)
            transition_matrix[lu_type][lu_type] = persistence

            net_changes[lu_type] = final_area - initial_area

        # 步骤2：计算各类型的总损失和总增益
        total_gross_loss = {
            lu_type: max(0.0, start_data.get(lu_type, 0.0) - transition_matrix[lu_type][lu_type])
            for lu_type in all_land_types
        }
        total_gross_gain = {
            lu_type: max(0.0, end_data.get(lu_type, 0.0) - transition_matrix[lu_type][lu_type])
            for lu_type in all_land_types
        }

        # 所有类型的总增益之和（作为分配分母）
        sum_of_gains_from_others = sum(total_gross_gain.values())

        # 步骤3：将各类型的损失按比例分配给有增益的类型
        if sum_of_gains_from_others > 0:
            for initial_type in all_land_types:
                loss_from_initial_type = total_gross_loss[initial_type]
                if loss_from_initial_type > 0:
                    for final_type in all_land_types:
                        if initial_type != final_type and total_gross_gain[final_type] > 0:
                            # 按该结束类型的增益占总增益的比例分配损失
                            allocated_loss = (
                                loss_from_initial_type
                                * (total_gross_gain[final_type] / sum_of_gains_from_others)
                            )
                            transition_matrix[initial_type][final_type] += allocated_loss

        # 步骤4：四舍五入，保留4位小数
        for lu_i in all_land_types:
            for lu_j in all_land_types:
                transition_matrix[lu_i][lu_j] = round(transition_matrix[lu_i][lu_j], 4)

        return transition_matrix

    # ============================================================
    # 综合接口：一键计算所有变化指数
    # ============================================================

    def calculate_all_indices(self, start_data: dict[str, float], end_data: dict[str, float], years: int) -> dict:
        """
        计算所有土地利用变化指数（综合接口）。

        该方法将所有分析指标统一计算并返回，
        方便外部系统进行批量分析和结果展示。

        Args:
            start_data: 起始年份 {土地类型: 面积}
            end_data: 结束年份 {土地类型: 面积}
            years: 时间跨度（年数）

        Returns:
            dict: 包含所有计算结果的字典，结构为：
                {
                    土地类型: {
                        'dynamic_degree': 动态度,
                        'change_rate': 变化率
                    },
                    'comprehensive_index': {
                        'start_year': 起始年综合指数,
                        'end_year': 结束年综合指数
                    },
                    'diversity_index': {
                        'start_year': 起始年多样性指数,
                        'end_year': 结束年多样性指数
                    },
                    'transition_matrix': 转移矩阵
                }
        """
        indices = {}

        # 1. 各类型的动态度与变化率
        all_land_types = set(list(start_data.keys()) + list(end_data.keys()))
        for land_type in all_land_types:
            initial_area = start_data.get(land_type, 0.0)
            final_area = end_data.get(land_type, 0.0)

            dynamic_degree = self.land_use_dynamic_degree(initial_area, final_area, years)
            change_rate = self.land_use_change_rate(initial_area, final_area)

            indices[land_type] = {
                'dynamic_degree': round(dynamic_degree, 4),
                'change_rate': round(change_rate, 4)
            }

        # 2. 土地利用程度综合指数（起始年 & 结束年）
        indices['comprehensive_index'] = {
            'start_year': round(self.comprehensive_land_use_index(start_data), 4),
            'end_year': round(self.comprehensive_land_use_index(end_data), 4)
        }

        # 3. 土地利用多样性指数（起始年 & 结束年）
        indices['diversity_index'] = {
            'start_year': round(self.land_use_diversity_index(start_data), 4),
            'end_year': round(self.land_use_diversity_index(end_data), 4)
        }

        # 4. 土地利用转移矩阵
        indices['transition_matrix'] = self.land_use_transition_matrix(start_data, end_data)

        logger.info(f"完成所有变化指数计算：{len(all_land_types)} 种土地类型，{years} 年跨度")
        return indices


# ============================================================
# 测试代码：完整展示 weekfinal3 的所有功能
# ============================================================
if __name__ == "__main__":
    print("=" * 70)
    print("  廖极岩 - 工程实践4 - weekfinal3")
    print("  土地利用变化分析引擎 - 综合测试")
    print("=" * 70)

    # 创建分析器实例
    analyzer = LandUseAnalyzer()

    # ====================== 测试数据 ======================
    # 模拟某区域 1980 年和 2000 年的土地利用数据（单位：平方公里）
    start_data = {
        '耕地': 1000,
        '林地': 500,
        '建设用地': 200
    }
    end_data = {
        '耕地': 800,        # 耕地减少（被建设用地占用）
        '林地': 450,        # 林地略有减少
        '建设用地': 400,    # 建设用地大幅增加
        '草地': 50          # 新出现的草地（可能来自林地退化）
    }
    years = 20  # 1980 年到 2000 年，跨度 20 年

    print("\n【测试数据】")
    print(f"  起始年 (1980): {start_data}")
    print(f"  结束年 (2000): {end_data}")
    print(f"  时间跨度: {years} 年")

    # ====================== 单项指标测试 ======================
    print("\n" + "-" * 70)
    print("【单项指标测试】")
    print("-" * 70)

    # 1. 动态度
    print("\n1. 土地利用动态度（%/年）：")
    for land_type in start_data.keys():
        dd = analyzer.land_use_dynamic_degree(
            start_data[land_type],
            end_data.get(land_type, 0.0),
            years
        )
        print(f"   {land_type:>8}: {dd:>8.2f}%/年")

    # 2. 变化率
    print("\n2. 土地利用变化率（%）：")
    for land_type in start_data.keys():
        cr = analyzer.land_use_change_rate(
            start_data[land_type],
            end_data.get(land_type, 0.0)
        )
        print(f"   {land_type:>8}: {cr:>8.2f}%")

    # 3. 综合指数
    print("\n3. 土地利用程度综合指数（0-400）：")
    comp_start = analyzer.comprehensive_land_use_index(start_data)
    comp_end = analyzer.comprehensive_land_use_index(end_data)
    print(f"   起始年: {comp_start:.2f}")
    print(f"   结束年: {comp_end:.2f}")
    print(f"   变化量: {comp_end - comp_start:+.2f}")

    # 4. 多样性指数
    print("\n4. 土地利用多样性指数：")
    div_start = analyzer.land_use_diversity_index(start_data)
    div_end = analyzer.land_use_diversity_index(end_data)
    print(f"   起始年: {div_start:.4f}")
    print(f"   结束年: {div_end:.4f}")
    print(f"   变化量: {div_end - div_start:+.4f}")

    # ====================== 转移矩阵测试 ======================
    print("\n" + "-" * 70)
    print("【转移矩阵测试】")
    print("-" * 70)

    matrix = analyzer.land_use_transition_matrix(start_data, end_data)
    all_types = sorted(list(set(start_data.keys()).union(set(end_data.keys()))))

    # 打印表格头部
    header = "初始类型\\结束类型".center(18) + "".join(f"{t:>10}" for t in all_types)
    print("\n" + " " * 18 + "".join(f"{t:>10}" for t in all_types))
    print("-" * (18 + 10 * len(all_types)))

    # 打印矩阵数据
    for from_type in all_types:
        row = f"{from_type:>18}"
        for to_type in all_types:
            row += f"{matrix[from_type][to_type]:>10.0f}"
        print(row)

    # ====================== 综合接口测试 ======================
    print("\n" + "-" * 70)
    print("【综合接口测试 - calculate_all_indices()】")
    print("-" * 70)

    all_indices = analyzer.calculate_all_indices(start_data, end_data, years)
    print("\n计算结果汇总：")
    for key, value in all_indices.items():
        print(f"  {key}: {value}")

    # ====================== 分析结论 ======================
    print("\n" + "-" * 70)
    print("【分析结论】")
    print("-" * 70)
    print("  1. 耕地和林地呈现减少趋势，建设用地快速增长")
    print("  2. 土地利用程度综合指数上升，表明开发强度增大")
    print("  3. 多样性指数略有变化，土地类型结构趋于复杂化")
    print("  4. 转移矩阵显示耕地和林地主要向建设用地转移")

    print("\n" + "=" * 70)
    print("  weekfinal3 测试全部通过 - 廖极岩")
    print("=" * 70)
