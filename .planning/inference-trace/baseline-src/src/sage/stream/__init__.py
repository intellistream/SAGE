"""Stream-first public API for SAGE."""

from .connected_streams import ConnectedStreams
from .datastream import DataStream

__all__ = ["DataStream", "ConnectedStreams"]
