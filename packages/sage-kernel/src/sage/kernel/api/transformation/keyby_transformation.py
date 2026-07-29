from __future__ import annotations

from typing import TYPE_CHECKING

from sage.kernel.api.operator.keyby_operator import KeyByOperator
from sage.kernel.api.transformation.base_transformation import BaseTransformation
from sage.kernel.runtime.factory.operator_factory import OperatorFactory

if TYPE_CHECKING:
    from sage.common.core.functions import BaseFunction
    from sage.kernel.api.base_environment import BaseEnvironment


class KeyByTransformation(BaseTransformation):
    """
    KeyBy变换，应用基于键的分区策略
    """

    def __init__(
        self,
        env: BaseEnvironment,
        key_selector_function: type[BaseFunction],
        strategy: str = "hash",
        name: str | None = None,
        parallelism: int = 1,
        *args,
        **kwargs,
    ):
        # 设置operator类
        self.operator_class = KeyByOperator
        self.partition_strategy = strategy

        # 调用父类构造函数
        super().__init__(
            env=env,
            function=key_selector_function,
            name=name,
            parallelism=parallelism,
            *args,
            **kwargs,
        )

    @property
    def operator_factory(self):
        if self._operator_factory is None:
            self._operator_factory = OperatorFactory(
                operator_class=self.operator_class,
                function_factory=self.function_factory,
                basename=self.basename,
                env_name=self.env_name,
                remote=self.remote,
                partition_strategy=self.partition_strategy,  # KeyBy特有参数
            )
        return self._operator_factory
