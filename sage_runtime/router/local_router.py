# sage_runtime/local_router.py

from typing import TYPE_CHECKING
from sage_runtime.router.base_router import BaseRouter
from sage_runtime.router.packet import Packet

if TYPE_CHECKING:
    from sage_runtime.router.connection import Connection
    from sage_runtime.runtime_context import RuntimeContext

class LocalRouter(BaseRouter):
    """
    本地任务的路由器，使用直接方法调用进行通信
    """
    
    def __init__(self, ctx: 'RuntimeContext'):
        super().__init__(ctx)