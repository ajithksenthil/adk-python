# ADK Control Plane OPA Policies
# 
# This file contains example OPA (Open Policy Agent) policies for the
# ADK Control Plane. These policies are evaluated when agents attempt
# to execute tools.

package adk.authz

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# Default deny
default allow = false

# Main authorization rule
allow = true if {
    # All checks must pass
    budget_check
    autonomy_check
    compliance_check
    time_window_check
    not security_violation
}

# Require approval for certain conditions
require_approval = true if {
    high_cost_operation
}

require_approval = true if {
    sensitive_operation
}

require_approval = true if {
    low_autonomy_sensitive_tool
}

# Budget checks
budget_check = true if {
    input.cost_estimate <= max_transaction_amount[input.autonomy_level]
}

budget_check = true if {
    input.cost_estimate == null
}

max_transaction_amount = {
    0: 0,      # AML 0: No transactions
    1: 10,     # AML 1: $10 max
    2: 100,    # AML 2: $100 max
    3: 1000,   # AML 3: $1,000 max
    4: 10000,  # AML 4: $10,000 max
    5: 100000, # AML 5: $100,000 max
}

high_cost_operation = true if {
    input.cost_estimate > 500
}

# Autonomy level checks
autonomy_check = true if {
    tool_allowed_at_level[input.tool][input.autonomy_level]
}

autonomy_check = true if {
    input.tool == null
}

# Define which tools are allowed at each autonomy level
tool_allowed_at_level = {
    "analyze_data": {0: true, 1: true, 2: true, 3: true, 4: true, 5: true},
    "generate_report": {0: true, 1: true, 2: true, 3: true, 4: true, 5: true},
    "send_email": {0: false, 1: false, 2: true, 3: true, 4: true, 5: true},
    "execute_trade": {0: false, 1: false, 2: false, 3: false, 4: true, 5: true},
    "modify_database": {0: false, 1: false, 2: false, 3: true, 4: true, 5: true},
}

sensitive_operation = true if {
    input.tool in ["execute_trade", "modify_database"]
}

low_autonomy_sensitive_tool = true if {
    sensitive_operation
    input.autonomy_level < 4
}

# Compliance checks
compliance_check = true if {
    required_tags_present
    data_residency_compliant
}

required_tags = ["reviewed", "approved", "compliant"]

required_tags_present = true if {
    tags := input.metadata.tags
    all_present := [tag | tag := required_tags[_]; tag in tags]
    count(all_present) == count(required_tags)
}

required_tags_present = true if {
    input.metadata.tags == null
}

data_residency_compliant = true if {
    # Check if data location is specified and compliant
    location := input.metadata.data_location
    location in allowed_data_locations
}

data_residency_compliant = true if {
    input.metadata.data_location == null
}

allowed_data_locations = ["us-east1", "us-west1", "eu-west1", "eu-central1"]

# Time window checks (business hours, maintenance windows)
time_window_check = true if {
    not maintenance_window
    business_hours_check
}

maintenance_window = true if {
    # Every Sunday 2-4 AM UTC
    time.weekday(time.now_ns()) == 0  # Sunday
    hour := time.clock(time.now_ns())[0]
    hour >= 2
    hour < 4
}

business_hours_check = true if {
    # High-risk operations only during business hours
    not sensitive_operation
}

business_hours_check = true if {
    sensitive_operation
    hour := time.clock(time.now_ns())[0]
    hour >= 9
    hour <= 17
    time.weekday(time.now_ns()) >= 1  # Monday
    time.weekday(time.now_ns()) <= 5  # Friday
}

# Security violations
security_violation = true if {
    contains(input.parameters.query, "DROP TABLE")
}

security_violation = true if {
    contains(input.parameters.query, "DELETE FROM")
    not input.metadata.delete_authorized
}

security_violation = true if {
    input.tool == "execute_trade"
    input.parameters.quantity > 10000
    not input.metadata.large_trade_authorized
}

# Pillar-specific rules
pillar_rules[pillar] = rules if {
    pillar := input.metadata.pillar
    rules := pillar_specific_rules[pillar]
}

pillar_specific_rules = {
    "Mission & Governance": {
        "max_daily_spend": 100,
        "requires_dual_approval": true,
        "allowed_tools": ["analyze_data", "generate_report"],
    },
    "Growth Engine": {
        "max_daily_spend": 1000,
        "campaign_limit": 500,
        "allowed_channels": ["Google", "Facebook", "LinkedIn"],
    },
    "Customer Success": {
        "max_refund": 100,
        "max_daily_refunds": 500,
        "escalation_threshold": 50,
    },
    "Platform & Infra": {
        "max_instances": 100,
        "allowed_regions": ["us-east1", "us-west1"],
        "require_change_request": true,
    },
}

# Generate detailed reasons for denials
reasons[msg] {
    not budget_check
    msg := sprintf("Budget check failed: cost $%.2f exceeds limit for AML %d", [input.cost_estimate, input.autonomy_level])
}

reasons[msg] {
    not autonomy_check
    msg := sprintf("Tool '%s' not allowed at autonomy level %d", [input.tool, input.autonomy_level])
}

reasons[msg] {
    not compliance_check
    not required_tags_present
    msg := "Missing required compliance tags"
}

reasons[msg] {
    maintenance_window
    msg := "Operation blocked during maintenance window"
}

reasons[msg] {
    security_violation
    msg := "Security policy violation detected"
}

# Output decision
decision = {
    "allow": allow,
    "require_approval": require_approval,
    "reasons": reasons,
    "metadata": {
        "evaluated_at": time.now_ns(),
        "autonomy_level": input.autonomy_level,
        "pillar": input.metadata.pillar,
    },
}