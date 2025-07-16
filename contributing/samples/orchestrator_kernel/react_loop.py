# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""ReAct (Reasoning and Acting) loop implementation for agent orchestration."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union
import uuid

logger = logging.getLogger(__name__)


class ReactPhase(Enum):
    """Phases of the ReAct loop."""
    THINK = "think"
    ACT = "act"
    OBSERVE = "observe"
    FINISH = "finish"


@dataclass
class ThoughtAction:
    """Represents a thought in the ReAct loop."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    reasoning: str = ""
    selected_action: Optional[str] = None
    action_parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "reasoning": self.reasoning,
            "selected_action": self.selected_action,
            "action_parameters": self.action_parameters,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ToolCall:
    """Represents a tool invocation in the ReAct loop."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None
    state_delta: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "state_delta": self.state_delta
        }


@dataclass
class Observation:
    """Represents an observation in the ReAct loop."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_call_id: str = ""
    content: str = ""
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    requires_followup: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "tool_call_id": self.tool_call_id,
            "content": self.content,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "requires_followup": self.requires_followup
        }


@dataclass
class ReactState:
    """State of the ReAct loop."""
    loop_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_phase: ReactPhase = ReactPhase.THINK
    thoughts: List[ThoughtAction] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)
    observations: List[Observation] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    scratchpad: str = ""
    iteration_count: int = 0
    max_iterations: int = 10
    is_finished: bool = False
    finish_reason: str = ""
    
    def add_thought(self, thought: ThoughtAction):
        """Add thought to state."""
        self.thoughts.append(thought)
        self.scratchpad += f"\nThought {len(self.thoughts)}: {thought.content}\n"
        if thought.reasoning:
            self.scratchpad += f"Reasoning: {thought.reasoning}\n"
    
    def add_tool_call(self, tool_call: ToolCall):
        """Add tool call to state."""
        self.tool_calls.append(tool_call)
        self.scratchpad += f"\nAction: {tool_call.tool_name}({json.dumps(tool_call.parameters)})\n"
    
    def add_observation(self, observation: Observation):
        """Add observation to state."""
        self.observations.append(observation)
        self.scratchpad += f"\nObservation: {observation.content}\n"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "loop_id": self.loop_id,
            "current_phase": self.current_phase.value,
            "thoughts": [t.to_dict() for t in self.thoughts],
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "observations": [o.to_dict() for o in self.observations],
            "context": self.context,
            "scratchpad": self.scratchpad,
            "iteration_count": self.iteration_count,
            "max_iterations": self.max_iterations,
            "is_finished": self.is_finished,
            "finish_reason": self.finish_reason
        }


class PolicyHook(ABC):
    """Abstract base class for policy hooks."""
    
    @abstractmethod
    async def check(
        self,
        tool_call: ToolCall,
        state: ReactState,
        context: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Check if tool call is allowed.
        
        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        pass


class AMLPolicyHook(PolicyHook):
    """Autonomy Maturity Level (AML) policy hook."""
    
    def __init__(self, aml_level: int, caps: Dict[str, Any]):
        self.aml_level = aml_level
        self.caps = caps
    
    async def check(
        self,
        tool_call: ToolCall,
        state: ReactState,
        context: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Check AML constraints."""
        # AML 0: No actions allowed
        if self.aml_level == 0:
            return False, "AML 0: Read-only mode, no actions allowed"
        
        # AML 1: Only suggest actions
        if self.aml_level == 1:
            # Check if this is a suggestion-only tool
            if not tool_call.tool_name.startswith("suggest_"):
                return False, f"AML 1: Only suggestion tools allowed, not {tool_call.tool_name}"
        
        # AML 2-5: Check specific caps
        if tool_call.tool_name in self.caps:
            cap_config = self.caps[tool_call.tool_name]
            
            # Check monetary limits
            if "max_amount" in cap_config:
                amount = tool_call.parameters.get("amount", 0)
                if amount > cap_config["max_amount"]:
                    return False, f"Exceeds cap: ${amount} > ${cap_config['max_amount']}"
            
            # Check rate limits
            if "max_per_hour" in cap_config:
                # Count recent calls
                recent_calls = sum(
                    1 for tc in state.tool_calls
                    if tc.tool_name == tool_call.tool_name
                    and (datetime.now() - tc.timestamp).seconds < 3600
                )
                if recent_calls >= cap_config["max_per_hour"]:
                    return False, f"Rate limit exceeded: {recent_calls} calls in last hour"
        
        return True, None


class OPAPolicyHook(PolicyHook):
    """Open Policy Agent (OPA) integration hook."""
    
    def __init__(self, opa_endpoint: str = "http://localhost:8181"):
        self.opa_endpoint = opa_endpoint
    
    async def check(
        self,
        tool_call: ToolCall,
        state: ReactState,
        context: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Check OPA policy."""
        # Mock OPA check for demo
        # In production, this would make an actual HTTP call to OPA
        
        # Example policy: No more than 3 external API calls per loop
        external_api_count = sum(
            1 for tc in state.tool_calls
            if tc.tool_name.endswith("_api")
        )
        
        if external_api_count >= 3 and tool_call.tool_name.endswith("_api"):
            return False, "OPA Policy: Maximum external API calls (3) reached"
        
        return True, None


@dataclass
class LoopConfig:
    """Configuration for ReAct loop."""
    max_iterations: int = 10
    max_thinking_time: float = 30.0  # seconds
    require_explicit_finish: bool = True
    enable_parallel_tools: bool = False
    policy_hooks: List[PolicyHook] = field(default_factory=list)
    available_tools: Dict[str, Callable] = field(default_factory=dict)


class ReactLoop:
    """ReAct loop implementation."""
    
    def __init__(self, config: LoopConfig):
        self.config = config
        self._llm_handler: Optional[Callable] = None
        self._tool_registry: Dict[str, Callable] = config.available_tools.copy()
    
    def set_llm_handler(self, handler: Callable):
        """Set LLM handler for thinking phase."""
        self._llm_handler = handler
    
    def register_tool(self, name: str, handler: Callable):
        """Register tool handler."""
        self._tool_registry[name] = handler
    
    async def run(
        self,
        initial_prompt: str,
        context: Dict[str, Any]
    ) -> ReactState:
        """Run the ReAct loop."""
        state = ReactState(
            context=context.copy(),
            max_iterations=self.config.max_iterations,
            scratchpad=f"Task: {initial_prompt}\n"
        )
        
        logger.info(f"Starting ReAct loop: {state.loop_id}")
        
        while not state.is_finished and state.iteration_count < state.max_iterations:
            state.iteration_count += 1
            logger.info(f"ReAct iteration {state.iteration_count}")
            
            try:
                # Think phase
                state.current_phase = ReactPhase.THINK
                thought = await self._think(state)
                state.add_thought(thought)
                
                # Check if finished
                if thought.selected_action == "FINISH":
                    state.is_finished = True
                    state.finish_reason = thought.reasoning or "Task completed"
                    state.current_phase = ReactPhase.FINISH
                    break
                
                # Act phase
                if thought.selected_action:
                    state.current_phase = ReactPhase.ACT
                    tool_call = await self._act(thought, state)
                    if tool_call:
                        state.add_tool_call(tool_call)
                        
                        # Observe phase
                        state.current_phase = ReactPhase.OBSERVE
                        observation = await self._observe(tool_call, state)
                        state.add_observation(observation)
            
            except Exception as e:
                logger.error(f"Error in ReAct loop: {e}")
                state.is_finished = True
                state.finish_reason = f"Error: {str(e)}"
                break
        
        # Check if we hit max iterations
        if state.iteration_count >= state.max_iterations:
            state.is_finished = True
            state.finish_reason = "Maximum iterations reached"
        
        logger.info(f"ReAct loop finished: {state.finish_reason}")
        return state
    
    async def _think(self, state: ReactState) -> ThoughtAction:
        """Think phase - LLM reasoning."""
        if not self._llm_handler:
            raise ValueError("No LLM handler configured")
        
        # Prepare prompt with scratchpad
        prompt = f"""
You are an AI agent using the ReAct (Reasoning and Acting) framework.
Here is your current scratchpad showing your thoughts and actions so far:

{state.scratchpad}

Available tools: {list(self._tool_registry.keys())}

Based on the above, what should you do next? 
Think step by step about:
1. What information do you have so far?
2. What do you still need to accomplish?
3. What action should you take next?

If the task is complete, select action "FINISH".

Respond with your thought process and selected action.
"""
        
        # Call LLM
        llm_response = await self._llm_handler(prompt, state.context)
        
        # Parse response (simplified for demo)
        thought = ThoughtAction(
            content=llm_response.get("thought", ""),
            reasoning=llm_response.get("reasoning", ""),
            selected_action=llm_response.get("action", ""),
            action_parameters=llm_response.get("parameters", {}),
            confidence=llm_response.get("confidence", 0.8)
        )
        
        return thought
    
    async def _act(
        self,
        thought: ThoughtAction,
        state: ReactState
    ) -> Optional[ToolCall]:
        """Act phase - execute selected tool."""
        if not thought.selected_action:
            return None
        
        tool_call = ToolCall(
            tool_name=thought.selected_action,
            parameters=thought.action_parameters
        )
        
        # Check policy hooks
        for hook in self.config.policy_hooks:
            allowed, reason = await hook.check(tool_call, state, state.context)
            if not allowed:
                logger.warning(f"Tool call denied by policy: {reason}")
                tool_call.status = "denied"
                tool_call.error = reason
                return tool_call
        
        # Execute tool
        if thought.selected_action in self._tool_registry:
            try:
                tool_handler = self._tool_registry[thought.selected_action]
                tool_call.status = "running"
                
                # Execute tool
                result = await tool_handler(
                    **thought.action_parameters,
                    context=state.context
                )
                
                tool_call.status = "completed"
                tool_call.result = result
                
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                tool_call.status = "failed"
                tool_call.error = str(e)
        else:
            tool_call.status = "failed"
            tool_call.error = f"Unknown tool: {thought.selected_action}"
        
        return tool_call
    
    async def _observe(
        self,
        tool_call: ToolCall,
        state: ReactState
    ) -> Observation:
        """Observe phase - process tool results."""
        observation = Observation(
            tool_call_id=tool_call.id
        )
        
        if tool_call.status == "completed":
            # Process successful result
            observation.content = f"Tool {tool_call.tool_name} completed successfully"
            observation.data = tool_call.result
            
            # Determine if followup is needed
            if isinstance(tool_call.result, dict):
                observation.requires_followup = tool_call.result.get("requires_followup", False)
        
        elif tool_call.status == "denied":
            observation.content = f"Tool call denied: {tool_call.error}"
            observation.requires_followup = True
        
        else:
            observation.content = f"Tool call failed: {tool_call.error}"
            observation.requires_followup = True
        
        return observation
    
    async def get_execution_trace(self, state: ReactState) -> Dict[str, Any]:
        """Get detailed execution trace for analysis."""
        return {
            "loop_id": state.loop_id,
            "total_iterations": state.iteration_count,
            "total_thoughts": len(state.thoughts),
            "total_actions": len(state.tool_calls),
            "successful_actions": sum(1 for tc in state.tool_calls if tc.status == "completed"),
            "failed_actions": sum(1 for tc in state.tool_calls if tc.status == "failed"),
            "denied_actions": sum(1 for tc in state.tool_calls if tc.status == "denied"),
            "finish_reason": state.finish_reason,
            "timeline": self._build_timeline(state)
        }
    
    def _build_timeline(self, state: ReactState) -> List[Dict[str, Any]]:
        """Build execution timeline."""
        events = []
        
        # Add thoughts
        for thought in state.thoughts:
            events.append({
                "type": "thought",
                "timestamp": thought.timestamp.isoformat(),
                "content": thought.content,
                "action": thought.selected_action
            })
        
        # Add tool calls
        for tool_call in state.tool_calls:
            events.append({
                "type": "tool_call",
                "timestamp": tool_call.timestamp.isoformat(),
                "tool": tool_call.tool_name,
                "status": tool_call.status
            })
        
        # Add observations
        for observation in state.observations:
            events.append({
                "type": "observation",
                "timestamp": observation.timestamp.isoformat(),
                "content": observation.content
            })
        
        # Sort by timestamp
        events.sort(key=lambda x: x["timestamp"])
        
        return events