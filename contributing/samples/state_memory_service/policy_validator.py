"""Policy validation for state deltas."""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import copy

from .conflict_resolver import ConflictResolver

logger = logging.getLogger(__name__)


@dataclass
class PolicyRule:
    """Represents a validation rule for state changes."""
    name: str
    field: str
    condition: str  # e.g., ">= 0", "< 1000", "in ['PENDING', 'COMPLETED']"
    error_message: str
    
    
@dataclass
class ValidationResult:
    """Result of policy validation."""
    allowed: bool
    violations: List[str] = None
    warnings: List[str] = None
    

class StatePolicyValidator:
    """Validates state deltas against policy rules."""
    
    def __init__(self):
        self.conflict_resolver = ConflictResolver()
        self.rules: Dict[str, List[PolicyRule]] = {}
        self._load_default_rules()
        
    def _load_default_rules(self):
        """Load default validation rules."""
        # Inventory rules
        self.add_rule("resource_supply", PolicyRule(
            name="inventory_non_negative",
            field="inventory.*",
            condition=">= 0",
            error_message="Inventory cannot be negative"
        ))
        
        # Budget rules  
        self.add_rule("*", PolicyRule(
            name="budget_non_negative",
            field="budget_remaining",
            condition=">= 0",
            error_message="Budget cannot be negative"
        ))
        
        # Task status rules
        self.add_rule("*", PolicyRule(
            name="valid_task_status",
            field="task_status.*",
            condition="in ['PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED']",
            error_message="Invalid task status"
        ))
        
    def add_rule(self, pillar: str, rule: PolicyRule):
        """Add a validation rule for a pillar."""
        if pillar not in self.rules:
            self.rules[pillar] = []
        self.rules[pillar].append(rule)
        
    def validate_delta(self, current_state: Dict[str, Any], delta: Dict[str, Any],
                      context: Dict[str, Any]) -> ValidationResult:
        """
        Validate a state delta against policy rules.
        
        Args:
            current_state: Current state
            delta: Proposed state changes
            context: Execution context with pillar, aml_level, etc.
            
        Returns:
            ValidationResult with allowed/denied and violations
        """
        # Apply delta to a copy of current state
        new_state = self.conflict_resolver.merge_delta(
            copy.deepcopy(current_state), 
            delta
        )
        
        # Get applicable rules
        pillar = context.get("pillar", "*")
        applicable_rules = self.rules.get(pillar, []) + self.rules.get("*", [])
        
        violations = []
        warnings = []
        
        for rule in applicable_rules:
            violation = self._check_rule(rule, new_state, context)
            if violation:
                violations.append(violation)
                
        # AML-specific checks
        aml_violations = self._check_aml_constraints(delta, context)
        violations.extend(aml_violations)
        
        return ValidationResult(
            allowed=len(violations) == 0,
            violations=violations if violations else None,
            warnings=warnings if warnings else None
        )
        
    def _check_rule(self, rule: PolicyRule, state: Dict[str, Any], 
                   context: Dict[str, Any]) -> Optional[str]:
        """Check a single rule against state."""
        # Handle wildcard fields
        if "*" in rule.field:
            base_field = rule.field.split(".*")[0]
            if base_field in state and isinstance(state[base_field], dict):
                for key, value in state[base_field].items():
                    violation = self._evaluate_condition(
                        value, rule.condition, f"{base_field}.{key}"
                    )
                    if violation:
                        return f"{rule.error_message}: {base_field}.{key} = {value}"
        else:
            # Direct field check
            value = self._get_nested_value(state, rule.field)
            if value is not None:
                violation = self._evaluate_condition(value, rule.condition, rule.field)
                if violation:
                    return f"{rule.error_message}: {rule.field} = {value}"
                    
        return None
        
    def _evaluate_condition(self, value: Any, condition: str, field: str) -> bool:
        """Evaluate a condition against a value. Returns True if violated."""
        try:
            if condition.startswith(">="):
                threshold = float(condition[2:].strip())
                return not (isinstance(value, (int, float)) and value >= threshold)
                
            elif condition.startswith("<="):
                threshold = float(condition[2:].strip())
                return not (isinstance(value, (int, float)) and value <= threshold)
                
            elif condition.startswith(">"):
                threshold = float(condition[1:].strip())
                return not (isinstance(value, (int, float)) and value > threshold)
                
            elif condition.startswith("<"):
                threshold = float(condition[1:].strip())
                return not (isinstance(value, (int, float)) and value < threshold)
                
            elif condition.startswith("in "):
                allowed_values = eval(condition[3:])  # Safe in controlled environment
                return value not in allowed_values
                
        except Exception as e:
            logger.warning(f"Failed to evaluate condition '{condition}' for {field}: {e}")
            return False
            
        return False
        
    def _get_nested_value(self, obj: Dict[str, Any], path: str) -> Any:
        """Get value from nested dict using dot notation."""
        parts = path.split(".")
        current = obj
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
                
        return current
        
    def _check_aml_constraints(self, delta: Dict[str, Any], 
                              context: Dict[str, Any]) -> List[str]:
        """Check AML-specific constraints."""
        violations = []
        aml_level = context.get("aml_level", 0)
        pillar = context.get("pillar", "")
        
        # Example AML constraints
        if aml_level <= 3:
            # Check for high-value operations
            if "budget_remaining" in delta:
                if isinstance(delta["budget_remaining"], dict) and "$inc" in delta["budget_remaining"]:
                    amount = abs(delta["budget_remaining"]["$inc"])
                    if amount > 1000:
                        violations.append(f"AML {aml_level} cannot approve transactions > $1000")
                        
        if aml_level <= 1:
            # Very restricted - no automated actions
            if any(key in delta for key in ["inventory", "budget_remaining"]):
                violations.append(f"AML {aml_level} cannot modify state automatically")
                
        return violations