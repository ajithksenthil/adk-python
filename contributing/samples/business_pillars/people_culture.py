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

"""People & Culture Pillar - Recruit, onboard, grow, off-board."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import AgentRole, BusinessPillar, BusinessPillarAgent, PillarType, WorkflowResult, WorkflowStep


class TalentScout(BusinessPillarAgent):
  """Agent for talent acquisition and recruitment."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="talent_scout",
      role=AgentRole.PLANNER,
      pillar=PillarType.PEOPLE_CULTURE,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    self.register_tool("source_candidates", self._source_candidates, cost=1.0)
    self.register_tool("screen_candidate", self._screen_candidate, cost=0.8)
    self.register_tool("check_bias_score", self._check_bias_score, cost=0.5)
  
  async def _source_candidates(self, role: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
    return {
      "role": role,
      "candidates_found": 15,
      "qualified_candidates": 8,
      "diversity_metrics": {"gender_balance": 0.6, "ethnic_diversity": 0.4},
      "sourced_at": datetime.now().isoformat()
    }
  
  async def _screen_candidate(self, candidate_id: str) -> Dict[str, Any]:
    return {
      "candidate_id": candidate_id,
      "technical_score": 0.85,
      "cultural_fit_score": 0.78,
      "experience_match": 0.92,
      "overall_score": 0.85,
      "recommendation": "proceed_to_interview"
    }
  
  async def _check_bias_score(self, screening_process: Dict[str, Any]) -> Dict[str, Any]:
    # Bias evaluation per guardrails (≥ 0.9 required)
    return {
      "bias_score": 0.94,
      "meets_requirement": True,
      "bias_factors": {
        "gender_bias": 0.96,
        "ethnic_bias": 0.92,
        "age_bias": 0.95
      }
    }
  
  async def execute_task(self, task: str, context: Dict[str, Any], workflow_id: Optional[str] = None) -> Dict[str, Any]:
    if task == "recruit_for_role":
      sourcing = await self._source_candidates(context["role"], context.get("requirements", {}))
      screening = await self._screen_candidate(context.get("candidate_id", "cand_001"))
      bias_check = await self._check_bias_score({"process": "screening"})
      
      if not bias_check["meets_requirement"]:
        return {"success": False, "error": "Bias score below required threshold"}
      
      return {"sourcing": sourcing, "screening": screening, "bias_check": bias_check}
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    return ["candidate_sourcing", "bias_free_screening", "diversity_recruitment"]


class OnboardAgent(BusinessPillarAgent):
  """Agent for employee onboarding."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="onboard_agent",
      role=AgentRole.WORKER,
      pillar=PillarType.PEOPLE_CULTURE,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    self.register_tool("create_onboard_plan", self._create_onboard_plan, cost=1.0)
    self.register_tool("setup_accounts", self._setup_accounts, cost=0.5)
    self.register_tool("grant_iam_access", self._grant_iam_access, cost=0.8)
  
  async def _create_onboard_plan(self, employee_id: str, role: str) -> Dict[str, Any]:
    plan_id = f"ONBOARD-{uuid.uuid4().hex[:8]}"
    return {
      "plan_id": plan_id,
      "employee_id": employee_id,
      "role": role,
      "onboard_tasks": [
        "IT equipment setup",
        "Account provisioning",
        "Training modules",
        "Buddy assignment"
      ],
      "estimated_completion": "5 business days"
    }
  
  async def _setup_accounts(self, employee_id: str, role: str) -> Dict[str, Any]:
    return {
      "employee_id": employee_id,
      "accounts_created": ["email", "slack", "jira", "confluence"],
      "temporary_password": "temp_123",
      "mfa_required": True
    }
  
  async def _grant_iam_access(self, employee_id: str, role: str) -> Dict[str, Any]:
    # Role-based IAM granting per guardrails
    role_permissions = {
      "engineer": ["code_repos", "staging_env"],
      "manager": ["team_reports", "budget_view"],
      "admin": ["user_management", "system_config"]
    }
    
    permissions = role_permissions.get(role, ["basic_access"])
    
    return {
      "employee_id": employee_id,
      "role": role,
      "permissions_granted": permissions,
      "access_level": "role_based",
      "granted_at": datetime.now().isoformat()
    }
  
  async def execute_task(self, task: str, context: Dict[str, Any], workflow_id: Optional[str] = None) -> Dict[str, Any]:
    if task == "onboard_employee":
      plan = await self._create_onboard_plan(context["employee_id"], context["role"])
      accounts = await self._setup_accounts(context["employee_id"], context["role"])
      iam = await self._grant_iam_access(context["employee_id"], context["role"])
      
      return {"onboard_plan": plan, "account_setup": accounts, "iam_access": iam}
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    return ["onboarding_automation", "account_provisioning", "iam_management"]


class PulseSurveyor(BusinessPillarAgent):
  """Agent for employee engagement and surveys."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="pulse_surveyor",
      role=AgentRole.CRITIC,
      pillar=PillarType.PEOPLE_CULTURE,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    self.register_tool("create_pulse_survey", self._create_pulse_survey, cost=0.5)
    self.register_tool("analyze_responses", self._analyze_responses, cost=1.0)
    self.register_tool("recommend_actions", self._recommend_actions, cost=0.8)
  
  async def _create_pulse_survey(self, survey_type: str) -> Dict[str, Any]:
    survey_id = f"SURVEY-{uuid.uuid4().hex[:8]}"
    return {
      "survey_id": survey_id,
      "survey_type": survey_type,
      "questions": [
        "How satisfied are you with your role?",
        "Do you feel supported by your manager?",
        "Would you recommend this company as a place to work?"
      ],
      "target_audience": "all_employees",
      "duration": "2 weeks"
    }
  
  async def _analyze_responses(self, survey_id: str) -> Dict[str, Any]:
    return {
      "survey_id": survey_id,
      "response_rate": 0.78,
      "satisfaction_score": 4.2,  # out of 5
      "key_themes": ["workload", "communication", "growth_opportunities"],
      "sentiment": "positive"
    }
  
  async def _recommend_actions(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
    return {
      "survey_id": analysis["survey_id"],
      "recommendations": [
        "Implement flexible work arrangements",
        "Improve manager communication training",
        "Create more growth path clarity"
      ],
      "priority": "medium"
    }
  
  async def execute_task(self, task: str, context: Dict[str, Any], workflow_id: Optional[str] = None) -> Dict[str, Any]:
    if task == "conduct_pulse_survey":
      survey = await self._create_pulse_survey(context.get("survey_type", "quarterly"))
      analysis = await self._analyze_responses(survey["survey_id"])
      recommendations = await self._recommend_actions(analysis)
      
      return {"survey": survey, "analysis": analysis, "recommendations": recommendations}
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    return ["employee_surveys", "engagement_analysis", "culture_insights"]


class PeopleCulturePillar(BusinessPillar):
  """People & Culture pillar coordinating HR and talent management."""
  
  def __init__(self, **kwargs):
    super().__init__(PillarType.PEOPLE_CULTURE, **kwargs)
    self._setup_agents()
  
  def _setup_agents(self):
    """Setup all agents for this pillar."""
    self.register_agent(TalentScout(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    ))
    
    self.register_agent(OnboardAgent(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    ))
    
    self.register_agent(PulseSurveyor(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    ))
  
  async def execute_workflow(self, workflow_type: str, inputs: Dict[str, Any], requester: Optional[str] = None) -> WorkflowResult:
    """Execute HR workflows."""
    workflow_id = f"people_{workflow_type}_{uuid.uuid4().hex[:8]}"
    workflow = WorkflowResult(workflow_id=workflow_id, pillar=self.pillar_type)
    
    if workflow_type == "hire_to_onboard":
      return await self._execute_hire_to_onboard_workflow(workflow, inputs)
    else:
      workflow.fail(f"Unknown workflow type: {workflow_type}")
      return workflow
  
  async def _execute_hire_to_onboard_workflow(self, workflow: WorkflowResult, inputs: Dict[str, Any]) -> WorkflowResult:
    """Execute hire to onboard workflow."""
    try:
      # Step 1: Recruit
      talent_scout = self.get_agent(AgentRole.PLANNER)
      step1 = WorkflowStep(
        step_id="recruit",
        agent_role=AgentRole.PLANNER,
        action="recruit_for_role",
        inputs=inputs
      )
      step1.start()
      workflow.add_step(step1)
      
      recruitment = await talent_scout.execute_task("recruit_for_role", inputs, workflow.workflow_id)
      step1.complete(recruitment)
      
      # Step 2: Onboard
      onboard_agent = self.get_agent(AgentRole.WORKER)
      step2 = WorkflowStep(
        step_id="onboard",
        agent_role=AgentRole.WORKER,
        action="onboard_employee",
        inputs=inputs
      )
      step2.start()
      workflow.add_step(step2)
      
      onboarding = await onboard_agent.execute_task("onboard_employee", inputs, workflow.workflow_id)
      step2.complete(onboarding)
      
      workflow.complete({
        "recruitment": recruitment,
        "onboarding": onboarding
      })
      
    except Exception as e:
      workflow.fail(str(e))
    
    return workflow
  
  def get_workflow_types(self) -> List[str]:
    return ["hire_to_onboard"]