


class StopSignal:
    """
    停止信号类，用于标识任务停止
    """
    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return f"<StopSignal {self.name}>"
