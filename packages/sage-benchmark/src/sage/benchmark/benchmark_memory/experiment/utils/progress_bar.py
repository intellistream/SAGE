"""进度条工具 - 提供类似 tqdm 的进度显示"""


class ProgressBar:
    """简单的进度条实现
    
    示例:
        progress = ProgressBar(total=100, desc="处理中")
        for i in range(100):
            progress.update(1)
        progress.close()
    """

    def __init__(self, total: int, desc: str = "进度", bar_length: int = 40):
        """初始化进度条
        
        Args:
            total: 总数
            desc: 描述文本
            bar_length: 进度条长度（字符数）
        """
        self.total = total
        self.desc = desc
        self.bar_length = bar_length
        self.current = 0

    def update(self, n: int = 1):
        """更新进度
        
        Args:
            n: 增加的数量
        """
        self.current += n
        self._print()

    def _print(self):
        """打印进度条"""
        if self.total == 0:
            return
        
        progress = self.current / self.total
        filled_length = int(self.bar_length * progress)
        bar = '█' * filled_length + '░' * (self.bar_length - filled_length)
        percent = progress * 100
        
        print(
            f"\r⏳ {self.desc}: |{bar}| {self.current}/{self.total} ({percent:.1f}%)",
            end='',
            flush=True
        )

    def close(self):
        """完成进度条，换行"""
        print()  # 换行，让进度条显示完整
