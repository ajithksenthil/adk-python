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

"""Product & Experience Pillar - Discover, design, build, ship, document."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base import AgentRole, BusinessPillar, BusinessPillarAgent, PillarType, WorkflowResult, WorkflowStep

logger = logging.getLogger(__name__)


class MarketScout(BusinessPillarAgent):
  """Agent for market research and competitive analysis."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="market_scout",
      role=AgentRole.PLANNER,
      pillar=PillarType.PRODUCT_EXPERIENCE,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    """Setup market research tools."""
    self.register_tool("analyze_market_trends", self._analyze_market_trends, cost=2.0)
    self.register_tool("competitive_analysis", self._competitive_analysis, cost=1.5)
    self.register_tool("customer_feedback_analysis", self._customer_feedback_analysis, cost=1.0)
  
  async def _analyze_market_trends(self, market_segment: str) -> Dict[str, Any]:
    """Analyze market trends for a segment."""
    return {
      "segment": market_segment,
      "growth_rate": 12.5,
      "market_size": "1.2B",
      "key_trends": ["AI integration", "Mobile-first", "Privacy-focused"],
      "opportunities": ["Enterprise automation", "SMB market expansion"]
    }
  
  async def _competitive_analysis(self, competitors: List[str]) -> Dict[str, Any]:
    """Analyze competitors."""
    return {
      "competitors": competitors,
      "market_share": {"us": 0.15, "competitor_a": 0.25, "competitor_b": 0.18},
      "feature_gaps": ["Advanced analytics", "Mobile app"],
      "pricing_comparison": "competitive"
    }
  
  async def _customer_feedback_analysis(self, feedback_sources: List[str]) -> Dict[str, Any]:
    """Analyze customer feedback."""
    return {
      "sources": feedback_sources,
      "sentiment_score": 0.72,
      "top_requests": ["Better reporting", "API improvements", "Mobile access"],
      "pain_points": ["Slow performance", "Complex setup"]
    }
  
  async def execute_task(self, task: str, context: Dict[str, Any], workflow_id: Optional[str] = None) -> Dict[str, Any]:
    if task == "market_research":
      trends = await self._analyze_market_trends(context.get("segment", "enterprise"))
      competitive = await self._competitive_analysis(context.get("competitors", ["competitor_a", "competitor_b"]))
      feedback = await self._customer_feedback_analysis(context.get("sources", ["surveys", "support_tickets"]))
      
      return {
        "market_trends": trends,
        "competitive_analysis": competitive,
        "customer_feedback": feedback
      }
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    return ["market_analysis", "competitive_intelligence", "customer_research"]


class SpecWriter(BusinessPillarAgent):
  """Agent for writing product specifications."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="spec_writer",
      role=AgentRole.PLANNER,
      pillar=PillarType.PRODUCT_EXPERIENCE,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    """Setup specification writing tools."""
    self.register_tool("write_feature_spec", self._write_feature_spec, cost=2.0)
    self.register_tool("create_user_stories", self._create_user_stories, cost=1.0)
    self.register_tool("generate_acceptance_criteria", self._generate_acceptance_criteria, cost=0.8)
  
  async def _write_feature_spec(self, feature_name: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
    """Write detailed feature specification."""
    return {
      "feature_name": feature_name,
      "spec_id": f"SPEC-{uuid.uuid4().hex[:8]}",
      "overview": f"Detailed specification for {feature_name}",
      "requirements": requirements,
      "technical_approach": "RESTful API with React frontend",
      "success_metrics": ["User adoption > 60%", "Performance < 2s load time"],
      "created_at": datetime.now().isoformat()
    }
  
  async def _create_user_stories(self, epic: str) -> Dict[str, Any]:
    """Create user stories for an epic."""
    stories = [
      f"As a user, I want to {epic.lower()} so that I can improve productivity",
      f"As an admin, I want to configure {epic.lower()} so that I can control access"
    ]
    return {"epic": epic, "user_stories": stories}
  
  async def _generate_acceptance_criteria(self, user_story: str) -> Dict[str, Any]:
    """Generate acceptance criteria."""
    return {
      "user_story": user_story,
      "criteria": [
        "Given user is logged in, when they access feature, then they see interface",
        "Given valid input, when user submits, then system processes successfully"
      ]
    }
  
  async def execute_task(self, task: str, context: Dict[str, Any], workflow_id: Optional[str] = None) -> Dict[str, Any]:
    if task == "create_feature_spec":
      spec = await self._write_feature_spec(context["feature_name"], context.get("requirements", {}))
      stories = await self._create_user_stories(context["feature_name"])
      return {"specification": spec, "user_stories": stories}
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    return ["feature_specification", "user_story_creation", "requirements_analysis"]


class DevImplementer(BusinessPillarAgent):
  """Agent for development implementation."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="dev_implementer",
      role=AgentRole.WORKER,
      pillar=PillarType.PRODUCT_EXPERIENCE,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    """Setup development tools."""
    self.register_tool("create_code_implementation", self._create_code_implementation, cost=3.0)
    self.register_tool("run_tests", self._run_tests, cost=1.0)
    self.register_tool("create_pull_request", self._create_pull_request, cost=0.5)
  
  async def _create_code_implementation(self, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Create code implementation from spec."""
    return {
      "implementation_id": f"IMPL-{uuid.uuid4().hex[:8]}",
      "spec_id": spec.get("spec_id"),
      "code_files": ["feature.py", "feature.js", "feature.test.js"],
      "lines_of_code": 245,
      "complexity_score": "medium",
      "implemented_at": datetime.now().isoformat()
    }
  
  async def _run_tests(self, implementation_id: str) -> Dict[str, Any]:
    """Run tests for implementation."""
    return {
      "implementation_id": implementation_id,
      "test_results": {
        "total_tests": 15,
        "passed": 14,
        "failed": 1,
        "coverage": 0.87
      },
      "test_status": "mostly_passing"
    }
  
  async def _create_pull_request(self, implementation_id: str) -> Dict[str, Any]:
    """Create pull request for code review."""
    return {
      "pr_id": f"PR-{uuid.uuid4().hex[:6]}",
      "implementation_id": implementation_id,
      "status": "ready_for_review",
      "reviewers": ["senior_dev", "tech_lead"],
      "created_at": datetime.now().isoformat()
    }
  
  async def execute_task(self, task: str, context: Dict[str, Any], workflow_id: Optional[str] = None) -> Dict[str, Any]:
    if task == "implement_feature":
      impl = await self._create_code_implementation(context["spec"])
      tests = await self._run_tests(impl["implementation_id"])
      pr = await self._create_pull_request(impl["implementation_id"])
      return {"implementation": impl, "test_results": tests, "pull_request": pr}
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    return ["code_implementation", "testing", "code_review_preparation"]


class QACritic(BusinessPillarAgent):
  """Agent for quality assurance and testing."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="qa_critic",
      role=AgentRole.CRITIC,
      pillar=PillarType.PRODUCT_EXPERIENCE,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    """Setup QA tools."""
    self.register_tool("review_code_quality", self._review_code_quality, cost=1.5)
    self.register_tool("run_integration_tests", self._run_integration_tests, cost=2.0)
    self.register_tool("security_scan", self._security_scan, cost=1.0)
  
  async def _review_code_quality(self, pr_id: str) -> Dict[str, Any]:
    """Review code quality."""
    return {
      "pr_id": pr_id,
      "quality_score": 0.85,
      "issues_found": [
        {"type": "complexity", "severity": "medium", "file": "feature.py"},
        {"type": "documentation", "severity": "low", "file": "feature.js"}
      ],
      "recommendation": "approve_with_minor_changes"
    }
  
  async def _run_integration_tests(self, implementation_id: str) -> Dict[str, Any]:
    """Run integration tests."""
    return {
      "implementation_id": implementation_id,
      "integration_results": {
        "api_tests": "passed",
        "ui_tests": "passed",
        "performance_tests": "passed",
        "security_tests": "passed"
      },
      "overall_status": "passed"
    }
  
  async def _security_scan(self, implementation_id: str) -> Dict[str, Any]:
    """Run security scan."""
    return {
      "implementation_id": implementation_id,
      "vulnerabilities": [],
      "security_score": 0.95,
      "compliance_status": "compliant"
    }
  
  async def execute_task(self, task: str, context: Dict[str, Any], workflow_id: Optional[str] = None) -> Dict[str, Any]:
    if task == "quality_review":
      quality = await self._review_code_quality(context["pr_id"])
      integration = await self._run_integration_tests(context["implementation_id"])
      security = await self._security_scan(context["implementation_id"])
      return {"quality_review": quality, "integration_tests": integration, "security_scan": security}
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    return ["code_quality_review", "integration_testing", "security_scanning"]


class ProductExperiencePillar(BusinessPillar):
  """Product & Experience pillar coordinating product development."""
  
  def __init__(self, **kwargs):
    super().__init__(PillarType.PRODUCT_EXPERIENCE, **kwargs)
    self._setup_agents()
  
  def _setup_agents(self):
    """Setup all agents for this pillar."""
    self.register_agent(MarketScout(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    ))
    
    spec_writer = SpecWriter(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    )
    spec_writer.role = AgentRole.PLANNER  # Second planner
    self.register_agent(spec_writer)
    
    self.register_agent(DevImplementer(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    ))
    
    self.register_agent(QACritic(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    ))
  
  async def execute_workflow(self, workflow_type: str, inputs: Dict[str, Any], requester: Optional[str] = None) -> WorkflowResult:
    """Execute product development workflows."""
    workflow_id = f"product_{workflow_type}_{uuid.uuid4().hex[:8]}"
    workflow = WorkflowResult(workflow_id=workflow_id, pillar=self.pillar_type)
    
    if workflow_type == "feature_development":
      return await self._execute_feature_development_workflow(workflow, inputs)
    else:
      workflow.fail(f"Unknown workflow type: {workflow_type}")
      return workflow
  
  async def _execute_feature_development_workflow(self, workflow: WorkflowResult, inputs: Dict[str, Any]) -> WorkflowResult:
    """Execute end-to-end feature development."""
    try:
      # Step 1: Market research
      market_scout = self.get_agent(AgentRole.PLANNER)
      step1 = WorkflowStep(
        step_id="market_research",
        agent_role=AgentRole.PLANNER,
        action="market_research",
        inputs=inputs
      )
      step1.start()
      workflow.add_step(step1)
      
      research = await market_scout.execute_task("market_research", inputs, workflow.workflow_id)
      step1.complete(research)
      
      # Step 2: Create specification
      spec_writer = [agent for agent in self.agents.values() if agent.agent_id == "spec_writer"][0]
      step2 = WorkflowStep(
        step_id="create_spec",
        agent_role=AgentRole.PLANNER,
        action="create_feature_spec",
        inputs={"feature_name": inputs["feature_name"]}
      )
      step2.start()
      workflow.add_step(step2)
      
      spec = await spec_writer.execute_task("create_feature_spec", step2.inputs, workflow.workflow_id)
      step2.complete(spec)
      
      # Step 3: Implement feature
      dev_implementer = self.get_agent(AgentRole.WORKER)
      step3 = WorkflowStep(
        step_id="implement",
        agent_role=AgentRole.WORKER,
        action="implement_feature",
        inputs={"spec": spec["specification"]}
      )
      step3.start()
      workflow.add_step(step3)
      
      implementation = await dev_implementer.execute_task("implement_feature", step3.inputs, workflow.workflow_id)
      step3.complete(implementation)
      
      # Step 4: Quality review
      qa_critic = self.get_agent(AgentRole.CRITIC)
      step4 = WorkflowStep(
        step_id="quality_review",
        agent_role=AgentRole.CRITIC,
        action="quality_review",
        inputs={
          "pr_id": implementation["pull_request"]["pr_id"],
          "implementation_id": implementation["implementation"]["implementation_id"]
        }
      )
      step4.start()
      workflow.add_step(step4)
      
      qa_results = await qa_critic.execute_task("quality_review", step4.inputs, workflow.workflow_id)
      step4.complete(qa_results)
      
      workflow.complete({
        "market_research": research,
        "specification": spec,
        "implementation": implementation,
        "qa_results": qa_results
      })
      
    except Exception as e:
      workflow.fail(str(e))
    
    return workflow
  
  def get_workflow_types(self) -> List[str]:
    return ["feature_development"]