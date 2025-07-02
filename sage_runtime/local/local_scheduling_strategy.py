from typing import List,Optional,Dict
import logging
from sage_runtime.local import Slot


class SchedulingStrategy:
    def select_slot(self, node, slots: List[Slot]) -> Optional[Slot]:
        raise NotImplementedError

class ResourceAwareStrategy(SchedulingStrategy):
    """基于资源利用率的调度策略"""
    #基于当前的slot的负荷选择负荷最少的slot

    def __init__(self):
        self.logger = logging.getLogger(type(self).__name__)

    def select_slot(self, node, slots: List[Slot]) -> int :
        return next((
            s for s in sorted(slots, key=lambda x: x.current_load)
            if s.current_load < s.max_load
        )).slot_id

class PriorityStrategy(SchedulingStrategy):
    """带优先级的调度策略,输入为优先级的映射"""
    def __init__(self, priority_map: Dict[str, int]) :
        self.priority_map = priority_map  # 节点类型到优先级的映射
        self.logger = logging.getLogger(type(self).__name__)
    def select_slot(self, node, slots: List[Slot]) -> int :
        prioritized = sorted(
            slots,
            key=lambda s: (
                -self.priority_map.get(node.name, 0),
                s.current_load
            )
        )
        return next((s for s in prioritized if s.current_load < s.max_load)).slot_id
