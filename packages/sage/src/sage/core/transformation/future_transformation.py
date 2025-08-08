from __future__ import annotations
from typing import TYPE_CHECKING
from .base_transformation import BaseTransformation
from sage.core.operator.future_operator import FutureOperator

if TYPE_CHECKING:
    from sage.core.api.base_environment import BaseEnvironment


class FutureTransformation(BaseTransformation):
    """
    特殊的transformation，用作反馈边的占位符。
    在DAG构建阶段作为placeholder，在fill_future时被实际的transformation替换。
    """
    
    def __init__(self, env: 'BaseEnvironment', name: str):
        # 使用一个特殊的function作为占位符
        from sage.core.api.function.future_function import FutureFunction
        
        # 设置operator类（必须在super().__init__之前）
        self.operator_class = FutureOperator
        
        super().__init__(
            env=env,
            function=FutureFunction,
            name=name,
            parallelism=1
        )
        
        # FutureTransformation特有属性
        self.is_future = True
        self.filled = False
        self.actual_transformation = None
        self.future_name = name
        
        self.logger.debug(f"Created FutureTransformation: {name}")
    
    def fill_with_transformation(self, actual_transformation: BaseTransformation) -> None:
        """
        用实际的transformation填充这个future placeholder
        
        Args:
            actual_transformation: 要填充的实际transformation
        """
        if self.filled:
            raise RuntimeError(f"Future transformation '{self.future_name}' has already been filled")
        
        self.actual_transformation = actual_transformation
        self.filled = True
        
        # 重定向所有下游连接
        self._redirect_downstreams()
        
        # 标记为已填充，但保留在pipeline中以便compiler能够处理
        # compiler会检查filled状态来决定如何处理这个transformation
        # self._mark_as_filled_in_pipeline()
        
        self.logger.debug(f"Filled FutureTransformation '{self.future_name}' with {actual_transformation.basename}")
    
    # def _mark_as_filled_in_pipeline(self) -> None:
    #     """
    #     将已填充的future transformation从pipeline中移除，并保存到filled_futures中
    #     这样compiler就看不到future transformations，只看到实际的反馈边连接
    #     """
    #     # 将该future transformation从pipeline中移除
    #     if self in self.env._pipeline:
    #         self.env._pipeline.remove(self)
    #         self.logger.debug(f"Removed FutureTransformation '{self.future_name}' from pipeline")
        
    #     # 保存填充信息到环境中，供调试和管理使用
    #     if not hasattr(self.env, '_filled_futures'):
    #         self.env._filled_futures = {}
        
    #     self.env._filled_futures[self.future_name] = {
    #         'future_transformation': self,
    #         'actual_transformation': self.actual_transformation,
    #         'filled_at': self._get_current_timestamp()
    #     }
        
    #     self.logger.info(f"Future transformation '{self.future_name}' filled and removed from pipeline")
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        import datetime
        return datetime.datetime.now().isoformat()
    
    def _redirect_downstreams(self) -> None:
        """
        将当前future transformation的所有下游连接重定向到实际的transformation
        """
        if not self.actual_transformation:
            return
            
        # 将所有下游节点的上游引用从当前节点改为实际节点
        for downstream_name, input_index in self.downstreams.items():
            # 找到下游transformation
            downstream_trans = self._find_transformation_by_name(downstream_name)
            if downstream_trans:
                # 移除对当前future的引用
                if self in downstream_trans.upstreams:
                    downstream_trans.upstreams.remove(self)
                
                # 添加对实际transformation的引用
                downstream_trans.upstreams.append(self.actual_transformation)
                
                # 更新实际transformation的下游引用
                self.actual_transformation.downstreams[downstream_name] = input_index
        
        # 清空当前future的下游引用
        self.downstreams.clear()
    
    def _find_transformation_by_name(self, name: str) -> BaseTransformation:
        """
        在pipeline中查找指定名称的transformation
        """
        for trans in self.env.pipeline:
            if trans.basename == name:
                return trans
        return None
    
    @property
    def is_spout(self) -> bool:
        """Future transformation不是spout"""
        return False
    
    def __repr__(self) -> str:
        status = "filled" if self.filled else "unfilled"
        actual = f" -> {self.actual_transformation.basename}" if self.filled else ""
        return f"FutureTransformation({self.future_name}, {status}{actual})"
