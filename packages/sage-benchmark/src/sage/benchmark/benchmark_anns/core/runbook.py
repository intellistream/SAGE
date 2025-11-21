"""
Runbook loader and processor for congestion tests
"""
import yaml
import numpy as np
from typing import List, Dict, Any


class RunbookEntry:
    """Single operation entry in a runbook"""
    def __init__(self, operation, **kwargs):
        self.operation = operation
        self.params = kwargs
    
    def __getitem__(self, key):
        if key == 'operation':
            return self.operation
        return self.params.get(key)
    
    def get(self, key, default=None):
        if key == 'operation':
            return self.operation
        return self.params.get(key, default)


class Runbook:
    """
    Runbook defines a sequence of operations for congestion testing.
    Operations include: initial, startHPC, insert, delete, search, waitPending, endHPC, etc.
    """
    
    def __init__(self, entries: List[RunbookEntry], maintenance_policy=None):
        self.entries = entries
        self.maintenance_policy = maintenance_policy or {}
    
    def __iter__(self):
        return iter(self.entries)
    
    def __len__(self):
        return len(self.entries)
    
    @classmethod
    def from_yaml(cls, filepath):
        """Load runbook from YAML file"""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        
        if not data:
            raise ValueError("Empty runbook file")
        
        entries = []
        maintenance_policy = {}
        
        for item in data:
            if isinstance(item, dict):
                if 'operation' in item:
                    operation = item.pop('operation')
                    entries.append(RunbookEntry(operation, **item))
                elif 'maintenance_policy' in item:
                    maintenance_policy = item['maintenance_policy']
        
        return cls(entries, maintenance_policy)
    
    @classmethod
    def from_dict_list(cls, data: List[Dict[str, Any]]):
        """Create runbook from list of dictionaries"""
        entries = []
        maintenance_policy = {}
        
        for item in data:
            if 'operation' in item:
                operation = item['operation']
                params = {k: v for k, v in item.items() if k != 'operation'}
                entries.append(RunbookEntry(operation, **params))
            elif 'maintenance_policy' in item:
                maintenance_policy = item['maintenance_policy']
        
        return cls(entries, maintenance_policy)
    
    def get_data_range(self):
        """Extract the overall data range from runbook"""
        min_start = float('inf')
        max_end = 0
        
        for entry in self.entries:
            if entry['operation'] in ['initial', 'batch_insert', 'insert']:
                start = entry.get('start', 0)
                end = entry.get('end', 0)
                min_start = min(min_start, start)
                max_end = max(max_end, end)
        
        if min_start == float('inf'):
            return 0, 0
        return int(min_start), int(max_end)


def create_simple_runbook(nb_initial=10000, nb_insert=5000, nb_delete=1000,
                         nb_search=100, batch_size=1000, event_rate=1000):
    """
    Create a simple runbook for testing.
    
    Args:
        nb_initial: Number of vectors to initially load
        nb_insert: Number of vectors to insert during streaming
        nb_delete: Number of vectors to delete
        nb_search: Number of search operations
        batch_size: Batch size for insertions
        event_rate: Event rate (events per second)
    
    Returns:
        Runbook instance
    """
    entries = []
    
    # Initial load
    entries.append(RunbookEntry('initial', start=0, end=nb_initial))
    
    # Start HPC workers
    entries.append(RunbookEntry('startHPC'))
    
    # Batch insert
    entries.append(RunbookEntry(
        'batch_insert',
        start=nb_initial,
        end=nb_initial + nb_insert,
        batchSize=batch_size,
        eventRate=event_rate
    ))
    
    # Wait for pending operations
    entries.append(RunbookEntry('waitPending'))
    
    # Search operations
    for i in range(nb_search):
        entries.append(RunbookEntry('search', k=10))
    
    # Delete some vectors
    if nb_delete > 0:
        entries.append(RunbookEntry(
            'delete',
            start=0,
            end=min(nb_delete, nb_initial)
        ))
    
    # Final wait and cleanup
    entries.append(RunbookEntry('waitPending'))
    entries.append(RunbookEntry('endHPC'))
    
    return Runbook(entries)
