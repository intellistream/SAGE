from enum import Enum

class PlatformType(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"
    HYBRID = "hybrid"