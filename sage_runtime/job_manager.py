import threading
from typing import Dict, Any
from sage_runtime.mixed_dag import MixedDAG

class JobManager:
    def __init__(self):
        self.handle_to_dag:Dict[str, MixedDAG] = {}
        