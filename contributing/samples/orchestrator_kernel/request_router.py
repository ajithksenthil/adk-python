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

"""Request routing and load balancing for agent orchestration."""

import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
import uuid
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class RequestPriority(Enum):
    """Priority levels for request routing."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class WorkerStatus(Enum):
    """Status of worker nodes."""
    IDLE = "idle"
    BUSY = "busy"
    DRAINING = "draining"
    OFFLINE = "offline"


@dataclass
class Request:
    """Incoming request to be routed."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    pillar: str = ""  # Business pillar (e.g., "customer_success", "growth_engine")
    agent_type: str = ""  # Agent type (e.g., "planner", "worker", "critic")
    aml_level: int = 0  # Autonomy Maturity Level
    priority: RequestPriority = RequestPriority.NORMAL
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    lineage_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "pillar": self.pillar,
            "agent_type": self.agent_type,
            "aml_level": self.aml_level,
            "priority": self.priority.value,
            "payload": self.payload,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "lineage_id": self.lineage_id
        }


@dataclass
class WorkerNode:
    """Worker node in the agent pool."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    host: str = ""
    port: int = 0
    pillar: str = ""  # Business pillar this worker serves
    agent_types: Set[str] = field(default_factory=set)  # Agent types supported
    status: WorkerStatus = WorkerStatus.IDLE
    capacity: int = 10  # Max concurrent requests
    current_load: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    latency_ms: float = 0.0  # Average response latency
    error_rate: float = 0.0
    last_heartbeat: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def available_capacity(self) -> int:
        """Get available capacity."""
        return max(0, self.capacity - self.current_load)
    
    @property
    def health_score(self) -> float:
        """Calculate health score (0-1)."""
        # Combine multiple metrics
        cpu_score = 1.0 - min(self.cpu_usage / 100.0, 1.0)
        memory_score = 1.0 - min(self.memory_usage / 100.0, 1.0)
        error_score = 1.0 - min(self.error_rate, 1.0)
        latency_score = 1.0 - min(self.latency_ms / 1000.0, 1.0)  # Normalize to 1s
        
        # Weighted average
        return (cpu_score * 0.25 + memory_score * 0.25 + 
                error_score * 0.3 + latency_score * 0.2)
    
    def can_handle_request(self, request: Request) -> bool:
        """Check if worker can handle request."""
        return (
            self.status == WorkerStatus.IDLE and
            self.pillar == request.pillar and
            request.agent_type in self.agent_types and
            self.available_capacity > 0
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "pillar": self.pillar,
            "agent_types": list(self.agent_types),
            "status": self.status.value,
            "capacity": self.capacity,
            "current_load": self.current_load,
            "available_capacity": self.available_capacity,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "latency_ms": self.latency_ms,
            "error_rate": self.error_rate,
            "health_score": self.health_score,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class RouteConfig:
    """Configuration for request routing."""
    enable_sticky_sessions: bool = True
    session_ttl_seconds: int = 3600
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: float = 0.5  # Error rate threshold
    circuit_breaker_timeout: int = 30  # Seconds
    enable_retry: bool = True
    max_retries: int = 3
    retry_delay_ms: int = 100
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    load_balancing_strategy: str = "weighted_round_robin"  # or "least_connections", "random"
    health_check_interval: int = 10  # Seconds


class LoadBalancer(ABC):
    """Abstract base class for load balancing strategies."""
    
    @abstractmethod
    async def select_worker(
        self,
        workers: List[WorkerNode],
        request: Request
    ) -> Optional[WorkerNode]:
        """Select a worker for the request."""
        pass


class RoundRobinLoadBalancer(LoadBalancer):
    """Round-robin load balancing."""
    
    def __init__(self):
        self._indices: Dict[str, int] = defaultdict(int)
    
    async def select_worker(
        self,
        workers: List[WorkerNode],
        request: Request
    ) -> Optional[WorkerNode]:
        """Select worker using round-robin."""
        key = f"{request.pillar}:{request.agent_type}"
        eligible_workers = [w for w in workers if w.can_handle_request(request)]
        
        if not eligible_workers:
            return None
        
        # Get next index
        index = self._indices[key] % len(eligible_workers)
        self._indices[key] = (self._indices[key] + 1) % len(eligible_workers)
        
        return eligible_workers[index]


class WeightedRoundRobinLoadBalancer(LoadBalancer):
    """Weighted round-robin based on health score and capacity."""
    
    async def select_worker(
        self,
        workers: List[WorkerNode],
        request: Request
    ) -> Optional[WorkerNode]:
        """Select worker using weighted round-robin."""
        eligible_workers = [w for w in workers if w.can_handle_request(request)]
        
        if not eligible_workers:
            return None
        
        # Calculate weights based on health score and available capacity
        weights = []
        for worker in eligible_workers:
            weight = worker.health_score * worker.available_capacity
            weights.append(weight)
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(eligible_workers)
        
        # Select based on weights
        r = random.uniform(0, total_weight)
        cumsum = 0
        for i, weight in enumerate(weights):
            cumsum += weight
            if r <= cumsum:
                return eligible_workers[i]
        
        return eligible_workers[-1]


class LeastConnectionsLoadBalancer(LoadBalancer):
    """Least connections load balancing."""
    
    async def select_worker(
        self,
        workers: List[WorkerNode],
        request: Request
    ) -> Optional[WorkerNode]:
        """Select worker with least connections."""
        eligible_workers = [w for w in workers if w.can_handle_request(request)]
        
        if not eligible_workers:
            return None
        
        # Sort by current load
        return min(eligible_workers, key=lambda w: w.current_load)


class WorkerPool:
    """Pool of worker nodes."""
    
    def __init__(self):
        self._workers: Dict[str, WorkerNode] = {}
        self._workers_by_pillar: Dict[str, Set[str]] = defaultdict(set)
        self._circuit_breakers: Dict[str, datetime] = {}
    
    def register_worker(self, worker: WorkerNode):
        """Register a worker node."""
        self._workers[worker.id] = worker
        self._workers_by_pillar[worker.pillar].add(worker.id)
        logger.info(f"Registered worker: {worker.name} ({worker.pillar})")
    
    def unregister_worker(self, worker_id: str):
        """Unregister a worker node."""
        if worker_id in self._workers:
            worker = self._workers[worker_id]
            self._workers_by_pillar[worker.pillar].discard(worker_id)
            del self._workers[worker_id]
            logger.info(f"Unregistered worker: {worker.name}")
    
    def get_workers(self, pillar: Optional[str] = None) -> List[WorkerNode]:
        """Get workers, optionally filtered by pillar."""
        if pillar:
            worker_ids = self._workers_by_pillar.get(pillar, set())
            return [self._workers[wid] for wid in worker_ids if wid in self._workers]
        return list(self._workers.values())
    
    def update_worker_metrics(
        self,
        worker_id: str,
        current_load: Optional[int] = None,
        cpu_usage: Optional[float] = None,
        memory_usage: Optional[float] = None,
        latency_ms: Optional[float] = None,
        error_rate: Optional[float] = None
    ):
        """Update worker metrics."""
        if worker_id in self._workers:
            worker = self._workers[worker_id]
            if current_load is not None:
                worker.current_load = current_load
            if cpu_usage is not None:
                worker.cpu_usage = cpu_usage
            if memory_usage is not None:
                worker.memory_usage = memory_usage
            if latency_ms is not None:
                worker.latency_ms = latency_ms
            if error_rate is not None:
                worker.error_rate = error_rate
            worker.last_heartbeat = datetime.now()
    
    def check_circuit_breaker(self, worker_id: str, config: RouteConfig) -> bool:
        """Check if circuit breaker is open for worker."""
        if not config.enable_circuit_breaker:
            return False
        
        if worker_id not in self._workers:
            return True
        
        worker = self._workers[worker_id]
        
        # Check error rate threshold
        if worker.error_rate > config.circuit_breaker_threshold:
            if worker_id not in self._circuit_breakers:
                self._circuit_breakers[worker_id] = datetime.now()
                logger.warning(f"Circuit breaker opened for worker: {worker.name}")
            
            # Check timeout
            time_since_open = (datetime.now() - self._circuit_breakers[worker_id]).seconds
            if time_since_open < config.circuit_breaker_timeout:
                return True
            else:
                # Reset circuit breaker
                del self._circuit_breakers[worker_id]
                logger.info(f"Circuit breaker reset for worker: {worker.name}")
        
        return False
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        total_capacity = sum(w.capacity for w in self._workers.values())
        total_load = sum(w.current_load for w in self._workers.values())
        
        stats_by_pillar = {}
        for pillar, worker_ids in self._workers_by_pillar.items():
            workers = [self._workers[wid] for wid in worker_ids if wid in self._workers]
            stats_by_pillar[pillar] = {
                "worker_count": len(workers),
                "total_capacity": sum(w.capacity for w in workers),
                "current_load": sum(w.current_load for w in workers),
                "avg_cpu": sum(w.cpu_usage for w in workers) / len(workers) if workers else 0,
                "avg_memory": sum(w.memory_usage for w in workers) / len(workers) if workers else 0,
                "avg_latency": sum(w.latency_ms for w in workers) / len(workers) if workers else 0
            }
        
        return {
            "total_workers": len(self._workers),
            "total_capacity": total_capacity,
            "total_load": total_load,
            "utilization": total_load / total_capacity if total_capacity > 0 else 0,
            "circuit_breakers_open": len(self._circuit_breakers),
            "stats_by_pillar": stats_by_pillar
        }


class RequestRouter:
    """Routes requests to appropriate workers."""
    
    def __init__(self, config: RouteConfig):
        self.config = config
        self._worker_pool = WorkerPool()
        self._load_balancer = self._create_load_balancer()
        self._request_queue: Dict[str, deque] = defaultdict(deque)
        self._sticky_sessions: Dict[str, str] = {}  # lineage_id -> worker_id
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
    
    def _create_load_balancer(self) -> LoadBalancer:
        """Create load balancer based on strategy."""
        strategy = self.config.load_balancing_strategy
        if strategy == "round_robin":
            return RoundRobinLoadBalancer()
        elif strategy == "weighted_round_robin":
            return WeightedRoundRobinLoadBalancer()
        elif strategy == "least_connections":
            return LeastConnectionsLoadBalancer()
        else:
            logger.warning(f"Unknown strategy: {strategy}, using weighted round robin")
            return WeightedRoundRobinLoadBalancer()
    
    def register_worker(self, worker: WorkerNode):
        """Register a worker node."""
        self._worker_pool.register_worker(worker)
    
    def unregister_worker(self, worker_id: str):
        """Unregister a worker node."""
        self._worker_pool.unregister_worker(worker_id)
        
        # Clean up sticky sessions
        sessions_to_remove = [
            lid for lid, wid in self._sticky_sessions.items()
            if wid == worker_id
        ]
        for lid in sessions_to_remove:
            del self._sticky_sessions[lid]
    
    async def route_request(self, request: Request) -> Optional[WorkerNode]:
        """Route request to appropriate worker."""
        logger.info(f"Routing request: {request.id} ({request.pillar}/{request.agent_type})")
        
        # Check cache
        if self.config.enable_caching:
            cache_key = self._get_cache_key(request)
            if cache_key in self._cache:
                cache_age = (datetime.now() - self._cache_timestamps[cache_key]).seconds
                if cache_age < self.config.cache_ttl_seconds:
                    logger.info(f"Cache hit for request: {request.id}")
                    return self._cache[cache_key]
        
        # Check sticky session
        if self.config.enable_sticky_sessions and request.lineage_id:
            if request.lineage_id in self._sticky_sessions:
                worker_id = self._sticky_sessions[request.lineage_id]
                worker = self._worker_pool._workers.get(worker_id)
                if worker and worker.can_handle_request(request):
                    logger.info(f"Using sticky session for request: {request.id}")
                    return worker
        
        # Get eligible workers
        workers = self._worker_pool.get_workers(request.pillar)
        
        # Filter out circuit breaker workers
        if self.config.enable_circuit_breaker:
            workers = [
                w for w in workers
                if not self._worker_pool.check_circuit_breaker(w.id, self.config)
            ]
        
        # Select worker using load balancer
        worker = await self._load_balancer.select_worker(workers, request)
        
        if not worker:
            # No worker available, queue request
            queue_key = f"{request.pillar}:{request.agent_type}"
            self._request_queue[queue_key].append(request)
            logger.warning(f"No worker available, queued request: {request.id}")
            return None
        
        # Update sticky session
        if self.config.enable_sticky_sessions and request.lineage_id:
            self._sticky_sessions[request.lineage_id] = worker.id
        
        # Update cache
        if self.config.enable_caching:
            cache_key = self._get_cache_key(request)
            self._cache[cache_key] = worker
            self._cache_timestamps[cache_key] = datetime.now()
        
        logger.info(f"Routed request {request.id} to worker: {worker.name}")
        return worker
    
    async def process_queued_requests(self):
        """Process queued requests when workers become available."""
        for queue_key, queue in self._request_queue.items():
            if not queue:
                continue
            
            # Try to process queued requests
            processed = []
            for request in queue:
                worker = await self.route_request(request)
                if worker:
                    processed.append(request)
                else:
                    break  # No more workers available
            
            # Remove processed requests
            for request in processed:
                queue.remove(request)
    
    def _get_cache_key(self, request: Request) -> str:
        """Generate cache key for request."""
        # Simple cache key based on routing attributes
        return f"{request.tenant_id}:{request.pillar}:{request.agent_type}:{request.aml_level}"
    
    def update_worker_metrics(self, worker_id: str, **metrics):
        """Update worker metrics."""
        self._worker_pool.update_worker_metrics(worker_id, **metrics)
    
    async def health_check(self):
        """Perform health checks on workers."""
        current_time = datetime.now()
        for worker in self._worker_pool.get_workers():
            # Check heartbeat timeout
            time_since_heartbeat = (current_time - worker.last_heartbeat).seconds
            if time_since_heartbeat > self.config.health_check_interval * 3:
                logger.warning(f"Worker {worker.name} missed heartbeat, marking offline")
                worker.status = WorkerStatus.OFFLINE
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        pool_stats = self._worker_pool.get_pool_stats()
        
        # Queue stats
        queue_stats = {}
        total_queued = 0
        for queue_key, queue in self._request_queue.items():
            queue_stats[queue_key] = len(queue)
            total_queued += len(queue)
        
        return {
            "pool_stats": pool_stats,
            "queue_stats": queue_stats,
            "total_queued": total_queued,
            "sticky_sessions": len(self._sticky_sessions),
            "cache_entries": len(self._cache),
            "load_balancer": self.config.load_balancing_strategy
        }
    
    async def scale_workers(self, pillar: str, agent_type: str, target_count: int):
        """Scale workers for specific pillar/agent type."""
        # This would integrate with Kubernetes HPA or Cloud Run
        # For demo, we just log the scaling request
        logger.info(f"Scaling request: {pillar}/{agent_type} to {target_count} workers")
        
        # Mock autoscaling logic
        current_workers = [
            w for w in self._worker_pool.get_workers(pillar)
            if agent_type in w.agent_types
        ]
        
        current_count = len(current_workers)
        
        if target_count > current_count:
            # Scale up
            for i in range(target_count - current_count):
                worker = WorkerNode(
                    name=f"{pillar}-{agent_type}-{current_count + i + 1}",
                    host=f"worker-{current_count + i + 1}.local",
                    port=8080,
                    pillar=pillar,
                    agent_types={agent_type}
                )
                self.register_worker(worker)
        
        elif target_count < current_count:
            # Scale down
            workers_to_remove = current_workers[target_count:]
            for worker in workers_to_remove:
                worker.status = WorkerStatus.DRAINING
                # Would drain connections before removal
                self.unregister_worker(worker.id)