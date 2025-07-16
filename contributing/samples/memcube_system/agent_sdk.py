"""Agent SDK extensions for MemCube memory integration."""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import aiohttp
import json

from .models import (
    MemoryScheduleRequest, MemCube, MemoryType,
    MemoryPriority, InsightCard
)

logger = logging.getLogger(__name__)


class MemCubeClient:
    """
    Client for agents to interact with MemCube system.
    
    Provides simplified interface for:
    - Memory retrieval
    - Memory creation
    - Insight submission
    - Context injection
    """
    
    def __init__(self, memcube_url: str = "http://localhost:8002"):
        self.base_url = memcube_url
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
            
    async def get_memories_for_task(self, agent_id: str, task_id: str,
                                  project_id: str, tags: List[str] = None,
                                  token_budget: int = 4000) -> List[Dict[str, Any]]:
        """
        Get relevant memories for current task.
        
        Returns formatted memories ready for context injection.
        """
        if not self._session:
            self._session = aiohttp.ClientSession()
            
        request = MemoryScheduleRequest(
            agent_id=agent_id,
            task_id=task_id,
            project_id=project_id,
            need_tags=tags or [],
            token_budget=token_budget,
            prefer_hot=True,
            include_insights=True
        )
        
        try:
            async with self._session.post(
                f"{self.base_url}/memories/schedule",
                json=request.dict()
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("memories", [])
                else:
                    logger.error(f"Failed to get memories: {resp.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting memories: {e}")
            return []
            
    async def store_experience(self, agent_id: str, project_id: str,
                             label: str, content: str,
                             tags: List[str] = None) -> Optional[str]:
        """Store an experience or learning as a memory."""
        if not self._session:
            self._session = aiohttp.ClientSession()
            
        try:
            payload = {
                "project_id": project_id,
                "label": label,
                "content": content,
                "type": "PLAINTEXT",
                "created_by": agent_id,
                "tags": tags or [],
                "priority": "WARM"
            }
            
            async with self._session.post(
                f"{self.base_url}/memories",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("id")
                else:
                    logger.error(f"Failed to store memory: {resp.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return None
            
    async def submit_insight(self, agent_id: str, project_id: str,
                           insight: str, evidence: List[str] = None,
                           sentiment: float = 0.0) -> Optional[str]:
        """Submit an insight based on observations."""
        if not self._session:
            self._session = aiohttp.ClientSession()
            
        try:
            payload = {
                "insight": insight,
                "evidence_refs": evidence or [],
                "sentiment": sentiment,
                "tags": []
            }
            
            async with self._session.post(
                f"{self.base_url}/insights",
                params={"project_id": project_id, "created_by": agent_id},
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("memory_id")
                else:
                    logger.error(f"Failed to submit insight: {resp.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error submitting insight: {e}")
            return None


class MemoryInjector:
    """
    Helper for injecting memories into agent prompts.
    
    Formats memories appropriately for LLM context.
    """
    
    def __init__(self, format_style: str = "default"):
        self.format_style = format_style
        
    def inject_memories(self, base_prompt: str, memories: List[Dict[str, Any]],
                       max_tokens: Optional[int] = None) -> str:
        """
        Inject memories into agent prompt.
        
        Args:
            base_prompt: Original prompt
            memories: List of memory dicts from MemCubeClient
            max_tokens: Optional token limit
            
        Returns:
            Prompt with memories injected
        """
        if not memories:
            return base_prompt
            
        # Format memories based on style
        if self.format_style == "xml":
            memory_section = self._format_xml(memories)
        elif self.format_style == "markdown":
            memory_section = self._format_markdown(memories)
        else:
            memory_section = self._format_default(memories)
            
        # Inject into prompt
        if "<MEMORIES>" in base_prompt:
            # Replace placeholder
            return base_prompt.replace("<MEMORIES>", memory_section)
        else:
            # Prepend to prompt
            return f"{memory_section}\n\n{base_prompt}"
            
    def _format_default(self, memories: List[Dict[str, Any]]) -> str:
        """Default memory formatting."""
        lines = ["=== Relevant Memories ==="]
        
        for mem in memories:
            lines.append(f"\n[{mem['label']}]")
            lines.append(mem['content'])
            
        lines.append("\n=== End Memories ===")
        return "\n".join(lines)
        
    def _format_xml(self, memories: List[Dict[str, Any]]) -> str:
        """XML-style memory formatting."""
        lines = ["<memories>"]
        
        for mem in memories:
            lines.append(f'  <memory id="{mem["id"]}" label="{mem["label"]}">')
            lines.append(f"    {mem['content']}")
            lines.append("  </memory>")
            
        lines.append("</memories>")
        return "\n".join(lines)
        
    def _format_markdown(self, memories: List[Dict[str, Any]]) -> str:
        """Markdown-style memory formatting."""
        lines = ["## Relevant Memories\n"]
        
        for i, mem in enumerate(memories, 1):
            lines.append(f"### {i}. {mem['label']}")
            lines.append(f"{mem['content']}\n")
            
        return "\n".join(lines)


class AgentMemoryExtension:
    """
    Full memory extension for AI agents.
    
    Provides:
    - Automatic memory retrieval
    - Experience capture
    - Insight generation
    - Context management
    """
    
    def __init__(self, agent_id: str, project_id: str,
                 memcube_url: str = "http://localhost:8002",
                 auto_store: bool = True):
        self.agent_id = agent_id
        self.project_id = project_id
        self.client = MemCubeClient(memcube_url)
        self.injector = MemoryInjector()
        self.auto_store = auto_store
        self._experience_buffer: List[Dict[str, Any]] = []
        
    async def __aenter__(self):
        await self.client.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Flush experience buffer if auto-store enabled
        if self.auto_store and self._experience_buffer:
            await self._flush_experiences()
            
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
        
    async def enhance_prompt(self, prompt: str, task_id: str,
                           tags: List[str] = None,
                           token_budget: int = 2000) -> str:
        """
        Enhance prompt with relevant memories.
        
        This is the main method agents call before LLM inference.
        """
        # Get relevant memories
        memories = await self.client.get_memories_for_task(
            agent_id=self.agent_id,
            task_id=task_id,
            project_id=self.project_id,
            tags=tags,
            token_budget=token_budget
        )
        
        # Inject into prompt
        enhanced = self.injector.inject_memories(prompt, memories)
        
        logger.info(f"Enhanced prompt with {len(memories)} memories for {self.agent_id}")
        return enhanced
        
    def capture_experience(self, label: str, content: str,
                         tags: List[str] = None,
                         immediate: bool = False):
        """
        Capture an experience for later storage.
        
        If immediate=True, stores immediately.
        Otherwise buffers for batch storage.
        """
        experience = {
            "label": label,
            "content": content,
            "tags": tags or [],
            "timestamp": datetime.utcnow()
        }
        
        if immediate:
            # Store immediately
            asyncio.create_task(self._store_experience(experience))
        else:
            # Buffer for later
            self._experience_buffer.append(experience)
            
    async def generate_insight(self, observation: str,
                             evidence: List[str] = None,
                             sentiment: float = 0.0) -> Optional[str]:
        """Generate and store an insight."""
        return await self.client.submit_insight(
            agent_id=self.agent_id,
            project_id=self.project_id,
            insight=observation,
            evidence=evidence,
            sentiment=sentiment
        )
        
    async def _store_experience(self, experience: Dict[str, Any]) -> Optional[str]:
        """Store a single experience."""
        return await self.client.store_experience(
            agent_id=self.agent_id,
            project_id=self.project_id,
            label=experience["label"],
            content=experience["content"],
            tags=experience["tags"]
        )
        
    async def _flush_experiences(self):
        """Flush all buffered experiences."""
        logger.info(f"Flushing {len(self._experience_buffer)} experiences for {self.agent_id}")
        
        tasks = [
            self._store_experience(exp)
            for exp in self._experience_buffer
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any failures
        failures = sum(1 for r in results if isinstance(r, Exception) or r is None)
        if failures:
            logger.warning(f"Failed to store {failures} experiences")
            
        # Clear buffer
        self._experience_buffer.clear()


class MemoryHooks:
    """
    Hooks for integrating memory operations into agent lifecycle.
    
    Can be attached to agent frameworks for automatic memory management.
    """
    
    def __init__(self, memory_extension: AgentMemoryExtension):
        self.memory = memory_extension
        
    async def pre_task_hook(self, task_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Hook to run before task execution."""
        # Enhance context with memories
        if "prompt" in context:
            context["prompt"] = await self.memory.enhance_prompt(
                context["prompt"],
                task_id,
                tags=context.get("tags", [])
            )
            
        return context
        
    async def post_task_hook(self, task_id: str, result: Any,
                           context: Dict[str, Any]) -> None:
        """Hook to run after task execution."""
        # Capture experience from result
        if isinstance(result, dict) and "learnings" in result:
            for learning in result["learnings"]:
                self.memory.capture_experience(
                    label=f"task_{task_id}_learning",
                    content=learning,
                    tags=["task_learning", task_id]
                )
                
    async def error_hook(self, task_id: str, error: Exception,
                       context: Dict[str, Any]) -> None:
        """Hook to run on task error."""
        # Store error as experience for learning
        self.memory.capture_experience(
            label=f"task_{task_id}_error",
            content=f"Error: {str(error)}\nContext: {json.dumps(context, indent=2)}",
            tags=["error", "learning", task_id],
            immediate=True
        )


def create_memory_agent(agent_class: type, **memory_kwargs) -> type:
    """
    Factory to create memory-enhanced agent classes.
    
    Usage:
        MemoryAgent = create_memory_agent(BaseAgent, project_id="my-project")
        agent = MemoryAgent()
    """
    
    class MemoryEnhancedAgent(agent_class):
        """Agent class with integrated memory support."""
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            
            # Initialize memory extension
            self.memory = AgentMemoryExtension(
                agent_id=getattr(self, "agent_id", self.__class__.__name__),
                **memory_kwargs
            )
            
            # Setup hooks if agent supports them
            if hasattr(self, "add_hook"):
                hooks = MemoryHooks(self.memory)
                self.add_hook("pre_task", hooks.pre_task_hook)
                self.add_hook("post_task", hooks.post_task_hook)
                self.add_hook("error", hooks.error_hook)
                
        async def __aenter__(self):
            await super().__aenter__()
            await self.memory.__aenter__()
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.memory.__aexit__(exc_type, exc_val, exc_tb)
            await super().__aexit__(exc_type, exc_val, exc_tb)
            
    return MemoryEnhancedAgent