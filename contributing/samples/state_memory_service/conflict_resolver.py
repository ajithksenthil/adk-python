"""Conflict resolution for state deltas using CRDT-like operations."""

from typing import Dict, Any
import copy
import logging

logger = logging.getLogger(__name__)


class ConflictResolver:
    """Handles conflict resolution for concurrent state updates."""
    
    def merge_delta(self, current_state: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge a delta into the current state using CRDT-like semantics.
        
        Supported operations:
        - Direct assignment: {"field": value}
        - Increment: {"field": {"$inc": 5}}
        - Append to list: {"field": {"$push": item}}
        - Set operations: {"field": {"$addToSet": item}}
        - Delete: {"field": {"$unset": True}}
        """
        new_state = copy.deepcopy(current_state)
        
        for key, value in delta.items():
            if isinstance(value, dict) and len(value) == 1:
                # Check for special operations
                op, op_value = next(iter(value.items()))
                
                if op == "$inc":
                    # Increment operation
                    current_val = new_state.get(key, 0)
                    if isinstance(current_val, (int, float)):
                        new_state[key] = current_val + op_value
                    else:
                        logger.warning(f"Cannot increment non-numeric field {key}")
                        
                elif op == "$push":
                    # Append to list
                    if key not in new_state:
                        new_state[key] = []
                    if isinstance(new_state[key], list):
                        new_state[key].append(op_value)
                    else:
                        logger.warning(f"Cannot push to non-list field {key}")
                        
                elif op == "$addToSet":
                    # Add to set (list with unique values)
                    if key not in new_state:
                        new_state[key] = []
                    if isinstance(new_state[key], list):
                        if op_value not in new_state[key]:
                            new_state[key].append(op_value)
                    else:
                        logger.warning(f"Cannot addToSet to non-list field {key}")
                        
                elif op == "$unset":
                    # Delete field
                    if key in new_state:
                        del new_state[key]
                        
                else:
                    # Unknown operation, treat as direct assignment
                    new_state[key] = value
            else:
                # Direct assignment
                if isinstance(value, dict) and isinstance(new_state.get(key), dict):
                    # Recursive merge for nested objects
                    new_state[key] = self.merge_delta(new_state.get(key, {}), value)
                else:
                    new_state[key] = value
                    
        return new_state
    
    def detect_conflicts(self, state1: Dict[str, Any], state2: Dict[str, Any]) -> Dict[str, Any]:
        """Detect conflicting changes between two states."""
        conflicts = {}
        
        all_keys = set(state1.keys()) | set(state2.keys())
        
        for key in all_keys:
            val1 = state1.get(key)
            val2 = state2.get(key)
            
            if val1 != val2:
                conflicts[key] = {
                    "state1": val1,
                    "state2": val2
                }
                
        return conflicts