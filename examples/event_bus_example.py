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

"""Example of using Event Bus for multi-agent communication."""

from google.adk.event_bus import (
    EventBusAgent,
    InMemoryEventBus,
    KafkaEventBus,
)
from google.adk.tools import FunctionTool

# Example 1: Create event bus (in-memory for development)
event_bus = InMemoryEventBus()

# For production, use Kafka:
# event_bus = KafkaEventBus(
#     bootstrap_servers="localhost:9092",
#     client_id="adk-agents",
#     group_id="agent-group",
# )

# Example 2: Create specialized agents that communicate via events

# Data processing agent
data_processor = EventBusAgent(
    name="data_processor",
    model="gemini-2.0-flash",
    description="Processes data and publishes results",
    event_bus=event_bus,
    agent_topics=["data.requests", "agent.data_processor"],
    publish_topics=["data.results", "processing.status"],
    instruction=(
        "I process data requests and publish results via the event bus. "
        "I can handle batch processing and real-time data streams."
    ),
    tools=[
        FunctionTool(
            name="process_data",
            description="Process incoming data",
            func=lambda data: {"processed": True, "record_count": len(data)},
        ),
    ],
)

# Analytics agent
analytics_agent = EventBusAgent(
    name="analytics",
    model="gemini-2.0-flash",
    description="Performs analytics on processed data",
    event_bus=event_bus,
    agent_topics=["data.results", "agent.analytics"],
    publish_topics=["analytics.insights", "analytics.reports"],
    instruction=(
        "I analyze processed data and generate insights. I subscribe to "
        "data results and publish analytical insights."
    ),
    tools=[
        FunctionTool(
            name="analyze_trends",
            description="Analyze data trends",
            func=lambda data: {
                "trend": "increasing",
                "confidence": 0.85,
                "key_metrics": {"growth": 15.5, "volatility": 0.23},
            },
        ),
    ],
)

# Notification agent
notification_agent = EventBusAgent(
    name="notifier",
    model="gemini-2.0-flash",
    description="Sends notifications based on events",
    event_bus=event_bus,
    agent_topics=["analytics.insights", "processing.status", "agent.broadcast"],
    publish_topics=["notifications.sent"],
    instruction=(
        "I monitor events and send notifications for important updates. "
        "I can filter events by priority and send alerts accordingly."
    ),
    tools=[
        FunctionTool(
            name="send_notification",
            description="Send notification to users",
            func=lambda message, priority: {
                "sent": True,
                "recipients": 10,
                "priority": priority,
            },
        ),
    ],
)

# Example 3: Coordinator agent that orchestrates workflows
coordinator = EventBusAgent(
    name="workflow_coordinator",
    model="gemini-2.0-flash",
    description="Coordinates multi-agent workflows",
    event_bus=event_bus,
    agent_topics=["coordination.all", "agent.workflow_coordinator"],
    publish_topics=["coordination.all", "workflow.status"],
    instruction=(
        "I coordinate complex workflows across multiple agents. I can "
        "assign tasks, monitor progress, and ensure workflows complete."
    ),
    sub_agents=[data_processor, analytics_agent, notification_agent],
)

# Example 4: Custom event handlers
async def handle_critical_event(event):
    """Custom handler for critical events."""
    print(f"CRITICAL EVENT: {event.event_type} from {event.source}")
    print(f"Payload: {event.payload}")

# Add custom handler to notification agent
notification_agent.event_handlers["alert.critical"] = handle_critical_event

# Example 5: Event-driven workflow
# This shows how agents can work together via events:
# 1. Data arrives -> data_processor handles it
# 2. Processed data -> analytics_agent analyzes it
# 3. Insights generated -> notification_agent alerts users
# 4. Coordinator monitors the entire flow

# The agents can now:
# - Publish events to notify others of state changes
# - Subscribe to relevant events from other agents
# - Implement request-reply patterns for direct communication
# - Coordinate complex multi-step workflows
# - Scale horizontally by adding more agents to topics

# Usage in agent.py:
root_agent = coordinator  # Use coordinator as the main entry point