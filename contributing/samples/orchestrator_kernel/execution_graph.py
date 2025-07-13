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

"""Execution graph management for agent orchestration."""

import asyncio
import json
import logging
import yaml
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union, Callable
import uuid
import networkx as nx
from collections import deque
import pickle

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Types of nodes in the execution graph."""
    LLM_CALL = "llm_call"
    TOOL_INVOCATION = "tool_invocation"
    CONDITIONAL_BRANCH = "conditional_branch"
    PARALLEL_BRANCH = "parallel_branch"
    LOOP = "loop"
    CHECKPOINT = "checkpoint"
    FINISH = "finish"


class NodeStatus(Enum):
    """Execution status of a graph node."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class GraphNode:
    """Node in the execution graph."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    node_type: NodeType = NodeType.LLM_CALL
    config: Dict[str, Any] = field(default_factory=dict)
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    status: NodeStatus = NodeStatus.PENDING
    dependencies: Set[str] = field(default_factory=set)
    retry_count: int = 0
    max_retries: int = 3
    checkpoint_enabled: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type.value,
            "config": self.config,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "status": self.status.value,
            "dependencies": list(self.dependencies),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "checkpoint_enabled": self.checkpoint_enabled,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphNode":
        """Create node from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            node_type=NodeType(data.get("node_type", "llm_call")),
            config=data.get("config", {}),
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            status=NodeStatus(data.get("status", "pending")),
            dependencies=set(data.get("dependencies", [])),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            checkpoint_enabled=data.get("checkpoint_enabled", False),
            metadata=data.get("metadata", {})
        )


@dataclass
class ExecutionGraph:
    """Directed graph representing agent execution flow."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    version: str = "1.0.0"
    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    edges: List[tuple[str, str]] = field(default_factory=list)
    entry_node: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_node(self, node: GraphNode):
        """Add node to graph."""
        self.nodes[node.id] = node
        if not self.entry_node:
            self.entry_node = node.id
    
    def add_edge(self, from_node: str, to_node: str):
        """Add edge between nodes."""
        if from_node in self.nodes and to_node in self.nodes:
            self.edges.append((from_node, to_node))
            self.nodes[to_node].dependencies.add(from_node)
        else:
            raise ValueError(f"Invalid edge: {from_node} -> {to_node}")
    
    def get_networkx_graph(self) -> nx.DiGraph:
        """Convert to NetworkX graph for analysis."""
        G = nx.DiGraph()
        for node_id, node in self.nodes.items():
            G.add_node(node_id, **node.to_dict())
        G.add_edges_from(self.edges)
        return G
    
    def validate(self) -> bool:
        """Validate graph structure."""
        G = self.get_networkx_graph()
        
        # Check for cycles in non-loop nodes
        if not nx.is_directed_acyclic_graph(G):
            cycles = list(nx.simple_cycles(G))
            for cycle in cycles:
                # Allow cycles only if they contain loop nodes
                loop_found = any(
                    self.nodes[node_id].node_type == NodeType.LOOP 
                    for node_id in cycle
                )
                if not loop_found:
                    logger.error(f"Invalid cycle detected: {cycle}")
                    return False
        
        # Check all nodes are reachable from entry
        if self.entry_node and self.nodes:
            reachable = nx.descendants(G, self.entry_node)
            reachable.add(self.entry_node)
            if len(reachable) != len(self.nodes):
                unreachable = set(self.nodes.keys()) - reachable
                logger.error(f"Unreachable nodes: {unreachable}")
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": self.edges,
            "entry_node": self.entry_node,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionGraph":
        """Create graph from dictionary."""
        graph = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            edges=data.get("edges", []),
            entry_node=data.get("entry_node"),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
        )
        
        # Add nodes
        for node_id, node_data in data.get("nodes", {}).items():
            node = GraphNode.from_dict(node_data)
            graph.nodes[node_id] = node
        
        return graph


class GraphCompiler:
    """Compiles YAML/Python definitions into execution graphs."""
    
    def compile_yaml(self, yaml_content: str) -> ExecutionGraph:
        """Compile YAML definition to execution graph."""
        config = yaml.safe_load(yaml_content)
        return self._compile_config(config)
    
    def compile_python(self, graph_def: Dict[str, Any]) -> ExecutionGraph:
        """Compile Python dictionary definition to execution graph."""
        return self._compile_config(graph_def)
    
    def _compile_config(self, config: Dict[str, Any]) -> ExecutionGraph:
        """Compile configuration to execution graph."""
        graph = ExecutionGraph(
            name=config.get("name", "unnamed_graph"),
            version=config.get("version", "1.0.0"),
            metadata=config.get("metadata", {})
        )
        
        # Compile nodes
        for node_config in config.get("nodes", []):
            node = self._compile_node(node_config)
            graph.add_node(node)
        
        # Compile edges
        for edge in config.get("edges", []):
            graph.add_edge(edge["from"], edge["to"])
        
        # Set entry node
        if "entry_node" in config:
            graph.entry_node = config["entry_node"]
        
        # Validate graph
        if not graph.validate():
            raise ValueError("Invalid graph structure")
        
        return graph
    
    def _compile_node(self, node_config: Dict[str, Any]) -> GraphNode:
        """Compile node configuration."""
        node_type_str = node_config.get("type", "llm_call")
        node_type = NodeType(node_type_str)
        
        return GraphNode(
            id=node_config.get("id", str(uuid.uuid4())),
            name=node_config.get("name", ""),
            node_type=node_type,
            config=node_config.get("config", {}),
            inputs=node_config.get("inputs", {}),
            checkpoint_enabled=node_config.get("checkpoint", False),
            max_retries=node_config.get("max_retries", 3),
            metadata=node_config.get("metadata", {})
        )


@dataclass
class GraphCheckpoint:
    """Checkpoint for graph execution state."""
    graph_id: str
    node_id: str
    state: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "graph_id": self.graph_id,
            "node_id": self.node_id,
            "state": self.state,
            "timestamp": self.timestamp.isoformat()
        }


class GraphScheduler:
    """Schedules and executes graph nodes."""
    
    def __init__(self):
        self._checkpoints: Dict[str, GraphCheckpoint] = {}
        self._execution_tasks: Dict[str, asyncio.Task] = {}
        self._node_executors: Dict[NodeType, Callable] = {}
    
    def register_executor(self, node_type: NodeType, executor: Callable):
        """Register executor for node type."""
        self._node_executors[node_type] = executor
    
    async def execute_graph(
        self,
        graph: ExecutionGraph,
        context: Dict[str, Any],
        resume_from_checkpoint: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute graph with scheduling and parallelism."""
        execution_id = str(uuid.uuid4())
        logger.info(f"Starting graph execution: {graph.name} (ID: {execution_id})")
        
        # Initialize execution state
        state = {
            "graph_id": graph.id,
            "execution_id": execution_id,
            "context": context.copy(),
            "node_outputs": {},
            "status": "running",
            "start_time": datetime.now()
        }
        
        # Resume from checkpoint if provided
        start_node = graph.entry_node
        if resume_from_checkpoint:
            checkpoint = self._checkpoints.get(resume_from_checkpoint)
            if checkpoint:
                state.update(checkpoint.state)
                start_node = checkpoint.node_id
                logger.info(f"Resuming from checkpoint at node: {start_node}")
        
        try:
            # Execute graph
            await self._execute_from_node(graph, start_node, state)
            
            state["status"] = "completed"
            state["end_time"] = datetime.now()
            logger.info(f"Graph execution completed: {execution_id}")
            
        except Exception as e:
            state["status"] = "failed"
            state["error"] = str(e)
            state["end_time"] = datetime.now()
            logger.error(f"Graph execution failed: {e}")
            raise
        
        return state
    
    async def _execute_from_node(
        self,
        graph: ExecutionGraph,
        start_node: str,
        state: Dict[str, Any]
    ):
        """Execute graph starting from given node."""
        # Build execution queue
        queue = deque([start_node])
        executing = set()
        completed = set()
        
        while queue or executing:
            # Find nodes ready to execute
            ready_nodes = []
            temp_queue = deque()
            
            while queue:
                node_id = queue.popleft()
                node = graph.nodes[node_id]
                
                # Check if dependencies are satisfied
                if node.dependencies.issubset(completed):
                    ready_nodes.append(node_id)
                else:
                    temp_queue.append(node_id)
            
            queue = temp_queue
            
            # Execute ready nodes in parallel
            if ready_nodes:
                tasks = []
                for node_id in ready_nodes:
                    if node_id not in executing:
                        executing.add(node_id)
                        task = asyncio.create_task(
                            self._execute_node(graph.nodes[node_id], state)
                        )
                        self._execution_tasks[node_id] = task
                        tasks.append((node_id, task))
                
                # Wait for any task to complete
                if tasks:
                    done, pending = await asyncio.wait(
                        [t[1] for t in tasks],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Process completed tasks
                    for node_id, task in tasks:
                        if task in done:
                            executing.remove(node_id)
                            completed.add(node_id)
                            
                            # Add successor nodes to queue
                            successors = [
                                to_node for from_node, to_node in graph.edges
                                if from_node == node_id
                            ]
                            queue.extend(successors)
                            
                            # Create checkpoint if enabled
                            node = graph.nodes[node_id]
                            if node.checkpoint_enabled:
                                await self._create_checkpoint(
                                    graph.id, node_id, state
                                )
            
            # Prevent busy waiting
            if not ready_nodes and executing:
                await asyncio.sleep(0.1)
    
    async def _execute_node(
        self,
        node: GraphNode,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute individual node."""
        logger.info(f"Executing node: {node.name} ({node.node_type.value})")
        
        # Update node status
        node.status = NodeStatus.RUNNING
        
        try:
            # Get executor for node type
            executor = self._node_executors.get(node.node_type)
            if not executor:
                raise ValueError(f"No executor for node type: {node.node_type}")
            
            # Prepare node inputs from state
            node_inputs = {}
            for key, value in node.inputs.items():
                if isinstance(value, str) and value.startswith("$"):
                    # Reference to another node's output
                    ref_node = value[1:]  # Remove $
                    if ref_node in state["node_outputs"]:
                        node_inputs[key] = state["node_outputs"][ref_node]
                    else:
                        node_inputs[key] = state["context"].get(ref_node)
                else:
                    node_inputs[key] = value
            
            # Execute node
            result = await executor(
                node=node,
                inputs=node_inputs,
                context=state["context"]
            )
            
            # Store outputs
            node.outputs = result
            state["node_outputs"][node.id] = result
            node.status = NodeStatus.COMPLETED
            
            logger.info(f"Node completed: {node.name}")
            return result
            
        except Exception as e:
            node.status = NodeStatus.FAILED
            node.retry_count += 1
            
            if node.retry_count < node.max_retries:
                logger.warning(f"Node failed, retrying: {node.name} ({node.retry_count}/{node.max_retries})")
                node.status = NodeStatus.RETRYING
                # Retry with exponential backoff
                await asyncio.sleep(2 ** node.retry_count)
                return await self._execute_node(node, state)
            else:
                logger.error(f"Node failed after {node.max_retries} retries: {node.name}")
                raise
    
    async def _create_checkpoint(
        self,
        graph_id: str,
        node_id: str,
        state: Dict[str, Any]
    ) -> str:
        """Create execution checkpoint."""
        checkpoint_id = f"{graph_id}_{node_id}_{datetime.now().timestamp()}"
        
        checkpoint = GraphCheckpoint(
            graph_id=graph_id,
            node_id=node_id,
            state=state.copy()
        )
        
        self._checkpoints[checkpoint_id] = checkpoint
        logger.info(f"Created checkpoint: {checkpoint_id}")
        
        return checkpoint_id


@dataclass
class GraphVersion:
    """Version information for execution graphs."""
    version: str
    graph: ExecutionGraph
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    change_description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "graph": self.graph.to_dict(),
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "change_description": self.change_description
        }


class GraphRegistry:
    """Registry for managing graph versions and rollback."""
    
    def __init__(self):
        self._graphs: Dict[str, List[GraphVersion]] = {}
        self._active_versions: Dict[str, str] = {}
    
    def register_graph(
        self,
        graph: ExecutionGraph,
        created_by: str = "system",
        change_description: str = ""
    ) -> str:
        """Register new graph version."""
        graph_name = graph.name
        
        # Initialize version list if needed
        if graph_name not in self._graphs:
            self._graphs[graph_name] = []
        
        # Create version
        version_num = len(self._graphs[graph_name]) + 1
        version = f"v{version_num}.0.0"
        
        graph_version = GraphVersion(
            version=version,
            graph=graph,
            created_by=created_by,
            change_description=change_description
        )
        
        self._graphs[graph_name].append(graph_version)
        self._active_versions[graph_name] = version
        
        logger.info(f"Registered graph: {graph_name} version {version}")
        return version
    
    def get_graph(self, name: str, version: Optional[str] = None) -> Optional[ExecutionGraph]:
        """Get graph by name and version."""
        if name not in self._graphs:
            return None
        
        # Use active version if not specified
        if not version:
            version = self._active_versions.get(name)
        
        # Find version
        for graph_version in self._graphs[name]:
            if graph_version.version == version:
                return graph_version.graph
        
        return None
    
    def rollback_graph(self, name: str, version: str) -> bool:
        """Rollback to specific graph version."""
        if name not in self._graphs:
            return False
        
        # Check version exists
        version_exists = any(
            gv.version == version for gv in self._graphs[name]
        )
        
        if version_exists:
            self._active_versions[name] = version
            logger.info(f"Rolled back graph {name} to version {version}")
            return True
        
        return False
    
    def list_versions(self, name: str) -> List[GraphVersion]:
        """List all versions of a graph."""
        return self._graphs.get(name, [])
    
    def export_graph(self, name: str, version: Optional[str] = None) -> str:
        """Export graph as JSON."""
        graph = self.get_graph(name, version)
        if graph:
            return json.dumps(graph.to_dict(), indent=2)
        return "{}"
    
    def import_graph(
        self,
        json_content: str,
        created_by: str = "system",
        change_description: str = "Imported"
    ) -> Optional[str]:
        """Import graph from JSON."""
        try:
            data = json.loads(json_content)
            graph = ExecutionGraph.from_dict(data)
            return self.register_graph(graph, created_by, change_description)
        except Exception as e:
            logger.error(f"Failed to import graph: {e}")
            return None