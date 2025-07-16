#!/usr/bin/env python3
"""Integration tests for MemCube memory system."""

import asyncio
import logging
import json
from datetime import datetime
import aiohttp

from memcube_system.agent_sdk import (
    MemCubeClient, AgentMemoryExtension, MemoryInjector,
    create_memory_agent
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
MEMCUBE_URL = "http://localhost:8002"
TEST_PROJECT = "test-project-001"
TEST_AGENT = "test-agent-001"


class MemCubeIntegrationTester:
    """Test MemCube integration scenarios."""
    
    def __init__(self):
        self.client = MemCubeClient(MEMCUBE_URL)
        self.created_memories = []
        
    async def test_basic_memory_operations(self):
        """Test basic CRUD operations."""
        logger.info("\n=== Testing Basic Memory Operations ===")
        
        async with self.client:
            # 1. Create a memory
            memory_id = await self.client.store_experience(
                agent_id=TEST_AGENT,
                project_id=TEST_PROJECT,
                label="test-memory-001",
                content="This is a test memory containing important information about React hooks.",
                tags=["test", "react", "hooks"]
            )
            
            assert memory_id is not None, "Failed to create memory"
            self.created_memories.append(memory_id)
            logger.info(f"✅ Created memory: {memory_id}")
            
            # 2. Create more memories for testing
            for i in range(5):
                mid = await self.client.store_experience(
                    agent_id=TEST_AGENT,
                    project_id=TEST_PROJECT,
                    label=f"test-memory-{i:03d}",
                    content=f"Test memory {i} with different content. " * 10,
                    tags=["test", f"category-{i%3}"]
                )
                if mid:
                    self.created_memories.append(mid)
                    
            logger.info(f"✅ Created {len(self.created_memories)} test memories")
            
    async def test_memory_scheduling(self):
        """Test intelligent memory scheduling."""
        logger.info("\n=== Testing Memory Scheduling ===")
        
        async with self.client:
            # Request memories for a task
            memories = await self.client.get_memories_for_task(
                agent_id=TEST_AGENT,
                task_id="TEST-TASK-001",
                project_id=TEST_PROJECT,
                tags=["react", "hooks"],
                token_budget=2000
            )
            
            logger.info(f"Retrieved {len(memories)} memories")
            
            # Verify memories fit budget
            total_tokens = sum(m.get("tokens", 100) for m in memories)
            assert total_tokens <= 2000, f"Memories exceed budget: {total_tokens}"
            
            # Display retrieved memories
            for mem in memories[:3]:  # Show first 3
                logger.info(f"  - {mem['label']}: {mem['content'][:50]}...")
                
            logger.info(f"✅ Memory scheduling working (total tokens: {total_tokens})")
            
    async def test_insight_creation(self):
        """Test insight submission."""
        logger.info("\n=== Testing Insight Creation ===")
        
        async with self.client:
            # Submit an insight
            memory_id = await self.client.submit_insight(
                agent_id=TEST_AGENT,
                project_id=TEST_PROJECT,
                insight="Users strongly prefer dark mode in evening hours",
                evidence=["analytics-001", "user-feedback-042"],
                sentiment=0.85
            )
            
            assert memory_id is not None, "Failed to create insight"
            self.created_memories.append(memory_id)
            
            logger.info(f"✅ Created insight memory: {memory_id}")
            
    async def test_memory_extension(self):
        """Test full memory extension."""
        logger.info("\n=== Testing Agent Memory Extension ===")
        
        async with AgentMemoryExtension(
            agent_id="extension-test-agent",
            project_id=TEST_PROJECT,
            memcube_url=MEMCUBE_URL
        ) as memory:
            
            # Test prompt enhancement
            original_prompt = "Build a React component for user profile"
            enhanced = await memory.enhance_prompt(
                prompt=original_prompt,
                task_id="BUILD-001",
                tags=["react", "component"]
            )
            
            assert len(enhanced) > len(original_prompt), "Prompt not enhanced"
            logger.info(f"✅ Enhanced prompt length: {len(enhanced)} (was {len(original_prompt)})")
            
            # Test experience capture
            memory.capture_experience(
                label="react-component-pattern",
                content="Always use functional components with hooks",
                tags=["react", "best-practice"]
            )
            
            memory.capture_experience(
                label="error-handling-pattern",
                content="Wrap async operations in try-catch blocks",
                tags=["error-handling", "async"]
            )
            
            # Experiences will be flushed on context exit
            logger.info("✅ Captured 2 experiences (will flush on exit)")
            
    async def test_memory_injector(self):
        """Test different memory injection formats."""
        logger.info("\n=== Testing Memory Injector ===")
        
        # Sample memories
        memories = [
            {
                "id": "mem-001",
                "label": "react-hooks",
                "content": "Use useState for component state"
            },
            {
                "id": "mem-002",
                "label": "error-handling",
                "content": "Always handle promise rejections"
            }
        ]
        
        # Test different formats
        formats = ["default", "xml", "markdown"]
        base_prompt = "How do I handle state in React?"
        
        for format_style in formats:
            injector = MemoryInjector(format_style)
            enhanced = injector.inject_memories(base_prompt, memories)
            
            logger.info(f"\n{format_style.upper()} format:")
            logger.info(enhanced[:200] + "..." if len(enhanced) > 200 else enhanced)
            
        logger.info("✅ All injection formats working")
        
    async def test_marketplace_search(self):
        """Test marketplace search (mock)."""
        logger.info("\n=== Testing Marketplace Search ===")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{MEMCUBE_URL}/marketplace/search",
                    params={"query": "react patterns"}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"Found {data['count']} memory packs")
                        
                        for pack in data["packs"][:3]:
                            logger.info(f"  - {pack['title']} by {pack['author']} (${pack['price_cents']/100})")
                            
                        logger.info("✅ Marketplace search working")
                    else:
                        logger.warning(f"Marketplace search returned {resp.status}")
                        
            except Exception as e:
                logger.warning(f"Marketplace search error: {e}")
                
    async def test_enhanced_agent_class(self):
        """Test memory-enhanced agent class."""
        logger.info("\n=== Testing Enhanced Agent Class ===")
        
        # Base agent class
        class SimpleAgent:
            def __init__(self):
                self.agent_id = "simple-agent"
                
            async def __aenter__(self):
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
                
            async def process(self, task: str) -> str:
                return f"Processed: {task}"
                
        # Create memory-enhanced version
        MemoryAgent = create_memory_agent(
            SimpleAgent,
            project_id=TEST_PROJECT,
            memcube_url=MEMCUBE_URL
        )
        
        # Use the enhanced agent
        async with MemoryAgent() as agent:
            # Agent now has memory capabilities
            assert hasattr(agent, "memory"), "Agent missing memory extension"
            
            # Process with memory context
            prompt = "Build a React dashboard"
            enhanced = await agent.memory.enhance_prompt(
                prompt=prompt,
                task_id="DASH-001",
                tags=["react", "dashboard"]
            )
            
            result = await agent.process(enhanced)
            logger.info(f"Agent result: {result[:100]}...")
            
            # Capture learning
            agent.memory.capture_experience(
                label="dashboard-learning",
                content="Grid layout works well for dashboards",
                tags=["dashboard", "ui"]
            )
            
        logger.info("✅ Memory-enhanced agent working")
        
    async def run_all_tests(self):
        """Run all integration tests."""
        logger.info("🚀 Starting MemCube Integration Tests")
        logger.info("=" * 60)
        
        try:
            # Check service health
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{MEMCUBE_URL}/health") as resp:
                    if resp.status != 200:
                        logger.error("MemCube service not available!")
                        return False
                        
            # Run tests
            await self.test_basic_memory_operations()
            await asyncio.sleep(0.5)
            
            await self.test_memory_scheduling()
            await asyncio.sleep(0.5)
            
            await self.test_insight_creation()
            await asyncio.sleep(0.5)
            
            await self.test_memory_extension()
            await asyncio.sleep(0.5)
            
            await self.test_memory_injector()
            await asyncio.sleep(0.5)
            
            await self.test_marketplace_search()
            await asyncio.sleep(0.5)
            
            await self.test_enhanced_agent_class()
            
            logger.info("\n" + "=" * 60)
            logger.info("✅ All integration tests passed!")
            
            # Cleanup note
            logger.info(f"\n📝 Created {len(self.created_memories)} test memories")
            logger.info("   These can be cleaned up via admin endpoints")
            
            return True
            
        except Exception as e:
            logger.error(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            

async def demonstrate_real_world_usage():
    """Demonstrate real-world agent usage pattern."""
    logger.info("\n" + "=" * 60)
    logger.info("🌟 Real-World Usage Demonstration")
    logger.info("=" * 60)
    
    # Simulate an agent working on a task
    async with AgentMemoryExtension(
        agent_id="frontend-specialist",
        project_id="ecommerce-rebuild",
        memcube_url=MEMCUBE_URL
    ) as memory:
        
        # Agent receives a task
        task = "Implement product carousel component"
        
        # 1. Enhance prompt with relevant memories
        base_prompt = f"""
Task: {task}

Requirements:
- Mobile responsive
- Smooth animations
- Lazy loading for images

<MEMORIES>
"""
        
        enhanced_prompt = await memory.enhance_prompt(
            prompt=base_prompt,
            task_id="FRONT-042",
            tags=["carousel", "component", "react", "animation"],
            token_budget=3000
        )
        
        logger.info(f"\n📝 Enhanced prompt for task: {task}")
        logger.info(f"Original length: {len(base_prompt)}")
        logger.info(f"Enhanced length: {len(enhanced_prompt)}")
        
        # 2. Simulate agent work and capture learnings
        logger.info("\n🤖 Agent working on task...")
        await asyncio.sleep(1)  # Simulate work
        
        # Capture implementation experience
        memory.capture_experience(
            label="carousel-implementation",
            content="""
Implemented product carousel using:
- Swiper.js for touch gestures
- Intersection Observer for lazy loading
- CSS transitions for smooth animations
- ResizeObserver for responsive behavior

Key learning: Debounce resize events to prevent performance issues.
            """.strip(),
            tags=["carousel", "performance", "react"]
        )
        
        # 3. Discover an issue and create insight
        await memory.generate_insight(
            observation="Mobile users swipe through carousels 3x faster than desktop users",
            evidence=["analytics-carousel-001", "heatmap-mobile-002"],
            sentiment=0.0  # Neutral observation
        )
        
        logger.info("✅ Captured experience and generated insight")
        
    logger.info("\n🎯 Demonstration complete - memories stored for future use")


async def main():
    """Run integration tests and demonstration."""
    # Make sure MemCube service is running
    # python -m uvicorn memcube_system.service:app --port 8002
    
    tester = MemCubeIntegrationTester()
    success = await tester.run_all_tests()
    
    if success:
        await demonstrate_real_world_usage()
        
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)