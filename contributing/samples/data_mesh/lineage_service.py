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

"""Data lineage tracking service for ADK agents."""

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
from pydantic import BaseModel, Field

from .event_bus import Event, EventHandler, EventMetadata

logger = logging.getLogger(__name__)


class LineageNodeType(Enum):
  """Types of nodes in lineage graph."""
  AGENT = "agent"
  TOOL = "tool"
  DATA_SOURCE = "data_source"
  DATA_SINK = "data_sink"
  TRANSFORM = "transform"
  MODEL = "model"
  DECISION = "decision"
  EVENT = "event"
  PILLAR = "pillar"


class LineageEdgeType(Enum):
  """Types of edges in lineage graph."""
  READS_FROM = "reads_from"
  WRITES_TO = "writes_to"
  TRIGGERS = "triggers"
  DEPENDS_ON = "depends_on"
  PRODUCES = "produces"
  CONSUMES = "consumes"
  INVOKES = "invokes"
  APPROVES = "approves"


@dataclass
class LineageNode:
  """Node in the lineage graph."""
  node_id: str
  node_type: LineageNodeType
  name: str
  pillar: Optional[str] = None
  metadata: Dict[str, Any] = field(default_factory=dict)
  created_at: datetime = field(default_factory=datetime.now)
  updated_at: datetime = field(default_factory=datetime.now)
  
  def to_dict(self) -> Dict[str, Any]:
    """Convert to dictionary."""
    return {
      "node_id": self.node_id,
      "node_type": self.node_type.value,
      "name": self.name,
      "pillar": self.pillar,
      "metadata": self.metadata,
      "created_at": self.created_at.isoformat(),
      "updated_at": self.updated_at.isoformat()
    }


@dataclass
class LineageEdge:
  """Edge in the lineage graph."""
  edge_id: str
  source_id: str
  target_id: str
  edge_type: LineageEdgeType
  trace_id: str
  metadata: Dict[str, Any] = field(default_factory=dict)
  created_at: datetime = field(default_factory=datetime.now)
  
  def to_dict(self) -> Dict[str, Any]:
    """Convert to dictionary."""
    return {
      "edge_id": self.edge_id,
      "source_id": self.source_id,
      "target_id": self.target_id,
      "edge_type": self.edge_type.value,
      "trace_id": self.trace_id,
      "metadata": self.metadata,
      "created_at": self.created_at.isoformat()
    }


class LineageQuery(BaseModel):
  """Query parameters for lineage search."""
  node_id: Optional[str] = None
  trace_id: Optional[str] = None
  pillar: Optional[str] = None
  node_type: Optional[LineageNodeType] = None
  direction: str = "both"  # upstream, downstream, both
  max_depth: int = 10
  time_range: Optional[Tuple[datetime, datetime]] = None
  include_metadata: bool = True


class LineageService:
  """Service for tracking and querying data lineage."""
  
  def __init__(self):
    self._graph = nx.DiGraph()
    self._nodes: Dict[str, LineageNode] = {}
    self._edges: Dict[str, LineageEdge] = {}
    self._trace_edges: Dict[str, List[str]] = defaultdict(list)
    self._pillar_nodes: Dict[str, Set[str]] = defaultdict(set)
    self._type_nodes: Dict[LineageNodeType, Set[str]] = defaultdict(set)
    self._event_handler = None
  
  def create_event_handler(self) -> EventHandler:
    """Create an event handler for automatic lineage tracking."""
    async def handle_event(event: Event):
      await self.track_event(event)
    
    self._event_handler = EventHandler(
      handler_func=handle_event,
      event_types=None  # Track all events
    )
    return self._event_handler
  
  async def track_event(self, event: Event):
    """Track lineage from an event."""
    metadata = event.metadata
    
    # Create nodes for source and target
    source_node_id = f"{metadata.source_pillar}:{metadata.source_agent}"
    await self.add_node(
      node_id=source_node_id,
      node_type=LineageNodeType.AGENT,
      name=metadata.source_agent,
      pillar=metadata.source_pillar
    )
    
    if metadata.target_agent:
      target_node_id = f"{metadata.target_pillar}:{metadata.target_agent}"
      await self.add_node(
        node_id=target_node_id,
        node_type=LineageNodeType.AGENT,
        name=metadata.target_agent,
        pillar=metadata.target_pillar
      )
      
      # Add edge
      await self.add_edge(
        source_id=source_node_id,
        target_id=target_node_id,
        edge_type=LineageEdgeType.TRIGGERS,
        trace_id=metadata.trace_id,
        metadata={
          "event_type": event.event_type.value,
          "event_id": metadata.event_id
        }
      )
    
    # Track event node
    event_node_id = f"event:{metadata.event_id}"
    await self.add_node(
      node_id=event_node_id,
      node_type=LineageNodeType.EVENT,
      name=event.event_type.value,
      metadata={
        "payload": event.payload,
        "priority": metadata.priority.value
      }
    )
    
    # Link agent to event
    await self.add_edge(
      source_id=source_node_id,
      target_id=event_node_id,
      edge_type=LineageEdgeType.PRODUCES,
      trace_id=metadata.trace_id
    )
  
  async def add_node(
    self,
    node_id: str,
    node_type: LineageNodeType,
    name: str,
    pillar: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
  ) -> LineageNode:
    """Add or update a node in the lineage graph."""
    if node_id in self._nodes:
      # Update existing node
      node = self._nodes[node_id]
      node.updated_at = datetime.now()
      if metadata:
        node.metadata.update(metadata)
    else:
      # Create new node
      node = LineageNode(
        node_id=node_id,
        node_type=node_type,
        name=name,
        pillar=pillar,
        metadata=metadata or {}
      )
      self._nodes[node_id] = node
      self._graph.add_node(node_id, **node.to_dict())
      
      # Index by pillar and type
      if pillar:
        self._pillar_nodes[pillar].add(node_id)
      self._type_nodes[node_type].add(node_id)
    
    return node
  
  async def add_edge(
    self,
    source_id: str,
    target_id: str,
    edge_type: LineageEdgeType,
    trace_id: str,
    metadata: Optional[Dict[str, Any]] = None
  ) -> LineageEdge:
    """Add an edge to the lineage graph."""
    edge_id = f"{source_id}->{target_id}:{trace_id}"
    
    edge = LineageEdge(
      edge_id=edge_id,
      source_id=source_id,
      target_id=target_id,
      edge_type=edge_type,
      trace_id=trace_id,
      metadata=metadata or {}
    )
    
    self._edges[edge_id] = edge
    self._trace_edges[trace_id].append(edge_id)
    
    # Add to graph
    self._graph.add_edge(
      source_id,
      target_id,
      edge_id=edge_id,
      **edge.to_dict()
    )
    
    return edge
  
  async def track_tool_invocation(
    self,
    agent_id: str,
    tool_name: str,
    trace_id: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    pillar: str
  ):
    """Track a tool invocation in lineage."""
    # Create tool node
    tool_node_id = f"tool:{tool_name}"
    await self.add_node(
      node_id=tool_node_id,
      node_type=LineageNodeType.TOOL,
      name=tool_name
    )
    
    # Agent invokes tool
    await self.add_edge(
      source_id=agent_id,
      target_id=tool_node_id,
      edge_type=LineageEdgeType.INVOKES,
      trace_id=trace_id,
      metadata={
        "inputs": inputs,
        "outputs": outputs,
        "timestamp": datetime.now().isoformat()
      }
    )
  
  async def track_data_flow(
    self,
    source_id: str,
    sink_id: str,
    trace_id: str,
    data_schema: Optional[str] = None,
    record_count: Optional[int] = None
  ):
    """Track data flow between sources and sinks."""
    await self.add_edge(
      source_id=source_id,
      target_id=sink_id,
      edge_type=LineageEdgeType.WRITES_TO,
      trace_id=trace_id,
      metadata={
        "data_schema": data_schema,
        "record_count": record_count,
        "timestamp": datetime.now().isoformat()
      }
    )
  
  async def track_decision(
    self,
    agent_id: str,
    decision_id: str,
    trace_id: str,
    decision_type: str,
    result: Any,
    factors: List[str]
  ):
    """Track a decision made by an agent."""
    # Create decision node
    decision_node_id = f"decision:{decision_id}"
    await self.add_node(
      node_id=decision_node_id,
      node_type=LineageNodeType.DECISION,
      name=decision_type,
      metadata={
        "result": result,
        "factors": factors
      }
    )
    
    # Agent makes decision
    await self.add_edge(
      source_id=agent_id,
      target_id=decision_node_id,
      edge_type=LineageEdgeType.PRODUCES,
      trace_id=trace_id
    )
  
  async def query_lineage(self, query: LineageQuery) -> Dict[str, Any]:
    """Query lineage based on parameters."""
    results = {
      "nodes": [],
      "edges": [],
      "stats": {}
    }
    
    # Find starting nodes
    start_nodes = set()
    
    if query.node_id:
      if query.node_id in self._nodes:
        start_nodes.add(query.node_id)
    elif query.trace_id:
      # Get all nodes involved in trace
      for edge_id in self._trace_edges.get(query.trace_id, []):
        edge = self._edges[edge_id]
        start_nodes.add(edge.source_id)
        start_nodes.add(edge.target_id)
    elif query.pillar:
      start_nodes.update(self._pillar_nodes.get(query.pillar, set()))
    elif query.node_type:
      start_nodes.update(self._type_nodes.get(query.node_type, set()))
    
    if not start_nodes:
      return results
    
    # Traverse graph based on direction
    visited_nodes = set()
    visited_edges = set()
    
    for node in start_nodes:
      if query.direction in ["upstream", "both"]:
        self._traverse_upstream(
          node, query.max_depth, visited_nodes, visited_edges
        )
      
      if query.direction in ["downstream", "both"]:
        self._traverse_downstream(
          node, query.max_depth, visited_nodes, visited_edges
        )
    
    # Add center nodes if only going one direction
    if query.direction != "both":
      visited_nodes.update(start_nodes)
    
    # Filter by time range if specified
    if query.time_range:
      start_time, end_time = query.time_range
      visited_nodes = {
        n for n in visited_nodes
        if self._nodes[n].created_at >= start_time
        and self._nodes[n].created_at <= end_time
      }
      visited_edges = {
        e for e in visited_edges
        if self._edges[e].created_at >= start_time
        and self._edges[e].created_at <= end_time
      }
    
    # Build results
    for node_id in visited_nodes:
      node = self._nodes[node_id]
      node_data = node.to_dict()
      if not query.include_metadata:
        node_data.pop("metadata", None)
      results["nodes"].append(node_data)
    
    for edge_id in visited_edges:
      edge = self._edges[edge_id]
      edge_data = edge.to_dict()
      if not query.include_metadata:
        edge_data.pop("metadata", None)
      results["edges"].append(edge_data)
    
    # Calculate stats
    results["stats"] = {
      "total_nodes": len(results["nodes"]),
      "total_edges": len(results["edges"]),
      "node_types": self._count_node_types(visited_nodes),
      "edge_types": self._count_edge_types(visited_edges),
      "pillars_involved": self._count_pillars(visited_nodes)
    }
    
    return results
  
  def _traverse_upstream(
    self,
    node_id: str,
    depth: int,
    visited_nodes: Set[str],
    visited_edges: Set[str]
  ):
    """Traverse upstream in the lineage graph."""
    if depth <= 0 or node_id in visited_nodes:
      return
    
    visited_nodes.add(node_id)
    
    # Get incoming edges
    for pred in self._graph.predecessors(node_id):
      edge_data = self._graph.get_edge_data(pred, node_id)
      if edge_data:
        edge_id = edge_data.get("edge_id")
        if edge_id:
          visited_edges.add(edge_id)
        self._traverse_upstream(pred, depth - 1, visited_nodes, visited_edges)
  
  def _traverse_downstream(
    self,
    node_id: str,
    depth: int,
    visited_nodes: Set[str],
    visited_edges: Set[str]
  ):
    """Traverse downstream in the lineage graph."""
    if depth <= 0 or node_id in visited_nodes:
      return
    
    visited_nodes.add(node_id)
    
    # Get outgoing edges
    for succ in self._graph.successors(node_id):
      edge_data = self._graph.get_edge_data(node_id, succ)
      if edge_data:
        edge_id = edge_data.get("edge_id")
        if edge_id:
          visited_edges.add(edge_id)
        self._traverse_downstream(succ, depth - 1, visited_nodes, visited_edges)
  
  def _count_node_types(self, node_ids: Set[str]) -> Dict[str, int]:
    """Count nodes by type."""
    counts = defaultdict(int)
    for node_id in node_ids:
      if node_id in self._nodes:
        counts[self._nodes[node_id].node_type.value] += 1
    return dict(counts)
  
  def _count_edge_types(self, edge_ids: Set[str]) -> Dict[str, int]:
    """Count edges by type."""
    counts = defaultdict(int)
    for edge_id in edge_ids:
      if edge_id in self._edges:
        counts[self._edges[edge_id].edge_type.value] += 1
    return dict(counts)
  
  def _count_pillars(self, node_ids: Set[str]) -> List[str]:
    """Get unique pillars involved."""
    pillars = set()
    for node_id in node_ids:
      if node_id in self._nodes and self._nodes[node_id].pillar:
        pillars.add(self._nodes[node_id].pillar)
    return sorted(list(pillars))
  
  async def get_trace_timeline(self, trace_id: str) -> List[Dict[str, Any]]:
    """Get timeline of events for a trace."""
    timeline = []
    
    # Get all edges for trace
    edge_ids = self._trace_edges.get(trace_id, [])
    
    for edge_id in edge_ids:
      edge = self._edges[edge_id]
      source = self._nodes.get(edge.source_id)
      target = self._nodes.get(edge.target_id)
      
      if source and target:
        timeline.append({
          "timestamp": edge.created_at.isoformat(),
          "source": {
            "id": source.node_id,
            "name": source.name,
            "type": source.node_type.value
          },
          "target": {
            "id": target.node_id,
            "name": target.name,
            "type": target.node_type.value
          },
          "action": edge.edge_type.value,
          "metadata": edge.metadata
        })
    
    # Sort by timestamp
    timeline.sort(key=lambda x: x["timestamp"])
    
    return timeline
  
  async def find_impact(
    self,
    node_id: str,
    change_type: str = "update"
  ) -> Dict[str, Any]:
    """Find potential impact of changes to a node."""
    impact = {
      "node": node_id,
      "change_type": change_type,
      "affected_nodes": [],
      "affected_pillars": set(),
      "risk_level": "low"
    }
    
    # Find all downstream nodes
    visited = set()
    self._traverse_downstream(node_id, 10, visited, set())
    
    for affected_id in visited:
      if affected_id != node_id and affected_id in self._nodes:
        node = self._nodes[affected_id]
        impact["affected_nodes"].append({
          "id": node.node_id,
          "name": node.name,
          "type": node.node_type.value,
          "pillar": node.pillar
        })
        if node.pillar:
          impact["affected_pillars"].add(node.pillar)
    
    # Calculate risk level
    affected_count = len(impact["affected_nodes"])
    pillar_count = len(impact["affected_pillars"])
    
    if affected_count > 10 or pillar_count > 3:
      impact["risk_level"] = "high"
    elif affected_count > 5 or pillar_count > 1:
      impact["risk_level"] = "medium"
    
    impact["affected_pillars"] = list(impact["affected_pillars"])
    
    return impact
  
  def export_graph(self, format: str = "json") -> Any:
    """Export lineage graph."""
    if format == "json":
      return {
        "nodes": [node.to_dict() for node in self._nodes.values()],
        "edges": [edge.to_dict() for edge in self._edges.values()]
      }
    elif format == "graphml":
      # Export as GraphML for visualization tools
      return nx.write_graphml(self._graph)
    elif format == "dot":
      # Export as DOT for Graphviz
      return nx.drawing.nx_pydot.to_pydot(self._graph)
    else:
      raise ValueError(f"Unsupported format: {format}")
  
  async def prune_old_data(self, days: int = 30):
    """Prune lineage data older than specified days."""
    cutoff = datetime.now() - timedelta(days=days)
    
    # Find nodes to remove
    nodes_to_remove = []
    for node_id, node in self._nodes.items():
      if node.updated_at < cutoff:
        nodes_to_remove.append(node_id)
    
    # Remove nodes and associated edges
    for node_id in nodes_to_remove:
      self._graph.remove_node(node_id)
      del self._nodes[node_id]
      
      # Update indexes
      for pillar, nodes in self._pillar_nodes.items():
        nodes.discard(node_id)
      for node_type, nodes in self._type_nodes.items():
        nodes.discard(node_id)
    
    # Clean up edges
    edges_to_remove = []
    for edge_id, edge in self._edges.items():
      if edge.created_at < cutoff:
        edges_to_remove.append(edge_id)
    
    for edge_id in edges_to_remove:
      edge = self._edges[edge_id]
      del self._edges[edge_id]
      self._trace_edges[edge.trace_id].remove(edge_id)
    
    logger.info(f"Pruned {len(nodes_to_remove)} nodes and {len(edges_to_remove)} edges")


class LineageVisualizer:
  """Helper for visualizing lineage graphs."""
  
  @staticmethod
  def generate_mermaid(lineage_data: Dict[str, Any]) -> str:
    """Generate Mermaid diagram from lineage data."""
    lines = ["graph TD"]
    
    # Add nodes
    for node in lineage_data["nodes"]:
      node_id = node["node_id"].replace(":", "_")
      label = f"{node['name']}\\n({node['node_type']})"
      lines.append(f"    {node_id}[{label}]")
    
    # Add edges
    for edge in lineage_data["edges"]:
      source = edge["source_id"].replace(":", "_")
      target = edge["target_id"].replace(":", "_")
      label = edge["edge_type"]
      lines.append(f"    {source} -->|{label}| {target}")
    
    return "\n".join(lines)