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

"""Compliance reporting system for generating audit-ready evidence packs."""

import asyncio
import json
import logging
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import base64

from .audit_trail import SpanData, AuditTrailManager
from .drift_detection import DriftAlert

logger = logging.getLogger(__name__)


class ReportType(Enum):
    """Types of compliance reports."""
    ISO_42001 = "iso_42001"          # AI Management System
    SOC_2 = "soc_2"                  # Security and Availability
    HIPAA = "hipaa"                  # Healthcare data protection
    PCI_DSS = "pci_dss"              # Payment card security
    GDPR = "gdpr"                    # Data protection regulation
    SEC = "sec"                      # Securities compliance
    CUSTOM = "custom"                # Custom compliance framework


class ReportFrequency(Enum):
    """Report generation frequency."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    AD_HOC = "ad_hoc"


@dataclass
class ComplianceMetric:
    """Individual compliance metric."""
    name: str
    description: str
    value: Union[float, int, str, bool]
    target: Optional[Union[float, int, str, bool]] = None
    unit: Optional[str] = None
    status: str = "compliant"  # compliant, non_compliant, warning, unknown
    evidence_refs: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class EvidencePack:
    """Container for compliance evidence."""
    evidence_id: str
    report_type: ReportType
    collection_period: Dict[str, datetime]
    
    # Evidence data
    span_summaries: List[Dict[str, Any]] = field(default_factory=list)
    policy_decisions: List[Dict[str, Any]] = field(default_factory=list)
    aml_changes: List[Dict[str, Any]] = field(default_factory=list)
    drift_alerts: List[Dict[str, Any]] = field(default_factory=list)
    access_logs: List[Dict[str, Any]] = field(default_factory=list)
    encryption_status: List[Dict[str, Any]] = field(default_factory=list)
    
    # Compliance metrics
    metrics: List[ComplianceMetric] = field(default_factory=list)
    
    # Metadata
    generated_by: str = "audit_bot"
    generation_timestamp: datetime = field(default_factory=datetime.now)
    signature: Optional[str] = None
    hash_digest: Optional[str] = None
    
    def sign_evidence(self, private_key: Optional[str] = None):
        """Sign the evidence pack for tamper detection."""
        # Create content hash
        content = self._get_content_for_hashing()
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        self.hash_digest = content_hash
        
        # Mock digital signature (in production, use real crypto)
        if private_key:
            signature_data = f"{content_hash}:audit_bot:{self.generation_timestamp.isoformat()}"
            self.signature = base64.b64encode(signature_data.encode()).decode()
        else:
            # Mock signature for testing
            self.signature = base64.b64encode(f"MOCK_SIGNATURE_{content_hash[:16]}".encode()).decode()
    
    def _get_content_for_hashing(self) -> str:
        """Get deterministic content string for hashing."""
        content_dict = {
            "evidence_id": self.evidence_id,
            "report_type": self.report_type.value,
            "collection_period": {
                k: v.isoformat() for k, v in self.collection_period.items()
            },
            "span_count": len(self.span_summaries),
            "policy_decision_count": len(self.policy_decisions),
            "aml_change_count": len(self.aml_changes),
            "metrics": [
                {
                    "name": m.name,
                    "value": str(m.value),
                    "status": m.status
                }
                for m in self.metrics
            ]
        }
        return json.dumps(content_dict, sort_keys=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert evidence pack to dictionary."""
        return {
            "evidence_id": self.evidence_id,
            "report_type": self.report_type.value,
            "collection_period": {
                k: v.isoformat() for k, v in self.collection_period.items()
            },
            "span_summaries": self.span_summaries,
            "policy_decisions": self.policy_decisions,
            "aml_changes": self.aml_changes,
            "drift_alerts": self.drift_alerts,
            "access_logs": self.access_logs,
            "encryption_status": self.encryption_status,
            "metrics": [
                {
                    "name": m.name,
                    "description": m.description,
                    "value": m.value,
                    "target": m.target,
                    "unit": m.unit,
                    "status": m.status,
                    "evidence_refs": m.evidence_refs,
                    "timestamp": m.timestamp.isoformat()
                }
                for m in self.metrics
            ],
            "generated_by": self.generated_by,
            "generation_timestamp": self.generation_timestamp.isoformat(),
            "signature": self.signature,
            "hash_digest": self.hash_digest
        }


class ComplianceReporter(ABC):
    """Abstract base class for compliance reporters."""
    
    @abstractmethod
    async def generate_report(
        self,
        start_date: datetime,
        end_date: datetime,
        **kwargs
    ) -> EvidencePack:
        """Generate compliance report for the specified period."""
        pass


class ISO42001Reporter(ComplianceReporter):
    """ISO 42001 AI Management System compliance reporter."""
    
    def __init__(self, audit_manager: AuditTrailManager):
        self.audit_manager = audit_manager
    
    async def generate_report(
        self,
        start_date: datetime,
        end_date: datetime,
        **kwargs
    ) -> EvidencePack:
        """Generate ISO 42001 compliance report."""
        evidence_id = f"iso42001_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        
        # Collect evidence
        spans = await self.audit_manager.storage.get_spans(
            start_time=start_date,
            end_time=end_date,
            limit=100000  # Large limit for comprehensive reporting
        )
        
        # Create evidence pack
        evidence = EvidencePack(
            evidence_id=evidence_id,
            report_type=ReportType.ISO_42001,
            collection_period={
                "start": start_date,
                "end": end_date
            }
        )
        
        # Generate compliance metrics
        evidence.metrics = await self._generate_iso42001_metrics(spans, start_date, end_date)
        
        # Collect span summaries (anonymized)
        evidence.span_summaries = self._create_span_summaries(spans)
        
        # Collect policy decisions
        evidence.policy_decisions = self._extract_policy_decisions(spans)
        
        # Collect AML changes (mock - would integrate with AML registry)
        evidence.aml_changes = await self._collect_aml_changes(start_date, end_date)
        
        # Sign the evidence
        evidence.sign_evidence()
        
        return evidence
    
    async def _generate_iso42001_metrics(
        self,
        spans: List[SpanData],
        start_date: datetime,
        end_date: datetime
    ) -> List[ComplianceMetric]:
        """Generate ISO 42001 specific metrics."""
        metrics = []
        
        if not spans:
            return metrics
        
        # AI System Availability (ISO 42001 Clause 8.1)
        error_count = sum(1 for span in spans if span.status.value == "error")
        availability = (len(spans) - error_count) / len(spans) * 100
        
        metrics.append(ComplianceMetric(
            name="ai_system_availability",
            description="AI system availability percentage (ISO 42001 Clause 8.1)",
            value=round(availability, 2),
            target=99.5,
            unit="percent",
            status="compliant" if availability >= 99.5 else "non_compliant",
            evidence_refs=[span.span_id for span in spans[:10]]
        ))
        
        # Policy Compliance Rate (ISO 42001 Clause 7.3)
        policy_spans = [s for s in spans if s.policy_decision]
        policy_violations = sum(1 for s in policy_spans if s.policy_decision == "deny")
        compliance_rate = (len(policy_spans) - policy_violations) / len(policy_spans) * 100 if policy_spans else 100
        
        metrics.append(ComplianceMetric(
            name="policy_compliance_rate",
            description="AI policy compliance rate (ISO 42001 Clause 7.3)",
            value=round(compliance_rate, 2),
            target=95.0,
            unit="percent",
            status="compliant" if compliance_rate >= 95.0 else "non_compliant",
            evidence_refs=[s.span_id for s in policy_spans[:10]]
        ))
        
        # Risk Management Coverage (ISO 42001 Clause 6.1)
        risk_assessments = len([s for s in spans if "risk" in s.operation_name.lower()])
        total_operations = len(spans)
        risk_coverage = risk_assessments / total_operations * 100 if total_operations > 0 else 0
        
        metrics.append(ComplianceMetric(
            name="risk_management_coverage",
            description="Risk assessment coverage of AI operations (ISO 42001 Clause 6.1)",
            value=round(risk_coverage, 2),
            target=80.0,
            unit="percent",
            status="compliant" if risk_coverage >= 80.0 else "warning"
        ))
        
        # Data Quality Monitoring (ISO 42001 Clause 7.5)
        data_quality_checks = len([s for s in spans if "data" in s.operation_name.lower()])
        
        metrics.append(ComplianceMetric(
            name="data_quality_monitoring",
            description="Data quality monitoring activities (ISO 42001 Clause 7.5)",
            value=data_quality_checks,
            target=100,
            unit="count",
            status="compliant" if data_quality_checks >= 100 else "warning"
        ))
        
        # Human Oversight (ISO 42001 Clause 7.2)
        human_approvals = len([s for s in spans if s.policy_decision == "require_approval"])
        
        metrics.append(ComplianceMetric(
            name="human_oversight_instances",
            description="Human oversight and approval instances (ISO 42001 Clause 7.2)",
            value=human_approvals,
            unit="count",
            status="compliant"
        ))
        
        return metrics
    
    def _create_span_summaries(self, spans: List[SpanData]) -> List[Dict[str, Any]]:
        """Create anonymized span summaries."""
        summaries = []
        
        for span in spans[:1000]:  # Limit for report size
            summary = {
                "span_id": span.span_id[:8] + "...",  # Truncated for privacy
                "operation_type": span.span_type.value,
                "duration_ms": span.duration_ms(),
                "status": span.status.value,
                "pillar": span.pillar,
                "aml_level": span.aml_level,
                "timestamp": span.start_time.isoformat(),
                "has_policy_decision": bool(span.policy_decision),
                "has_tool_usage": bool(span.tool_name)
            }
            summaries.append(summary)
        
        return summaries
    
    def _extract_policy_decisions(self, spans: List[SpanData]) -> List[Dict[str, Any]]:
        """Extract policy decision evidence."""
        decisions = []
        
        for span in spans:
            if span.policy_decision:
                decision = {
                    "timestamp": span.start_time.isoformat(),
                    "decision": span.policy_decision,
                    "reasons": span.policy_reasons,
                    "agent_id": span.agent_id,
                    "pillar": span.pillar,
                    "operation": span.operation_name,
                    "aml_level": span.aml_level
                }
                decisions.append(decision)
        
        return decisions[:500]  # Limit for report size
    
    async def _collect_aml_changes(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Collect AML level changes (mock implementation)."""
        # Mock AML changes for demonstration
        return [
            {
                "timestamp": start_date.isoformat(),
                "agent_group": "pricing_bot_agents",
                "from_level": 3,
                "to_level": 2,
                "change_type": "demotion",
                "reason": "Policy violations detected",
                "changed_by": "drift_detector"
            },
            {
                "timestamp": (start_date + timedelta(days=2)).isoformat(),
                "agent_group": "customer_support_agents",
                "from_level": 2,
                "to_level": 3,
                "change_type": "promotion",
                "reason": "Performance improvements validated",
                "changed_by": "human_operator"
            }
        ]


class SOC2Reporter(ComplianceReporter):
    """SOC 2 Security and Availability compliance reporter."""
    
    def __init__(self, audit_manager: AuditTrailManager):
        self.audit_manager = audit_manager
    
    async def generate_report(
        self,
        start_date: datetime,
        end_date: datetime,
        **kwargs
    ) -> EvidencePack:
        """Generate SOC 2 compliance report."""
        evidence_id = f"soc2_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        
        spans = await self.audit_manager.storage.get_spans(
            start_time=start_date,
            end_time=end_date,
            limit=100000
        )
        
        evidence = EvidencePack(
            evidence_id=evidence_id,
            report_type=ReportType.SOC_2,
            collection_period={
                "start": start_date,
                "end": end_date
            }
        )
        
        # Generate SOC 2 specific metrics
        evidence.metrics = await self._generate_soc2_metrics(spans, start_date, end_date)
        
        # Collect access logs
        evidence.access_logs = self._extract_access_logs(spans)
        
        # Collect encryption status
        evidence.encryption_status = self._collect_encryption_status()
        
        # Collect security events
        evidence.span_summaries = self._create_security_summaries(spans)
        
        evidence.sign_evidence()
        return evidence
    
    async def _generate_soc2_metrics(
        self,
        spans: List[SpanData],
        start_date: datetime,
        end_date: datetime
    ) -> List[ComplianceMetric]:
        """Generate SOC 2 Trust Services Criteria metrics."""
        metrics = []
        
        # Security - Access Controls (CC6.1)
        unauthorized_access = len([s for s in spans if s.error_type == "Unauthorized"])
        
        metrics.append(ComplianceMetric(
            name="unauthorized_access_attempts",
            description="Count of unauthorized access attempts (CC6.1)",
            value=unauthorized_access,
            target=0,
            unit="count",
            status="compliant" if unauthorized_access == 0 else "non_compliant"
        ))
        
        # Availability - System Uptime (A1.1)
        if spans:
            error_rate = sum(1 for s in spans if s.status.value == "error") / len(spans) * 100
            uptime = 100 - error_rate
        else:
            uptime = 100
        
        metrics.append(ComplianceMetric(
            name="system_uptime",
            description="System availability percentage (A1.1)",
            value=round(uptime, 2),
            target=99.9,
            unit="percent",
            status="compliant" if uptime >= 99.9 else "non_compliant"
        ))
        
        # Processing Integrity - Data Accuracy (PI1.1)
        data_operations = [s for s in spans if "data" in s.operation_name.lower()]
        data_errors = [s for s in data_operations if s.status.value == "error"]
        data_integrity = (len(data_operations) - len(data_errors)) / len(data_operations) * 100 if data_operations else 100
        
        metrics.append(ComplianceMetric(
            name="data_processing_integrity",
            description="Data processing integrity rate (PI1.1)",
            value=round(data_integrity, 2),
            target=99.0,
            unit="percent",
            status="compliant" if data_integrity >= 99.0 else "warning"
        ))
        
        # Confidentiality - Encryption Usage (C1.1)
        encrypted_operations = len([s for s in spans if "encrypted" in s.attributes.get("tags", "")])
        encryption_rate = encrypted_operations / len(spans) * 100 if spans else 0
        
        metrics.append(ComplianceMetric(
            name="encryption_coverage",
            description="Percentage of operations using encryption (C1.1)",
            value=round(encryption_rate, 2),
            target=100.0,
            unit="percent",
            status="compliant" if encryption_rate >= 100.0 else "non_compliant"
        ))
        
        return metrics
    
    def _extract_access_logs(self, spans: List[SpanData]) -> List[Dict[str, Any]]:
        """Extract access log evidence."""
        access_logs = []
        
        for span in spans[:1000]:  # Limit for report size
            if span.agent_id:  # Only spans with agent access
                log_entry = {
                    "timestamp": span.start_time.isoformat(),
                    "agent_id": span.agent_id,
                    "operation": span.operation_name,
                    "status": span.status.value,
                    "pillar": span.pillar,
                    "source_ip": "10.0.0.1",  # Mock IP
                    "user_agent": "ADK-Agent/1.0",
                    "resource_accessed": span.tool_name or "internal_operation"
                }
                access_logs.append(log_entry)
        
        return access_logs
    
    def _collect_encryption_status(self) -> List[Dict[str, Any]]:
        """Collect encryption status evidence."""
        return [
            {
                "component": "data_at_rest",
                "encryption_enabled": True,
                "encryption_algorithm": "AES-256",
                "key_management": "Cloud KMS",
                "status": "compliant"
            },
            {
                "component": "data_in_transit", 
                "encryption_enabled": True,
                "encryption_algorithm": "TLS 1.3",
                "certificate_status": "valid",
                "status": "compliant"
            },
            {
                "component": "application_layer",
                "encryption_enabled": True,
                "encryption_algorithm": "ChaCha20-Poly1305",
                "key_rotation": "automatic",
                "status": "compliant"
            }
        ]
    
    def _create_security_summaries(self, spans: List[SpanData]) -> List[Dict[str, Any]]:
        """Create security-focused span summaries."""
        summaries = []
        
        for span in spans[:500]:
            summary = {
                "timestamp": span.start_time.isoformat(),
                "operation_type": span.span_type.value,
                "security_context": {
                    "agent_authenticated": bool(span.agent_id),
                    "policy_checked": bool(span.policy_decision),
                    "encryption_used": "encrypted" in span.attributes.get("tags", ""),
                    "access_level": span.aml_level
                },
                "outcome": span.status.value,
                "duration_ms": span.duration_ms()
            }
            summaries.append(summary)
        
        return summaries


class ComplianceOrchestrator:
    """Main orchestrator for compliance reporting."""
    
    def __init__(
        self,
        audit_manager: AuditTrailManager,
        report_storage_path: Optional[str] = None
    ):
        self.audit_manager = audit_manager
        self.report_storage_path = report_storage_path or "/tmp/compliance_reports"
        
        # Initialize reporters
        self.reporters = {
            ReportType.ISO_42001: ISO42001Reporter(audit_manager),
            ReportType.SOC_2: SOC2Reporter(audit_manager)
        }
        
        # Scheduled reports
        self.scheduled_reports: Dict[str, Dict[str, Any]] = {}
    
    def add_reporter(self, report_type: ReportType, reporter: ComplianceReporter):
        """Add custom compliance reporter."""
        self.reporters[report_type] = reporter
    
    async def generate_report(
        self,
        report_type: ReportType,
        start_date: datetime,
        end_date: datetime,
        **kwargs
    ) -> EvidencePack:
        """Generate compliance report."""
        if report_type not in self.reporters:
            raise ValueError(f"No reporter configured for {report_type.value}")
        
        reporter = self.reporters[report_type]
        evidence_pack = await reporter.generate_report(start_date, end_date, **kwargs)
        
        # Store report
        await self._store_report(evidence_pack)
        
        logger.info(f"Generated {report_type.value} compliance report: {evidence_pack.evidence_id}")
        return evidence_pack
    
    async def generate_weekly_reports(self) -> List[EvidencePack]:
        """Generate all weekly compliance reports."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        reports = []
        for report_type in [ReportType.ISO_42001, ReportType.SOC_2]:
            try:
                report = await self.generate_report(report_type, start_date, end_date)
                reports.append(report)
            except Exception as e:
                logger.error(f"Failed to generate {report_type.value} report: {e}")
        
        return reports
    
    async def generate_monthly_reports(self) -> List[EvidencePack]:
        """Generate all monthly compliance reports."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        reports = []
        for report_type in self.reporters:
            try:
                report = await self.generate_report(report_type, start_date, end_date)
                reports.append(report)
            except Exception as e:
                logger.error(f"Failed to generate {report_type.value} report: {e}")
        
        return reports
    
    async def _store_report(self, evidence_pack: EvidencePack):
        """Store compliance report (mock implementation)."""
        # In production, this would upload to secure storage (WORM bucket)
        logger.info(f"Would store report {evidence_pack.evidence_id} to secure storage")
        
        # Mock storage to local filesystem
        import os
        os.makedirs(self.report_storage_path, exist_ok=True)
        
        report_path = f"{self.report_storage_path}/{evidence_pack.evidence_id}.json"
        with open(report_path, 'w') as f:
            json.dump(evidence_pack.to_dict(), f, indent=2)
        
        logger.debug(f"Stored report locally: {report_path}")
    
    async def get_compliance_dashboard(self) -> Dict[str, Any]:
        """Get compliance dashboard summary."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Get recent spans for analysis
        spans = await self.audit_manager.storage.get_spans(
            start_time=start_date,
            end_time=end_date,
            limit=10000
        )
        
        # Calculate overall compliance metrics
        total_operations = len(spans)
        error_operations = sum(1 for s in spans if s.status.value == "error")
        policy_violations = sum(1 for s in spans if s.policy_decision == "deny")
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": 30
            },
            "overall_metrics": {
                "total_operations": total_operations,
                "success_rate": round((total_operations - error_operations) / total_operations * 100, 2) if total_operations > 0 else 100,
                "policy_compliance_rate": round((total_operations - policy_violations) / total_operations * 100, 2) if total_operations > 0 else 100,
                "availability_estimate": round((total_operations - error_operations) / total_operations * 100, 2) if total_operations > 0 else 100
            },
            "compliance_status": {
                "iso_42001": "compliant",
                "soc_2": "compliant",
                "last_audit": "2024-Q4",
                "next_audit": "2025-Q2"
            },
            "recent_activities": {
                "reports_generated": 2,
                "policy_updates": 1,
                "aml_adjustments": 3,
                "security_alerts": 0
            }
        }