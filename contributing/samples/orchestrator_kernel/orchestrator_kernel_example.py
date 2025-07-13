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

"""Comprehensive demonstration of the Orchestrator Kernel capabilities."""

import asyncio
import logging
import yaml
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Orchestrator kernel components
try:
    from .kernel import OrchestratorKernel, KernelConfig, ExecutionContext
    from .execution_graph import GraphNode, NodeType, ExecutionGraph
    from .react_loop import LoopConfig, AMLPolicyHook
    from .request_router import Request, WorkerNode, RequestPriority, RouteConfig
except ImportError:
    from kernel import OrchestratorKernel, KernelConfig, ExecutionContext
    from execution_graph import GraphNode, NodeType, ExecutionGraph
    from react_loop import LoopConfig, AMLPolicyHook
    from request_router import Request, WorkerNode, RequestPriority, RouteConfig

# External integrations
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from control_plane.policy_engine import PolicyEngine
    from control_plane.autonomy_manager import AutonomyManager
    from data_mesh.event_bus import EventBusFactory
    from data_mesh.lineage_service import LineageService
    from trust.observability import ObservabilityProvider
    HAS_INTEGRATIONS = True
except ImportError:
    HAS_INTEGRATIONS = False
    logging.warning("Some integrations not available, running in standalone mode")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrchestratorKernelDemo:
    """Demonstrates orchestrator kernel capabilities."""
    
    def __init__(self):
        # Configure kernel
        self.kernel_config = KernelConfig(
            enable_observability=HAS_INTEGRATIONS,
            enable_policy_checks=HAS_INTEGRATIONS,
            enable_event_bus=HAS_INTEGRATIONS,
            enable_lineage_tracking=HAS_INTEGRATIONS,
            health_check_interval=5,
            metrics_export_interval=10,
            route_config=RouteConfig(
                load_balancing_strategy="weighted_round_robin",
                enable_circuit_breaker=True,
                circuit_breaker_threshold=0.3
            )
        )
        
        self.kernel = OrchestratorKernel(self.kernel_config)
        
        # Integration components (if available)
        self.policy_engine = None
        self.event_bus = None
        self.lineage_service = None
        self.observability = None
        
        if HAS_INTEGRATIONS:
            self._setup_integrations()
    
    def _setup_integrations(self):
        """Set up external integrations."""
        # Policy engine
        self.policy_engine = PolicyEngine()
        
        # Event bus
        self.event_bus = EventBusFactory.create("memory")
        
        # Lineage service
        self.lineage_service = LineageService()
        
        # Observability
        self.observability = ObservabilityProvider({
            "service_name": "orchestrator_kernel_demo",
            "export_endpoint": "http://localhost:4317"
        })
    
    async def initialize(self):
        """Initialize the demo."""
        logger.info("=€ Initializing Orchestrator Kernel Demo")
        
        # Initialize kernel with integrations
        await self.kernel.initialize(
            policy_engine=self.policy_engine,
            event_bus=self.event_bus,
            lineage_service=self.lineage_service,
            observability=self.observability
        )
        
        # Register sample workers
        await self._register_sample_workers()
        
        # Register sample graphs
        await self._register_sample_graphs()
        
        logger.info(" Demo initialization complete")
    
    async def _register_sample_workers(self):
        """Register sample worker nodes."""
        # Customer Success workers
        for i in range(3):
            worker = WorkerNode(
                name=f"cs-worker-{i+1}",
                host=f"cs-worker-{i+1}.local",
                port=8080,
                pillar="customer_success",
                agent_types={"refund_bot", "support_agent"},
                capacity=5,
                cpu_usage=20 + i * 10,
                memory_usage=30 + i * 5,
                latency_ms=50 + i * 10
            )
            self.kernel._request_router.register_worker(worker)
        
        # Growth Engine workers
        for i in range(2):
            worker = WorkerNode(
                name=f"growth-worker-{i+1}",
                host=f"growth-worker-{i+1}.local",
                port=8080,
                pillar="growth_engine",
                agent_types={"pricing_bot", "campaign_manager"},
                capacity=8,
                cpu_usage=15 + i * 15,
                memory_usage=25 + i * 10,
                latency_ms=40 + i * 20
            )
            self.kernel._request_router.register_worker(worker)
        
        logger.info(" Registered 5 worker nodes across 2 pillars")
    
    async def _register_sample_graphs(self):
        """Register sample execution graphs."""
        # Refund processing graph
        refund_graph_yaml = """
name: customer_success_refund_bot
version: 1.0.0
metadata:
  description: Automated refund processing workflow
  owner: customer_success_team

nodes:
  - id: analyze_request
    name: Analyze Refund Request
    type: llm_call
    config:
      prompt: Analyze the refund request and determine validity
    checkpoint: true
    
  - id: check_policy
    name: Check Refund Policy
    type: conditional_branch
    config:
      condition: valid_reason
      
  - id: calculate_amount
    name: Calculate Refund Amount
    type: tool_invocation
    config:
      tool: calculate_refund_amount
      
  - id: process_refund
    name: Process Refund
    type: tool_invocation
    config:
      tool: create_refund
    checkpoint: true
    max_retries: 2
    
  - id: notify_customer
    name: Notify Customer
    type: tool_invocation
    config:
      tool: send_email
      
  - id: complete
    name: Complete
    type: finish

edges:
  - from: analyze_request
    to: check_policy
  - from: check_policy
    to: calculate_amount
  - from: calculate_amount
    to: process_refund
  - from: process_refund
    to: notify_customer
  - from: notify_customer
    to: complete

entry_node: analyze_request
"""
        
        # Register refund graph
        await self.kernel.register_graph(refund_graph_yaml, format="yaml")
        
        # Pricing optimization graph
        pricing_graph = {
            "name": "growth_engine_pricing_bot",
            "version": "1.0.0",
            "metadata": {
                "description": "Dynamic pricing optimization workflow",
                "owner": "growth_team"
            },
            "nodes": [
                {
                    "id": "market_analysis",
                    "name": "Analyze Market Conditions",
                    "type": "parallel_branch",
                    "config": {
                        "branches": ["competitor_prices", "demand_forecast", "inventory_levels"]
                    }
                },
                {
                    "id": "competitor_prices",
                    "name": "Get Competitor Prices",
                    "type": "tool_invocation",
                    "config": {"tool": "scrape_competitor_prices"}
                },
                {
                    "id": "demand_forecast",
                    "name": "Forecast Demand",
                    "type": "tool_invocation",
                    "config": {"tool": "ml_demand_forecast"}
                },
                {
                    "id": "inventory_levels",
                    "name": "Check Inventory",
                    "type": "tool_invocation",
                    "config": {"tool": "query_inventory"}
                },
                {
                    "id": "optimize_price",
                    "name": "Optimize Pricing",
                    "type": "llm_call",
                    "config": {"prompt": "Based on market analysis, recommend optimal pricing"},
                    "checkpoint": True
                },
                {
                    "id": "apply_pricing",
                    "name": "Apply New Pricing",
                    "type": "tool_invocation",
                    "config": {"tool": "update_product_prices"}
                }
            ],
            "edges": [
                {"from": "market_analysis", "to": "competitor_prices"},
                {"from": "market_analysis", "to": "demand_forecast"},
                {"from": "market_analysis", "to": "inventory_levels"},
                {"from": "competitor_prices", "to": "optimize_price"},
                {"from": "demand_forecast", "to": "optimize_price"},
                {"from": "inventory_levels", "to": "optimize_price"},
                {"from": "optimize_price", "to": "apply_pricing"}
            ],
            "entry_node": "market_analysis"
        }
        
        await self.kernel.register_graph(pricing_graph, format="python")
        
        logger.info(" Registered 2 execution graphs")
    
    async def demonstrate_request_routing(self):
        """Demonstrate request routing and load balancing."""
        logger.info("\n" + "="*60)
        logger.info("=¦ DEMONSTRATING REQUEST ROUTING & LOAD BALANCING")
        logger.info("="*60)
        
        # Create multiple requests
        requests = [
            Request(
                tenant_id="tenant_001",
                pillar="customer_success",
                agent_type="refund_bot",
                aml_level=3,
                priority=RequestPriority.HIGH,
                payload={"order_id": "ORD-123", "reason": "damaged_item", "amount": 75},
                lineage_id="trace_refund_001"
            ),
            Request(
                tenant_id="tenant_001",
                pillar="customer_success",
                agent_type="refund_bot",
                aml_level=3,
                priority=RequestPriority.NORMAL,
                payload={"order_id": "ORD-456", "reason": "wrong_item", "amount": 50},
                lineage_id="trace_refund_002"
            ),
            Request(
                tenant_id="tenant_002",
                pillar="growth_engine",
                agent_type="pricing_bot",
                aml_level=4,
                priority=RequestPriority.HIGH,
                payload={"products": ["PROD-001", "PROD-002"], "strategy": "competitive"},
                lineage_id="trace_pricing_001"
            )
        ]
        
        # Route requests
        for request in requests:
            worker = await self.kernel._request_router.route_request(request)
            if worker:
                logger.info(f" Routed {request.pillar}/{request.agent_type} to {worker.name}")
                logger.info(f"   Worker health: {worker.health_score:.2f}, load: {worker.current_load}/{worker.capacity}")
                
                # Simulate load increase
                self.kernel._request_router.update_worker_metrics(
                    worker.id,
                    current_load=worker.current_load + 1
                )
            else:
                logger.warning(f"L No worker available for {request.pillar}/{request.agent_type}")
        
        # Show routing statistics
        stats = self.kernel._request_router.get_routing_stats()
        logger.info(f"\n=Ê Routing Statistics:")
        logger.info(f"   Total workers: {stats['pool_stats']['total_workers']}")
        logger.info(f"   Total capacity: {stats['pool_stats']['total_capacity']}")
        logger.info(f"   Current utilization: {stats['pool_stats']['utilization']:.1%}")
        logger.info(f"   Queued requests: {stats['total_queued']}")
        logger.info(f"   Sticky sessions: {stats['sticky_sessions']}")
    
    async def demonstrate_react_loop_with_policies(self):
        """Demonstrate ReAct loop with policy enforcement."""
        logger.info("\n" + "="*60)
        logger.info("= DEMONSTRATING REACT LOOP WITH POLICY ENFORCEMENT")
        logger.info("="*60)
        
        # Simulate a refund request at different AML levels
        scenarios = [
            {
                "name": "Small refund at AML 3",
                "aml_level": 3,
                "amount": 50,
                "expected": "allowed"
            },
            {
                "name": "Large refund at AML 3",
                "aml_level": 3,
                "amount": 150,
                "expected": "denied"
            },
            {
                "name": "Large refund at AML 5",
                "aml_level": 5,
                "amount": 450,
                "expected": "allowed"
            }
        ]
        
        for scenario in scenarios:
            logger.info(f"\n>ê Scenario: {scenario['name']}")
            
            # Create request
            request = Request(
                tenant_id="tenant_001",
                pillar="customer_success",
                agent_type="refund_bot",
                aml_level=scenario["aml_level"],
                payload={
                    "order_id": "ORD-TEST",
                    "amount": scenario["amount"],
                    "reason": "test_scenario"
                }
            )
            
            # Mock execution to show policy checks
            try:
                # Create policy hook
                aml_hook = AMLPolicyHook(
                    aml_level=scenario["aml_level"],
                    caps=self.kernel._get_aml_caps("customer_success", scenario["aml_level"])
                )
                
                # Create mock tool call
                from react_loop import ToolCall, ReactState
                tool_call = ToolCall(
                    tool_name="create_refund",
                    parameters={"amount": scenario["amount"]}
                )
                
                state = ReactState()
                
                # Check policy
                allowed, reason = await aml_hook.check(tool_call, state, {})
                
                if allowed:
                    logger.info(f"    Policy check PASSED: Refund of ${scenario['amount']} allowed at AML {scenario['aml_level']}")
                else:
                    logger.info(f"   L Policy check DENIED: {reason}")
                    self.kernel._metrics["policy_denials"] += 1
                
                # Verify expectation
                result = "allowed" if allowed else "denied"
                if result == scenario["expected"]:
                    logger.info(f"    Result matches expectation: {scenario['expected']}")
                else:
                    logger.error(f"    Unexpected result: got {result}, expected {scenario['expected']}")
            
            except Exception as e:
                logger.error(f"   Error in scenario: {e}")
    
    async def demonstrate_graph_execution(self):
        """Demonstrate graph execution with checkpoints."""
        logger.info("\n" + "="*60)
        logger.info("=Ê DEMONSTRATING GRAPH EXECUTION & CHECKPOINTS")
        logger.info("="*60)
        
        # Create a simple demonstration graph
        demo_graph_yaml = """
name: demo_workflow
version: 1.0.0

nodes:
  - id: step1
    name: Step 1 - Initialize
    type: llm_call
    config:
      prompt: Initialize workflow
    checkpoint: true
    
  - id: step2
    name: Step 2 - Process
    type: tool_invocation
    config:
      tool: mock_processing
      
  - id: step3
    name: Step 3 - Validate
    type: conditional_branch
    config:
      condition: success
      
  - id: step4
    name: Step 4 - Complete
    type: finish
    checkpoint: true

edges:
  - from: step1
    to: step2
  - from: step2
    to: step3
  - from: step3
    to: step4

entry_node: step1
"""
        
        # Register and compile graph
        version = await self.kernel.register_graph(demo_graph_yaml, format="yaml")
        graph = self.kernel._graph_registry.get_graph("demo_workflow", version)
        
        logger.info(f"=Ý Registered demo graph version: {version}")
        logger.info(f"   Nodes: {len(graph.nodes)}")
        logger.info(f"   Checkpoints: {sum(1 for n in graph.nodes.values() if n.checkpoint_enabled)}")
        
        # Mock execution context
        context = {
            "request_id": "demo_001",
            "pillar": "demo",
            "status": "success"
        }
        
        # Execute graph
        logger.info("\n¶ Executing graph...")
        
        # Mock node execution results
        for node_id, node in graph.nodes.items():
            logger.info(f"   =Í Executing: {node.name}")
            
            if node.checkpoint_enabled:
                logger.info(f"      =¾ Checkpoint created at node: {node_id}")
            
            if node.node_type == NodeType.CONDITIONAL_BRANCH:
                logger.info(f"      =  Branch evaluation: {context.get('status') == 'success'}")
        
        logger.info("    Graph execution completed")
    
    async def demonstrate_autoscaling(self):
        """Demonstrate worker autoscaling."""
        logger.info("\n" + "="*60)
        logger.info("=È DEMONSTRATING AUTOSCALING")
        logger.info("="*60)
        
        # Show current state
        initial_stats = self.kernel._request_router.get_routing_stats()
        cs_workers = initial_stats["pool_stats"]["stats_by_pillar"].get("customer_success", {})
        
        logger.info(f"Initial Customer Success workers: {cs_workers.get('worker_count', 0)}")
        
        # Simulate high load
        logger.info("\n=% Simulating high load on Customer Success...")
        
        # Update worker metrics to simulate load
        workers = self.kernel._request_router._worker_pool.get_workers("customer_success")
        for worker in workers:
            self.kernel._request_router.update_worker_metrics(
                worker.id,
                current_load=worker.capacity - 1,  # Almost full
                cpu_usage=85.0,
                latency_ms=200.0
            )
        
        # Trigger scale up
        logger.info("=È Triggering scale up...")
        await self.kernel._request_router.scale_workers(
            pillar="customer_success",
            agent_type="refund_bot",
            target_count=5
        )
        
        # Show new state
        new_stats = self.kernel._request_router.get_routing_stats()
        new_cs_workers = new_stats["pool_stats"]["stats_by_pillar"].get("customer_success", {})
        
        logger.info(f"Customer Success workers after scaling: {new_cs_workers.get('worker_count', 0)}")
        logger.info(f"New total capacity: {new_cs_workers.get('total_capacity', 0)}")
    
    async def demonstrate_circuit_breaker(self):
        """Demonstrate circuit breaker pattern."""
        logger.info("\n" + "="*60)
        logger.info("¡ DEMONSTRATING CIRCUIT BREAKER")
        logger.info("="*60)
        
        # Get a worker and simulate failures
        workers = self.kernel._request_router._worker_pool.get_workers()
        if workers:
            worker = workers[0]
            logger.info(f"Testing circuit breaker on worker: {worker.name}")
            
            # Simulate high error rate
            logger.info("L Simulating high error rate...")
            self.kernel._request_router.update_worker_metrics(
                worker.id,
                error_rate=0.6  # 60% error rate
            )
            
            # Check if circuit breaker opens
            is_open = self.kernel._request_router._worker_pool.check_circuit_breaker(
                worker.id,
                self.kernel_config.route_config
            )
            
            if is_open:
                logger.info("¡ Circuit breaker OPENED - worker temporarily unavailable")
                logger.info(f"   Will reset after {self.kernel_config.route_config.circuit_breaker_timeout}s")
            else:
                logger.info(" Circuit breaker still closed")
            
            # Show impact on routing
            request = Request(
                pillar=worker.pillar,
                agent_type=list(worker.agent_types)[0] if worker.agent_types else "test",
                aml_level=3
            )
            
            routed_worker = await self.kernel._request_router.route_request(request)
            if routed_worker and routed_worker.id != worker.id:
                logger.info(f" Request routed to healthy worker: {routed_worker.name}")
            elif not routed_worker:
                logger.info("L No healthy workers available")
    
    async def demonstrate_full_scenario(self):
        """Demonstrate a complete end-to-end scenario."""
        logger.info("\n" + "="*80)
        logger.info("<¬ FULL SCENARIO: Shopify Order Refund Processing")
        logger.info("="*80)
        
        # Scenario: Order refund webhook from Shopify
        logger.info("\n1ã External trigger: Shopify webhook 'order_refunded'")
        
        refund_request = Request(
            tenant_id="shopify_store_123",
            pillar="customer_success",
            agent_type="refund_bot",
            aml_level=3,  # AML 3: Real-time execution with caps
            priority=RequestPriority.HIGH,
            payload={
                "order_id": "SHOP-ORD-789",
                "customer_email": "customer@example.com",
                "refund_amount": 89.99,
                "reason": "Product quality issue",
                "items": [
                    {"sku": "WIDGET-001", "quantity": 1, "price": 89.99}
                ]
            },
            lineage_id="shopify_webhook_20250113_001"
        )
        
        logger.info(f"   Order ID: {refund_request.payload['order_id']}")
        logger.info(f"   Amount: ${refund_request.payload['refund_amount']}")
        logger.info(f"   AML Level: {refund_request.aml_level}")
        
        # Process through kernel
        logger.info("\n2ã Kernel routing: Finding appropriate worker...")
        
        try:
            result = await self.kernel.handle_request(refund_request)
            
            logger.info("\n3ã Think-Act-Observe cycle:")
            logger.info("   > THINK: 'Customer requesting refund for quality issue'")
            logger.info("   <¯ ACT: create_refund($89.99)")
            logger.info("    Policy check: AML 3 cap ($100) - APPROVED")
            logger.info("   =@ OBSERVE: 'Refund processed successfully'")
            
            logger.info("\n4ã Spans & lineage:")
            logger.info(f"   Lineage ID: {refund_request.lineage_id}")
            logger.info("   Every step tracked with OpenTelemetry spans")
            logger.info("   Full audit trail available for compliance")
            
            # Show kernel metrics
            kernel_status = self.kernel.get_kernel_status()
            logger.info("\n=Ê Kernel Metrics:")
            logger.info(f"   Requests completed: {kernel_status['metrics']['requests_completed']}")
            logger.info(f"   Graphs executed: {kernel_status['metrics']['graphs_executed']}")
            logger.info(f"   Policy denials: {kernel_status['metrics']['policy_denials']}")
            
        except Exception as e:
            logger.error(f"Scenario failed: {e}")
    
    async def cleanup(self):
        """Clean up resources."""
        logger.info("\n>ù Cleaning up...")
        
        await self.kernel.shutdown()
        
        if self.event_bus:
            await self.event_bus.close()
        
        logger.info(" Cleanup complete")


async def main():
    """Run the orchestrator kernel demonstration."""
    print("=€ Orchestrator Kernel Demonstration")
    print("=" * 80)
    print("This demo showcases the runtime 'OS' for all agents:")
    print("- Unified execution graph management")
    print("- Think-Act-Observe loop implementation")
    print("- Request routing and load balancing")
    print("- Policy enforcement and circuit breakers")
    print("- Integration with Control Plane, Data Mesh, and Trust layers")
    print("=" * 80)
    
    demo = OrchestratorKernelDemo()
    
    try:
        # Initialize
        await demo.initialize()
        
        # Run demonstrations
        await demo.demonstrate_request_routing()
        await demo.demonstrate_react_loop_with_policies()
        await demo.demonstrate_graph_execution()
        await demo.demonstrate_autoscaling()
        await demo.demonstrate_circuit_breaker()
        await demo.demonstrate_full_scenario()
        
        # Show final kernel status
        print("\n" + "="*80)
        print("=Ê FINAL KERNEL STATUS")
        print("="*80)
        
        status = demo.kernel.get_kernel_status()
        print(f"Status: {status['status']}")
        print(f"Active executions: {status['active_executions']}")
        print(f"Registered graphs: {status['registered_graphs']}")
        print("\nRouting stats:")
        routing = status['routing_stats']['pool_stats']
        print(f"  Total workers: {routing['total_workers']}")
        print(f"  Total capacity: {routing['total_capacity']}")
        print(f"  Utilization: {routing['utilization']:.1%}")
        
        print("\n" + "="*80)
        print("<‰ ORCHESTRATOR KERNEL DEMONSTRATION COMPLETE!")
        print("="*80)
        print("\nKey capabilities demonstrated:")
        print(" Graph compilation and versioned execution")
        print(" ReAct loop with policy hooks (AML + OPA)")
        print(" Smart request routing with health-aware load balancing")
        print(" Circuit breakers and autoscaling")
        print(" Full observability and lineage tracking")
        print(" Integration with enterprise control/data/trust layers")
        
        print("\nThe Orchestrator Kernel provides:")
        print("<¯ Single policy choke-point for all tool calls")
        print("= Operational resilience with retries and failover")
        print("= Observability-first design with unified spans")
        print("=È Elastic scale like cloud microservices")
        print("= Seamless integration with business pillars")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
    finally:
        await demo.cleanup()


if __name__ == "__main__":
    asyncio.run(main())