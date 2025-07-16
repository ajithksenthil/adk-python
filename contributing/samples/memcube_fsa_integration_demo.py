#!/usr/bin/env python3
"""
Demonstration of MemCube + FSA Integration.

Shows how agents use both systems together:
- FSA for live state and coordination
- MemCube for persistent knowledge and experience
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

from state_memory_service.service import app as fsa_app
from memcube_system.agent_sdk import AgentMemoryExtension
from orchestrator_kernel.state_client_efficient import EfficientStateMemoryClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntelligentAgent:
    """
    An agent that uses both FSA (live state) and MemCube (persistent memory).
    
    This demonstrates the complementary nature of both systems.
    """
    
    def __init__(self, agent_id: str, project_id: str, tenant_id: str):
        self.agent_id = agent_id
        self.project_id = project_id
        self.tenant_id = tenant_id
        
        # FSA client for live state
        self.fsa_client = EfficientStateMemoryClient()
        
        # MemCube for persistent memory
        self.memory = AgentMemoryExtension(
            agent_id=agent_id,
            project_id=project_id
        )
        
    async def __aenter__(self):
        await self.fsa_client.__aenter__()
        await self.memory.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.memory.__aexit__(exc_type, exc_val, exc_tb)
        await self.fsa_client.__aexit__(exc_type, exc_val, exc_tb)
        
    async def execute_task(self, task_id: str, fsa_id: str) -> Dict[str, Any]:
        """
        Execute a task using both FSA and MemCube.
        
        Workflow:
        1. Read current state from FSA
        2. Get relevant memories from MemCube
        3. Execute task with combined context
        4. Update FSA state
        5. Store new experiences in MemCube
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Agent {self.agent_id} executing task {task_id}")
        logger.info(f"{'='*60}")
        
        # 1. Read live state from FSA (fast, targeted slice)
        logger.info("\n📊 Reading FSA state...")
        state_slice = await self.fsa_client.get_slice(
            tenant_id=self.tenant_id,
            fsa_id=fsa_id,
            slice_pattern=f"task:{task_id}",
            k=1
        )
        
        if state_slice:
            logger.info(f"FSA State (v{state_slice.version}):")
            logger.info(f"  Summary: {state_slice.summary}")
            
            task_data = state_slice.tasks.get(task_id, {})
            logger.info(f"  Task status: {task_data.get('status', 'UNKNOWN')}")
            logger.info(f"  Assigned team: {task_data.get('assigned_team', 'NONE')}")
        else:
            logger.warning("No FSA state found")
            task_data = {}
            
        # 2. Get relevant memories from MemCube
        logger.info("\n🧠 Retrieving relevant memories...")
        
        # Build prompt with task context
        base_prompt = f"""
Task: {task_id}
Type: {task_data.get('type', 'general')}
Description: {task_data.get('description', 'No description')}

Current project metrics from FSA:
{state_slice.summary if state_slice else 'No metrics available'}

Please complete this task following best practices.
"""
        
        # Enhance with memories
        enhanced_prompt = await self.memory.enhance_prompt(
            prompt=base_prompt,
            task_id=task_id,
            tags=self._extract_tags(task_data),
            token_budget=2000
        )
        
        logger.info(f"Enhanced prompt with memories (added {len(enhanced_prompt) - len(base_prompt)} chars)")
        
        # 3. Execute task (simulated)
        logger.info(f"\n🔧 Executing task {task_id}...")
        result = await self._perform_task(task_id, enhanced_prompt, task_data)
        
        # 4. Update FSA state with results
        logger.info("\n📝 Updating FSA state...")
        state_delta = {
            f"tasks.{task_id}.status": "COMPLETED",
            f"tasks.{task_id}.completed_at": datetime.utcnow().isoformat(),
            f"tasks.{task_id}.completed_by": self.agent_id,
            "metrics.tasks_completed": {"$inc": 1},
            f"agents_online.{self.agent_id}": datetime.utcnow().isoformat()
        }
        
        success = await self.fsa_client.apply_delta(
            tenant_id=self.tenant_id,
            fsa_id=fsa_id,
            delta=state_delta,
            actor=self.agent_id,
            lineage_id=f"task_{task_id}"
        )
        
        if success:
            logger.info("✅ FSA state updated")
        else:
            logger.warning("Failed to update FSA state")
            
        # 5. Store experience in MemCube
        logger.info("\n💾 Storing experience in MemCube...")
        
        # Capture what we learned
        if result.get("learnings"):
            for learning in result["learnings"]:
                self.memory.capture_experience(
                    label=f"task_{task_id}_learning",
                    content=learning,
                    tags=self._extract_tags(task_data) + ["experience"]
                )
                
        # Generate insights if applicable
        if result.get("insights"):
            for insight in result["insights"]:
                await self.memory.generate_insight(
                    observation=insight["observation"],
                    evidence=[task_id],
                    sentiment=insight.get("sentiment", 0.0)
                )
                
        logger.info(f"✅ Stored {len(result.get('learnings', []))} experiences and {len(result.get('insights', []))} insights")
        
        return result
        
    async def _perform_task(self, task_id: str, prompt: str, 
                          task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate task execution."""
        # In real implementation, this would call an LLM or execute actual work
        await asyncio.sleep(1)  # Simulate work
        
        # Generate some mock results based on task type
        task_type = task_data.get("type", "general")
        
        if "design" in task_type.lower():
            return {
                "status": "completed",
                "output": "Created design mockups",
                "learnings": [
                    "Users prefer minimalist interfaces with clear CTAs",
                    "Dark mode should be implemented from the start"
                ],
                "insights": [
                    {
                        "observation": "Card-based layouts improve user engagement by 23%",
                        "sentiment": 0.8
                    }
                ]
            }
        elif "implement" in task_type.lower():
            return {
                "status": "completed", 
                "output": "Implemented feature",
                "learnings": [
                    "React hooks simplify state management",
                    "Always implement error boundaries for robust components"
                ],
                "insights": []
            }
        else:
            return {
                "status": "completed",
                "output": f"Completed task {task_id}",
                "learnings": [
                    f"Generic learning from task {task_id}"
                ],
                "insights": []
            }
            
    def _extract_tags(self, task_data: Dict[str, Any]) -> List[str]:
        """Extract relevant tags from task data."""
        tags = []
        
        # Add task type as tag
        if task_type := task_data.get("type"):
            tags.append(task_type.lower())
            
        # Add team as tag
        if team := task_data.get("assigned_team"):
            tags.append(f"team_{team}")
            
        # Add any explicit tags
        if task_tags := task_data.get("tags"):
            tags.extend(task_tags)
            
        return tags


async def demonstrate_multi_agent_coordination():
    """
    Demonstrate multiple agents coordinating via FSA while building knowledge in MemCube.
    """
    logger.info("\n" + "="*80)
    logger.info("🚀 Multi-Agent FSA + MemCube Coordination Demo")
    logger.info("="*80)
    
    # Configuration
    tenant_id = "demo-tenant"
    fsa_id = "project-alpha-2024"
    project_id = "project-alpha"
    
    # Initialize FSA state with tasks
    logger.info("\n📋 Initializing project state in FSA...")
    
    async with EfficientStateMemoryClient() as fsa_client:
        initial_state = {
            "tasks": {
                "DESIGN_001": {
                    "task_id": "DESIGN_001",
                    "type": "design",
                    "description": "Design user dashboard",
                    "status": "PENDING",
                    "assigned_team": "frontend",
                    "tags": ["ui", "dashboard"]
                },
                "DESIGN_002": {
                    "task_id": "DESIGN_002", 
                    "type": "design",
                    "description": "Design mobile navigation",
                    "status": "PENDING",
                    "assigned_team": "mobile",
                    "tags": ["ui", "mobile", "navigation"]
                },
                "IMPL_001": {
                    "task_id": "IMPL_001",
                    "type": "implement",
                    "description": "Implement auth system",
                    "status": "PENDING",
                    "assigned_team": "backend",
                    "tags": ["auth", "security"]
                }
            },
            "metrics": {
                "tasks_total": 3,
                "tasks_completed": 0
            },
            "resources": {
                "budget_remaining": 50000
            },
            "agents_online": {}
        }
        
        # Post initial state
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://localhost:8000/state/{tenant_id}/{fsa_id}",
                json=initial_state,
                params={"actor": "system", "lineage_id": "init"}
            ) as resp:
                if resp.status == 200:
                    logger.info("✅ FSA state initialized")
                else:
                    logger.error(f"Failed to initialize FSA: {resp.status}")
                    return
                    
    # Create specialized agents
    agents = [
        IntelligentAgent("design-bot", project_id, tenant_id),
        IntelligentAgent("frontend-dev", project_id, tenant_id),
        IntelligentAgent("backend-dev", project_id, tenant_id)
    ]
    
    # Agents work on tasks concurrently
    logger.info(f"\n🤖 Deploying {len(agents)} agents to work on tasks...")
    
    # Each agent picks a task based on their specialty
    task_assignments = [
        (agents[0], "DESIGN_001"),  # design-bot
        (agents[1], "DESIGN_002"),  # frontend-dev  
        (agents[2], "IMPL_001")     # backend-dev
    ]
    
    # Execute tasks concurrently
    tasks = []
    for agent, task_id in task_assignments:
        async with agent:
            task = agent.execute_task(task_id, fsa_id)
            tasks.append(task)
            
    results = await asyncio.gather(*tasks)
    
    # Show final state
    logger.info("\n📊 Final Project State:")
    
    async with EfficientStateMemoryClient() as fsa_client:
        final_state = await fsa_client.get_slice(
            tenant_id=tenant_id,
            fsa_id=fsa_id,
            slice_pattern="*"
        )
        
        if final_state:
            logger.info(f"Version: {final_state.version}")
            logger.info(f"Summary: {final_state.summary}")
            
            # Show metrics
            metrics = final_state.slice_data.get("metrics", {})
            logger.info(f"\nMetrics:")
            logger.info(f"  Tasks completed: {metrics.get('tasks_completed', 0)}/{metrics.get('tasks_total', 0)}")
            
            # Show online agents
            agents_online = final_state.slice_data.get("agents_online", {})
            logger.info(f"\nAgents worked on project: {list(agents_online.keys())}")
            
    logger.info("\n" + "="*80)
    logger.info("✨ Demo Summary:")
    logger.info("- Agents coordinated via FSA (live state)")
    logger.info("- Each agent enhanced their work with MemCube memories")
    logger.info("- New learnings stored in MemCube for future tasks")
    logger.info("- Both systems working together for intelligent automation")
    logger.info("="*80)


async def main():
    """Run the integration demonstration."""
    # Ensure both services are running:
    # 1. FSA: python -m uvicorn state_memory_service.service_v2:app --port 8000
    # 2. MemCube: python -m uvicorn memcube_system.service:app --port 8002
    
    try:
        await demonstrate_multi_agent_coordination()
        return True
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)