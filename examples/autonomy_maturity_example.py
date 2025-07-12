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

"""Example of using the Autonomy Maturity Level framework."""

from google.adk.autonomy_maturity import (
    AdaptiveAutonomyAgent,
    AutonomyLevel,
    MaturityEvaluator,
    MaturityFramework,
)
from google.adk.tools import google_search, FunctionTool

# Example 1: Create an adaptive agent that starts at Level 1
assistant_agent = AdaptiveAutonomyAgent(
    name="adaptive_assistant",
    model="gemini-2.0-flash",
    description="An assistant that adapts its autonomy based on performance",
    current_autonomy_level=AutonomyLevel.LEVEL_1_ASSISTED,
    target_autonomy_level=AutonomyLevel.LEVEL_4_HIGH,
    allow_dynamic_adjustment=True,
    tools=[
        google_search,
        FunctionTool(
            name="execute_task",
            description="Execute a task (requires appropriate autonomy level)",
            func=lambda task: f"Executing: {task}",
        ),
    ],
)

# Example 2: Set initial performance metrics
assistant_agent.update_performance_metrics(
    "decision_making",
    {
        "decision_accuracy": 85.0,
        "decision_complexity": 2.5,
        "autonomy_percentage": 30.0,
    },
)

assistant_agent.update_performance_metrics(
    "learning_capability",
    {
        "learning_rate": 0.6,
        "knowledge_retention": 90.0,
    },
)

assistant_agent.update_performance_metrics(
    "error_handling",
    {
        "error_recovery_rate": 70.0,
        "mean_time_to_recovery": 300.0,  # 5 minutes
    },
)

# Example 3: Create a custom agent with specific autonomy requirements
customer_service_agent = AdaptiveAutonomyAgent(
    name="customer_service",
    model="gemini-2.0-flash",
    description="Customer service agent with graduated autonomy",
    current_autonomy_level=AutonomyLevel.LEVEL_2_PARTIAL,
    target_autonomy_level=AutonomyLevel.LEVEL_3_CONDITIONAL,
    allow_dynamic_adjustment=True,
    # Define what requires approval at each level
    approval_required_actions=[
        "process_refund",
        "modify_order",
        "access_sensitive_data",
    ],
    tools=[
        FunctionTool(
            name="lookup_order",
            description="Look up customer order",
            func=lambda order_id: {"order_id": order_id, "status": "shipped"},
        ),
        FunctionTool(
            name="process_refund",
            description="Process a refund (requires approval at lower levels)",
            func=lambda order_id, amount: {
                "order_id": order_id,
                "refund_amount": amount,
                "status": "pending_approval",
            },
        ),
    ],
)

# Example 4: Evaluate maturity and generate roadmap
evaluator = MaturityEvaluator()

# Perform assessment
performance_data = {
    "decision_making": {
        "decision_accuracy": 75.0,
        "decision_complexity": 3.0,
        "autonomy_percentage": 50.0,
    },
    "learning_capability": {
        "learning_rate": 0.4,
        "knowledge_retention": 80.0,
    },
    "error_handling": {
        "error_recovery_rate": 60.0,
        "mean_time_to_recovery": 600.0,
    },
}

assessment = evaluator.evaluate_agent(
    customer_service_agent,
    performance_data,
    target_level=AutonomyLevel.LEVEL_4_HIGH,
)

# The assessment provides:
# - Current maturity level
# - Scores for each dimension
# - Identified gaps
# - Recommendations for improvement
# - Roadmap to reach target level

# Example 5: Different autonomy levels for different contexts
context_aware_agent = AdaptiveAutonomyAgent(
    name="context_aware",
    model="gemini-2.0-flash",
    description="Agent that adjusts autonomy based on risk and context",
    current_autonomy_level=AutonomyLevel.LEVEL_3_CONDITIONAL,
    target_autonomy_level=AutonomyLevel.LEVEL_5_FULL,
    allow_dynamic_adjustment=True,
)

# The agent can:
# 1. Operate at Level 3 for normal operations
# 2. Drop to Level 2 for high-risk situations
# 3. Advance to Level 4 for well-understood tasks
# 4. Track its progress toward Level 5 full autonomy

# Usage in agent.py:
root_agent = assistant_agent  # or any of the other configured agents