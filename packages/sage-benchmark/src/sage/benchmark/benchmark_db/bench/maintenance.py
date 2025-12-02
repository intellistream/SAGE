"""
Maintenance State and Policy

管理索引维护状态和策略
"""


class MaintenanceState:
    """
    跟踪索引维护状态
    """

    def __init__(self):
        self.live_intervals: list[tuple[int, int]] = []  # 活跃数据区间
        self.live_points: int = 0  # 活跃数据点数
        self.deleted_points: int = 0  # 已删除数据点数
        self.rebuild_count: int = 0  # 重建次数
        self.budget_spent_us: float = 0.0  # 已使用的维护预算 (微秒)
        self.current_min_id: int = 0  # 当前最小 ID
        self.current_max_id: int = 0  # 当前最大 ID

    def _recalculate(self) -> None:
        """重新计算统计信息"""
        self.live_points = sum(end - start for start, end in self.live_intervals)
        if self.live_intervals:
            self.current_min_id = self.live_intervals[0][0]
            self.current_max_id = self.live_intervals[-1][1]
        else:
            self.current_min_id = 0
            self.current_max_id = 0

    def _add_interval(self, start: int, end: int) -> None:
        """添加数据区间"""
        if start >= end:
            return

        merged: list[tuple[int, int]] = []
        inserted = False

        for cur_start, cur_end in self.live_intervals:
            if cur_end < start:
                merged.append((cur_start, cur_end))
            elif end < cur_start:
                if not inserted:
                    merged.append((start, end))
                    inserted = True
                merged.append((cur_start, cur_end))
            else:
                # 有重叠，合并
                start = min(start, cur_start)
                end = max(end, cur_end)

        if not inserted:
            merged.append((start, end))

        merged.sort()
        self.live_intervals = merged
        self._recalculate()

    def _remove_interval(self, start: int, end: int) -> int:
        """移除数据区间，返回移除的数据点数"""
        if start >= end or not self.live_intervals:
            return 0

        removed = 0
        updated: list[tuple[int, int]] = []

        for cur_start, cur_end in self.live_intervals:
            if cur_end <= start or cur_start >= end:
                # 无重叠
                updated.append((cur_start, cur_end))
                continue

            # 有重叠
            overlap_start = max(cur_start, start)
            overlap_end = min(cur_end, end)
            removed += max(0, overlap_end - overlap_start)

            # 保留非重叠部分
            if cur_start < start:
                updated.append((cur_start, start))
            if cur_end > end:
                updated.append((end, cur_end))

        updated = [(s, e) for s, e in updated if e > s]
        updated.sort()
        self.live_intervals = updated
        self._recalculate()
        return removed

    def record_initial_range(self, start: int, end: int) -> None:
        """记录初始加载范围"""
        self.live_intervals = []
        self.deleted_points = 0
        self._add_interval(start, end)

    def record_insert_range(self, start: int, end: int) -> None:
        """记录插入范围"""
        count = max(end - start, 0)
        if count <= 0:
            return
        self._add_interval(start, end)

    def record_delete_range(self, start: int, end: int) -> None:
        """记录删除范围"""
        removed = self._remove_interval(start, end)
        if removed > 0:
            self.deleted_points += removed

    def record_rebuild(self, intervals: list[tuple[int, int]], cost_us: float) -> None:
        """记录重建事件"""
        self.live_intervals = []
        for start, end in intervals:
            self._add_interval(start, end)
        self.deleted_points = 0
        self.rebuild_count += 1
        self.budget_spent_us += max(cost_us, 0.0)

    def get_intervals(self) -> list[tuple[int, int]]:
        """获取当前活跃区间"""
        return list(self.live_intervals)

    def deletion_ratio(self) -> float:
        """计算删除率"""
        total = self.live_points + self.deleted_points
        if total == 0:
            return 0.0
        return self.deleted_points / total


class MaintenancePolicy:
    """
    索引维护策略
    """

    def __init__(self, thresholds: dict = None):
        """
        Args:
            thresholds: 算法特定的删除率阈值
                例如: {'freshdiskann': 0.15, 'default': 0.20}
        """
        if thresholds is None:
            thresholds = {
                "freshdiskann": 0.15,
                "ipdiskann": 0.20,
                "default": 0.25,
            }
        self.thresholds = thresholds

    def should_execute(self, state: MaintenanceState, algo_name: str, forced: bool = False) -> bool:
        """
        判断是否应该执行维护

        Args:
            state: 维护状态
            algo_name: 算法名称
            forced: 是否强制执行

        Returns:
            是否应该执行维护
        """
        if forced:
            return True

        # 获取算法特定的阈值
        algo_name_lower = algo_name.lower()
        threshold = self.thresholds.get(algo_name_lower, self.thresholds["default"])

        # 检查删除率
        ratio = state.deletion_ratio()
        return ratio >= threshold
