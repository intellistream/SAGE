



from dataclasses import dataclass
from typing import Union, Any
from sage_core.api.tuple import Data

@dataclass
class Message:
    type: str  # 控制消息类型，如 "WATERMARK", "CHECKPOINT", "EOS", "ACK"
    payload: Any = None  # 可选的数据体

@dataclass
class Packet:
    content_type: str
    content: Union[Data, Message]
    sequence: int = None  # 可选序号
    channel: int = 0  # 来源/目标通道号