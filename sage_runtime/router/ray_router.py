# sage_runtime/ray_router.py

from typing import TYPE_CHECKING
from ray.util.queue import Queue as RayQueue
from sage_runtime.router.base_router import BaseRouter
from sage_runtime.router.packet import Packet

if TYPE_CHECKING:
    from sage_runtime.router.connection import Connection
    from sage_runtime.runtime_context import RuntimeContext

class RayRouter(BaseRouter):
    """
    Ray Actor任务的路由器，使用Ray Queue进行跨进程通信
    """
    
    def __init__(self, ctx: 'RuntimeContext'):
        super().__init__(ctx)
    
    # 目前没有什么特异功能