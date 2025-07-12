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

"""Example of using the Control Plane Agent with policy enforcement."""

from google.adk.agents import LlmAgent
from google.adk.control_plane import (
    ControlPlaneAgent,
    ResourcePolicy,
    SecurityPolicy,
    CompliancePolicy,
)
from google.adk.tools import google_search, FunctionTool


# Define some example agents that will be managed by the control plane
data_analyst_agent = LlmAgent(
    name="data_analyst",
    model="gemini-2.0-flash",
    description="Analyzes data and generates insights",
    instruction="I analyze data and provide insights based on queries.",
    tools=[
        FunctionTool(
            name="query_database",
            description="Query the company database",
            func=lambda query: f"Results for: {query}",
        ),
    ],
)

web_researcher_agent = LlmAgent(
    name="web_researcher",
    model="gemini-2.0-flash",
    description="Researches information on the web",
    instruction="I search the web for information and summarize findings.",
    tools=[google_search],
)

# Create the control plane agent
control_plane = ControlPlaneAgent(
    name="control_plane",
    model="gemini-2.0-flash",
    description="Manages and governs other agents with policy enforcement",
    sub_agents=[data_analyst_agent, web_researcher_agent],
    enforce_policies=True,
    audit_all_actions=True,
)

# Define and register policies

# Resource access policy
resource_policy = ResourcePolicy(
    name="database_access_policy",
    description="Controls access to database resources",
    allowed_resources=["public_data/*", "analytics/*"],
    denied_resources=["sensitive_data/*", "*/pii/*"],
    max_resources_per_session=100,
)

# Security policy
security_policy = SecurityPolicy(
    name="agent_security_policy",
    description="Security controls for agent actions",
    require_authentication=True,
    allowed_actions=[
        "agent_invocation",
        "tool_call:google_search",
        "tool_call:query_database",
    ],
    denied_actions=["tool_call:delete_*", "tool_call:modify_*"],
    require_encryption=False,
)

# Compliance policy
compliance_policy = CompliancePolicy(
    name="data_compliance_policy",
    description="Ensures regulatory compliance",
    data_retention_days=90,
    require_audit_trail=True,
    pii_handling={
        "email": "encryption_required",
        "ssn": "access_denied",
        "credit_card": "tokenization_required",
    },
    geographic_restrictions=["US", "EU", "UK"],
)

# Register policies with the control plane
control_plane.register_policies([
    resource_policy,
    security_policy,
    compliance_policy,
])

# The control plane is now ready to use
# It will enforce all registered policies before allowing actions

# Example usage in agent.py:
root_agent = control_plane