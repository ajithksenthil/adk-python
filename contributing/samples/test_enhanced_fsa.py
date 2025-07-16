#!/usr/bin/env python3
"""Test the enhanced FSA memory system with comprehensive state and comments."""

import asyncio
import time
import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SMS_URL = "http://localhost:8000"
TEST_TENANT = "acme-corp"
TEST_FSA_ID = "project-alpha-2024"


class EnhancedFSATestRunner:
    """Tests for enhanced FSA features."""
    
    async def setup_comprehensive_state(self):
        """Set up a comprehensive project state."""
        logger.info("\n=== Setting Up Comprehensive Project State ===")
        
        initial_state = {
            # What are we doing?
            "tasks": {
                "DESIGN_LANDING_PAGE": {
                    "task_id": "DESIGN_LANDING_PAGE",
                    "status": "RUNNING",
                    "assigned_team": "alice/frontend",
                    "depends_on": [],
                    "created_at": datetime.utcnow().isoformat()
                },
                "IMPLEMENT_API": {
                    "task_id": "IMPLEMENT_API",
                    "status": "PENDING",
                    "assigned_team": "bob/backend",
                    "depends_on": ["DESIGN_LANDING_PAGE"],
                    "created_at": datetime.utcnow().isoformat()
                },
                "WRITE_COPY": {
                    "task_id": "WRITE_COPY",
                    "status": "VOTING",
                    "assigned_team": "eva/marketing",
                    "depends_on": [],
                    "created_at": datetime.utcnow().isoformat()
                }
            },
            
            # Where are we?
            "active_state": {
                "current_sprint": "Sprint-31",
                "milestone_id": 7,
                "phase": "MVP Development",
                "target_launch": "2024-08-15"
            },
            
            # What do we have?
            "artefacts": {
                "landing_page_url": "https://staging.acme.com/new-product",
                "api_spec_doc": "docs/api-v2-spec.md",
                "commit_sha": "abc123def456",
                "ad_creative_ids": ["cr_001", "cr_002", "cr_003"]
            },
            
            "resources": {
                "cash_balance_usd": 125435.22,
                "cloud_credits": 5000,
                "inventory": {
                    "servers": 15,
                    "licenses": 100
                },
                "team_capacity": {
                    "frontend": 0.8,
                    "backend": 1.0,
                    "marketing": 0.6
                }
            },
            
            # How are we doing?
            "metrics": {
                "ctr_last_24h": 2.7,
                "conversion_rate": 0.045,
                "nps_score": 72,
                "page_load_time_ms": 1250,
                "api_response_time_p99": 450,
                "daily_active_users": 5420
            },
            
            # What rules apply?
            "policy_caps": {
                "max_po_per_day": 10000,
                "refund_limit": 100,
                "api_rate_limit": 1000,
                "max_team_size": 50,
                "budget_variance_allowed": 0.1
            },
            
            "aml_levels": {
                "growth_engine": 3,
                "customer_success": 2,
                "product_development": 4,
                "finance_ops": 1
            },
            
            "vote_rules": {
                "default": "2_of_5_core",
                "high_cost": "3_of_5_core+treasurer",
                "architecture_change": "unanimous_tech_leads",
                "customer_impact": "include_cs_team"
            },
            
            # When do things happen?
            "timers": {
                "next_sprint_planning": (datetime.utcnow() + timedelta(days=3)).isoformat(),
                "quarterly_review": (datetime.utcnow() + timedelta(days=45)).isoformat(),
                "ssl_cert_expiry": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                "contract_renewal": (datetime.utcnow() + timedelta(days=60)).isoformat()
            },
            
            # Who is available?
            "agents_online": {
                "alice/frontend": datetime.utcnow().isoformat(),
                "bob/backend": datetime.utcnow().isoformat(),
                "eva/marketing": (datetime.utcnow() - timedelta(minutes=10)).isoformat(),
                "dave/devops": datetime.utcnow().isoformat()
            }
        }
        
        resp = requests.post(
            f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}",
            json=initial_state,
            params={"actor": "system", "lineage_id": "setup-001"}
        )
        
        assert resp.status_code == 200
        result = resp.json()
        logger.info(f"✅ Comprehensive state initialized, version: {result['version']}")
        
        # Get summary
        resp = requests.get(
            f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}",
            params={"summary": True}
        )
        summary_data = resp.json()
        logger.info(f"\n📄 State Summary:\n{summary_data['summary']}")
        
    async def test_task_management(self):
        """Test task status updates and dependencies."""
        logger.info("\n=== Testing Task Management ===")
        
        # Complete the landing page design
        delta = {
            "tasks.DESIGN_LANDING_PAGE.status": "COMPLETED",
            "tasks.DESIGN_LANDING_PAGE.updated_at": datetime.utcnow().isoformat(),
            "artefacts.design_mockups": ["mockup_v1.fig", "mockup_v2.fig"]
        }
        
        resp = requests.post(
            f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}/delta",
            json=delta,
            params={
                "actor": "alice/frontend",
                "lineage_id": "complete-design-001",
                "pillar": "product_development",
                "aml_level": 4
            }
        )
        
        assert resp.status_code == 200
        result = resp.json()
        assert result["success"]
        logger.info("✅ Landing page design completed")
        
        # Now API implementation can start
        delta2 = {
            "tasks.IMPLEMENT_API.status": "RUNNING",
            "tasks.IMPLEMENT_API.updated_at": datetime.utcnow().isoformat()
        }
        
        resp = requests.post(
            f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}/delta",
            json=delta2,
            params={
                "actor": "bob/backend",
                "lineage_id": "start-api-001",
                "pillar": "product_development",
                "aml_level": 4
            }
        )
        
        assert resp.json()["success"]
        logger.info("✅ API implementation started")
        
    async def test_resource_management(self):
        """Test resource updates with policy enforcement."""
        logger.info("\n=== Testing Resource Management ===")
        
        # Try to spend beyond daily limit (should fail)
        bad_delta = {
            "resources.cash_balance_usd": {"$inc": -15000}
        }
        
        resp = requests.post(
            f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}/delta",
            json=bad_delta,
            params={
                "actor": "junior_buyer",
                "lineage_id": "overspend-001",
                "pillar": "finance_ops",
                "aml_level": 1
            }
        )
        
        result = resp.json()
        assert not result["success"]
        assert "AML" in result["message"]
        logger.info(f"✅ Policy correctly blocked overspending: {result['message']}")
        
        # Approved spending within limits
        good_delta = {
            "resources.cash_balance_usd": {"$inc": -2500},
            "resources.cloud_credits": {"$inc": -500},
            "metrics.infrastructure_cost": 2500
        }
        
        resp = requests.post(
            f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}/delta",
            json=good_delta,
            params={
                "actor": "dave/devops",
                "lineage_id": "infra-spend-001",
                "pillar": "product_development",
                "aml_level": 3
            }
        )
        
        assert resp.json()["success"]
        logger.info("✅ Approved infrastructure spending processed")
        
    async def test_comment_system(self):
        """Test task comment threads."""
        logger.info("\n=== Testing Comment System ===")
        
        task_id = "WRITE_COPY"
        
        # Add comments from different sources
        comments = [
            {
                "author": "eva/marketing",
                "body": "We need to A/B test the hero copy. Current version might be too technical.",
                "lineage_id": "comment-001"
            },
            {
                "author": "alice/frontend",
                "body": "Agreed. I can set up the A/B test framework by Friday.",
                "lineage_id": "comment-002"
            },
            {
                "author": "CopyOptimizer/agent",
                "body": "Analysis complete. Variant B with simpler language shows 15% better engagement in similar campaigns.",
                "lineage_id": "agent-analysis-001"
            },
            {
                "author": "bob/backend",
                "body": "@blocker - Need API endpoints for A/B test assignment first",
                "lineage_id": "comment-003",
                "is_blocker": True
            }
        ]
        
        for comment in comments:
            resp = requests.post(
                f"{SMS_URL}/tasks/{TEST_TENANT}/{TEST_FSA_ID}/{task_id}/comment",
                params=comment
            )
            assert resp.status_code == 200
            result = resp.json()
            assert result["success"]
            logger.info(f"✅ Comment added by {comment['author']}")
            time.sleep(0.1)  # Small delay to ensure ordering
        
        # Retrieve comments
        resp = requests.get(
            f"{SMS_URL}/tasks/{TEST_TENANT}/{TEST_FSA_ID}/{task_id}/comments",
            params={"limit": 10}
        )
        
        comment_data = resp.json()
        assert len(comment_data["comments"]) == 4
        
        logger.info(f"\n💬 Task Comment Thread ({len(comment_data['comments'])} comments):")
        for comment in reversed(comment_data["comments"]):  # Show in chronological order
            author = comment["author"]
            body = comment["body_md"]
            blocker = "🚫 " if comment.get("is_blocker") else ""
            logger.info(f"  {blocker}[{author}]: {body}")
        
    async def test_agent_coordination(self):
        """Test multi-agent coordination through shared state."""
        logger.info("\n=== Testing Agent Coordination ===")
        
        # Agent 1: Marketing bot updates metrics
        delta1 = {
            "metrics.ctr_last_24h": 3.2,
            "metrics.conversion_rate": 0.052,
            "metrics.campaign_impressions": 125000
        }
        
        resp = requests.post(
            f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}/delta",
            json=delta1,
            params={
                "actor": "MetricsCollector/agent",
                "lineage_id": "metrics-update-001",
                "pillar": "growth_engine",
                "aml_level": 3
            }
        )
        assert resp.json()["success"]
        logger.info("✅ Marketing metrics updated by MetricsCollector")
        
        # Agent 2: Optimizer bot sees improved metrics and adjusts budget
        delta2 = {
            "resources.marketing_budget": {"$inc": 1000},
            "policy_caps.daily_ad_spend": 2500,
            "active_state.optimization_notes": "CTR improved 18%, increasing budget allocation"
        }
        
        resp = requests.post(
            f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}/delta",
            json=delta2,
            params={
                "actor": "BudgetOptimizer/agent",
                "lineage_id": "budget-adjust-001",
                "pillar": "growth_engine",
                "aml_level": 3
            }
        )
        assert resp.json()["success"]
        logger.info("✅ Budget optimized based on performance metrics")
        
        # Agent 3: Scheduler bot sets up next review
        next_review = datetime.utcnow() + timedelta(hours=6)
        delta3 = {
            "timers.next_budget_review": next_review.isoformat(),
            "tasks.REVIEW_CAMPAIGN_PERFORMANCE": {
                "task_id": "REVIEW_CAMPAIGN_PERFORMANCE",
                "status": "PENDING",
                "assigned_team": "analytics/team",
                "deadline": next_review.isoformat()
            }
        }
        
        resp = requests.post(
            f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}/delta",
            json=delta3,
            params={
                "actor": "TaskScheduler/agent",
                "lineage_id": "schedule-review-001",
                "pillar": "platform_infrastructure",
                "aml_level": 4
            }
        )
        assert resp.json()["success"]
        logger.info("✅ Review task scheduled for 6 hours from now")
        
    async def test_voting_scenario(self):
        """Test voting workflow with comments."""
        logger.info("\n=== Testing Voting Workflow ===")
        
        # Create a high-impact task requiring vote
        task_id = "MAJOR_REFACTOR"
        delta = {
            f"tasks.{task_id}": {
                "task_id": task_id,
                "status": "VOTING",
                "assigned_team": "tech_leads",
                "description": "Refactor core authentication system",
                "impact": "high",
                "estimated_hours": 120
            }
        }
        
        resp = requests.post(
            f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}/delta",
            json=delta,
            params={
                "actor": "ArchitectureBot/agent",
                "lineage_id": "propose-refactor-001",
                "pillar": "product_development",
                "aml_level": 2  # Can only propose, not execute
            }
        )
        assert resp.json()["success"]
        logger.info("✅ Major refactor proposed, entering voting phase")
        
        # Stakeholders comment
        votes = [
            ("alice/frontend", "👍 Needed for scaling. I can help with UI auth components.", False),
            ("bob/backend", "👍 Current system has security issues. This is overdue.", False),
            ("dave/devops", "⚠️ Need to plan zero-downtime migration carefully.", True),
            ("SecurityAuditor/agent", "✅ Security scan confirms vulnerabilities in current system.", False)
        ]
        
        for author, body, is_blocker in votes:
            resp = requests.post(
                f"{SMS_URL}/tasks/{TEST_TENANT}/{TEST_FSA_ID}/{task_id}/comment",
                params={
                    "author": author,
                    "body": body,
                    "lineage_id": f"vote-{author}",
                    "is_blocker": is_blocker
                }
            )
            assert resp.json()["success"]
        
        logger.info("✅ Voting comments recorded")
        
        # Check if we can proceed (would be done by Governance Bot)
        resp = requests.get(f"{SMS_URL}/tasks/{TEST_TENANT}/{TEST_FSA_ID}/{task_id}/comments")
        comments = resp.json()["comments"]
        
        blockers = [c for c in comments if c.get("is_blocker")]
        approvals = [c for c in comments if "👍" in c["body_md"]]
        
        logger.info(f"📊 Vote tally: {len(approvals)} approvals, {len(blockers)} blockers")
        
    async def test_heartbeat_monitoring(self):
        """Test agent heartbeat monitoring."""
        logger.info("\n=== Testing Agent Heartbeat Monitoring ===")
        
        agents = ["alice/frontend", "bob/backend", "MetricsCollector/agent", "TaskScheduler/agent"]
        
        # Update heartbeats
        for agent in agents:
            resp = requests.post(
                f"{SMS_URL}/agents/{TEST_TENANT}/{TEST_FSA_ID}/{agent}/heartbeat"
            )
            assert resp.status_code == 200
            logger.info(f"💓 Heartbeat updated: {agent}")
        
        # Check who's online
        resp = requests.get(f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}")
        state = resp.json()
        
        agents_online = state["agents_online"]
        logger.info(f"\n🟢 Agents Online ({len(agents_online)}):")
        
        now = datetime.utcnow()
        for agent, last_seen_str in agents_online.items():
            last_seen = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00'))
            delta = (now - last_seen.replace(tzinfo=None)).total_seconds()
            status = "🟢" if delta < 300 else "🟡" if delta < 600 else "🔴"
            logger.info(f"  {status} {agent} - last seen {int(delta)}s ago")
    
    async def show_final_summary(self):
        """Display comprehensive final state."""
        logger.info("\n=== Final Project State Summary ===")
        
        resp = requests.get(f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}")
        state = resp.json()
        
        logger.info(f"\n📊 Project Dashboard")
        logger.info(f"Version: {state.get('lineage_version', 'N/A')}")
        
        # Active state
        active = state.get("active_state", {})
        logger.info(f"\n📍 Current Position:")
        logger.info(f"  Sprint: {active.get('current_sprint')}")
        logger.info(f"  Milestone: {active.get('milestone_id')}")
        logger.info(f"  Phase: {active.get('phase')}")
        
        # Task summary
        tasks = state.get("tasks", {})
        task_summary = {}
        for task in tasks.values():
            status = task.get("status", "UNKNOWN")
            task_summary[status] = task_summary.get(status, 0) + 1
        
        logger.info(f"\n📋 Tasks:")
        for status, count in task_summary.items():
            logger.info(f"  {status}: {count}")
        
        # Resources
        resources = state.get("resources", {})
        logger.info(f"\n💰 Resources:")
        logger.info(f"  Cash: ${resources.get('cash_balance_usd', 0):,.2f}")
        logger.info(f"  Cloud Credits: {resources.get('cloud_credits', 0)}")
        
        # Key metrics
        metrics = state.get("metrics", {})
        logger.info(f"\n📈 Key Metrics:")
        logger.info(f"  CTR: {metrics.get('ctr_last_24h', 0)}%")
        logger.info(f"  Conversion: {metrics.get('conversion_rate', 0)*100:.2f}%")
        logger.info(f"  NPS: {metrics.get('nps_score', 0)}")
        logger.info(f"  DAU: {metrics.get('daily_active_users', 0):,}")
        
        # AML levels
        aml = state.get("aml_levels", {})
        logger.info(f"\n🔒 Autonomy Levels:")
        for pillar, level in aml.items():
            logger.info(f"  {pillar}: AML {level}")
    
    async def run_all_tests(self):
        """Run all enhanced FSA tests."""
        logger.info("🚀 Starting Enhanced FSA Integration Tests")
        logger.info("=" * 60)
        
        try:
            await self.setup_comprehensive_state()
            await asyncio.sleep(0.5)
            
            await self.test_task_management()
            await asyncio.sleep(0.5)
            
            await self.test_resource_management()
            await asyncio.sleep(0.5)
            
            await self.test_comment_system()
            await asyncio.sleep(0.5)
            
            await self.test_agent_coordination()
            await asyncio.sleep(0.5)
            
            await self.test_voting_scenario()
            await asyncio.sleep(0.5)
            
            await self.test_heartbeat_monitoring()
            await asyncio.sleep(0.5)
            
            await self.show_final_summary()
            
            logger.info("\n" + "=" * 60)
            logger.info("✅ All enhanced FSA tests passed!")
            
            logger.info("\n🎯 Key Achievements:")
            logger.info("1. Comprehensive state tracks tasks, resources, metrics, and policies")
            logger.info("2. Human-agent discussion threads on every task")
            logger.info("3. Real-time agent coordination through shared memory")
            logger.info("4. Policy enforcement based on AML levels")
            logger.info("5. Voting workflows with comment integration")
            logger.info("6. Agent heartbeat monitoring for availability")
            
            return True
            
        except Exception as e:
            logger.error(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Run enhanced FSA tests."""
    # Note: Make sure SMS v2 is running
    # python -m uvicorn state_memory_service.service_v2:app --port 8000
    
    runner = EnhancedFSATestRunner()
    success = await runner.run_all_tests()
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)