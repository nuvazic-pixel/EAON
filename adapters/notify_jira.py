"""
EAON 2.0 — JIRA Integration
============================
Automatic ticket creation for security events.
"""

from typing import Optional
from dataclasses import dataclass
from datetime import datetime

import requests

from config import get_settings, classify_risk, RiskLevel
from utils import get_logger

logger = get_logger("notify_jira")


@dataclass
class JiraTicket:
    """JIRA ticket data."""
    summary: str
    description: str
    issue_type: str = "Task"
    priority: str = "Medium"
    labels: list[str] = None
    components: list[str] = None
    custom_fields: dict = None
    
    def __post_init__(self):
        self.labels = self.labels or []
        self.components = self.components or []
        self.custom_fields = self.custom_fields or {}


@dataclass
class JiraTicketResult:
    """Result of ticket creation."""
    success: bool
    ticket_key: Optional[str] = None
    ticket_url: Optional[str] = None
    error: Optional[str] = None


class JiraNotifier:
    """
    Creates JIRA tickets for security events.
    """
    
    PRIORITY_MAP = {
        RiskLevel.LOW: "Low",
        RiskLevel.MEDIUM: "Medium",
        RiskLevel.HIGH: "High",
        RiskLevel.CRITICAL: "Highest",
    }
    
    def __init__(self):
        self.settings = get_settings().jira
        self.session = requests.Session()
        
        if self.settings.username and self.settings.api_token:
            self.session.auth = (self.settings.username, self.settings.api_token)
        
        self.session.headers["Content-Type"] = "application/json"
        self.session.headers["Accept"] = "application/json"
    
    @property
    def enabled(self) -> bool:
        return (
            self.settings.enabled
            and bool(self.settings.server_url)
            and bool(self.settings.username)
            and bool(self.settings.api_token)
        )
    
    @property
    def api_url(self) -> str:
        base = self.settings.server_url.rstrip("/")
        return f"{base}/rest/api/3/issue"
    
    def create_ticket(self, ticket: JiraTicket) -> JiraTicketResult:
        """
        Create a JIRA ticket.
        
        Args:
            ticket: JiraTicket data
        
        Returns:
            JiraTicketResult with ticket key/URL or error
        """
        if not self.enabled:
            return JiraTicketResult(success=False, error="JIRA not configured")
        
        payload = {
            "fields": {
                "project": {"key": self.settings.project_key},
                "summary": ticket.summary,
                "description": self._format_description(ticket.description),
                "issuetype": {"name": ticket.issue_type},
                "priority": {"name": ticket.priority},
            }
        }
        
        if ticket.labels:
            payload["fields"]["labels"] = ticket.labels
        
        if ticket.custom_fields:
            payload["fields"].update(ticket.custom_fields)
        
        try:
            resp = self.session.post(self.api_url, json=payload, timeout=15)
            resp.raise_for_status()
            
            data = resp.json()
            ticket_key = data.get("key")
            ticket_url = f"{self.settings.server_url}/browse/{ticket_key}"
            
            logger.info("jira_created", ticket=ticket_key)
            
            return JiraTicketResult(
                success=True,
                ticket_key=ticket_key,
                ticket_url=ticket_url,
            )
        
        except requests.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.error("jira_error", error=error_msg)
            return JiraTicketResult(success=False, error=error_msg)
        
        except Exception as e:
            logger.error("jira_error", error=str(e))
            return JiraTicketResult(success=False, error=str(e))
    
    def create_security_ticket(
        self,
        action: str,
        score: int,
        reasons: list[str],
        src_ip: Optional[str] = None,
        dst_ip: Optional[str] = None,
        intel_summary: Optional[str] = None,
        prompt: Optional[str] = None,
        model: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> JiraTicketResult:
        """
        Create a security incident ticket.
        
        Args:
            action: Decision action
            score: Risk score
            reasons: List of reasons
            src_ip: Optional source IP
            dst_ip: Optional destination IP
            intel_summary: Optional intel summary
            prompt: Optional triggering prompt
            model: Optional model used
            request_id: Optional request ID
        
        Returns:
            JiraTicketResult
        """
        # Check if we should create ticket
        if not self._should_create(action, score):
            return JiraTicketResult(success=False, error="Does not meet ticket criteria")
        
        risk_level = classify_risk(score)
        priority = self.PRIORITY_MAP.get(risk_level, "Medium")
        
        # Build summary
        summary = f"[EAON] {action.upper()} - Score {score} - {intel_summary or 'Security Event'}"
        if len(summary) > 100:
            summary = summary[:97] + "..."
        
        # Build description
        description = self._build_description(
            action=action,
            score=score,
            risk_level=risk_level,
            reasons=reasons,
            src_ip=src_ip,
            dst_ip=dst_ip,
            intel_summary=intel_summary,
            prompt=prompt,
            model=model,
            request_id=request_id,
        )
        
        # Labels
        labels = ["eaon", "security", f"risk-{risk_level}", action]
        
        ticket = JiraTicket(
            summary=summary,
            description=description,
            issue_type=self.settings.issue_type,
            priority=priority,
            labels=labels,
        )
        
        return self.create_ticket(ticket)
    
    def _should_create(self, action: str, score: int) -> bool:
        """Check if ticket should be created based on settings."""
        if action == "block" and self.settings.create_on_block:
            return True
        if score >= self.settings.high_risk_threshold and self.settings.create_on_high_risk:
            return True
        return False
    
    def _build_description(
        self,
        action: str,
        score: int,
        risk_level: str,
        reasons: list[str],
        src_ip: Optional[str],
        dst_ip: Optional[str],
        intel_summary: Optional[str],
        prompt: Optional[str],
        model: Optional[str],
        request_id: Optional[str],
    ) -> str:
        """Build ticket description."""
        lines = [
            "h2. Security Event Details",
            "",
            f"*Action:* {action.upper()}",
            f"*Risk Score:* {score}",
            f"*Risk Level:* {risk_level}",
            f"*Timestamp:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            "",
        ]
        
        if src_ip or dst_ip:
            lines.append("h3. Network")
            if src_ip:
                lines.append(f"*Source IP:* {src_ip}")
            if dst_ip:
                lines.append(f"*Destination IP:* {dst_ip}")
            lines.append("")
        
        if intel_summary:
            lines.append("h3. Threat Intelligence")
            lines.append(f"{intel_summary}")
            lines.append("")
        
        if reasons:
            lines.append("h3. Risk Indicators")
            for r in reasons:
                lines.append(f"* {r}")
            lines.append("")
        
        if prompt:
            lines.append("h3. Triggering Prompt")
            lines.append("{code}")
            lines.append(prompt[:1000])
            lines.append("{code}")
            lines.append("")
        
        lines.append("h3. System Info")
        if model:
            lines.append(f"*Model:* {model}")
        if request_id:
            lines.append(f"*Request ID:* {request_id}")
        
        lines.append("")
        lines.append("----")
        lines.append("_Automatically created by EAON 2.0_")
        
        return "\n".join(lines)
    
    def _format_description(self, text: str) -> dict:
        """Format description for JIRA API v3 (ADF format)."""
        # JIRA API v3 requires Atlassian Document Format
        # For simplicity, we use a basic paragraph with the text
        return {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": text,
                        }
                    ]
                }
            ]
        }


# Singleton
_notifier: Optional[JiraNotifier] = None


def get_jira_notifier() -> JiraNotifier:
    """Get or create JIRA notifier singleton."""
    global _notifier
    if _notifier is None:
        _notifier = JiraNotifier()
    return _notifier


def create_jira_ticket(
    action: str,
    score: int,
    reasons: list[str],
    **kwargs,
) -> JiraTicketResult:
    """Convenience function to create JIRA ticket."""
    return get_jira_notifier().create_security_ticket(
        action=action,
        score=score,
        reasons=reasons,
        **kwargs,
    )
