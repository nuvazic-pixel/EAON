"""
EAON 2.0 — Slack Notifications
===============================
Rich Slack notifications with Block Kit formatting.
"""

import json
from typing import Optional, Any
from dataclasses import dataclass
from datetime import datetime

import requests

from config import get_settings, RiskLevel, classify_risk
from utils import get_logger, obfuscate_ip

logger = get_logger("notify_slack")


@dataclass
class SlackMessage:
    """Slack message with optional blocks."""
    text: str
    blocks: Optional[list[dict]] = None
    attachments: Optional[list[dict]] = None
    thread_ts: Optional[str] = None


class SlackNotifier:
    """
    Sends notifications to Slack using Block Kit.
    """
    
    # Emoji mapping for risk levels
    RISK_EMOJI = {
        RiskLevel.LOW: "✅",
        RiskLevel.MEDIUM: "⚠️",
        RiskLevel.HIGH: "🚨",
        RiskLevel.CRITICAL: "🔴",
    }
    
    # Color mapping for attachments
    RISK_COLORS = {
        RiskLevel.LOW: "#36a64f",      # green
        RiskLevel.MEDIUM: "#f2c744",   # yellow
        RiskLevel.HIGH: "#e01e5a",     # red
        RiskLevel.CRITICAL: "#8b0000", # dark red
    }
    
    def __init__(self):
        self.settings = get_settings().slack
        self.session = requests.Session()
    
    @property
    def enabled(self) -> bool:
        return self.settings.enabled and bool(self.settings.webhook_url)
    
    def send(self, message: SlackMessage) -> bool:
        """
        Send message to Slack.
        
        Args:
            message: SlackMessage to send
        
        Returns:
            True if successful
        """
        if not self.enabled:
            logger.debug("slack_disabled")
            return False
        
        payload = {
            "text": message.text,
            "username": self.settings.username,
            "icon_emoji": self.settings.icon_emoji,
            "channel": self.settings.channel,
        }
        
        if message.blocks:
            payload["blocks"] = message.blocks
        
        if message.attachments:
            payload["attachments"] = message.attachments
        
        if message.thread_ts:
            payload["thread_ts"] = message.thread_ts
        
        try:
            resp = self.session.post(
                self.settings.webhook_url,
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
            logger.info("slack_sent", channel=self.settings.channel)
            return True
        except Exception as e:
            logger.error("slack_error", error=str(e))
            return False
    
    def notify_decision(
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
    ) -> bool:
        """
        Send notification for a security decision.
        
        Args:
            action: Decision action (allow/review/block)
            score: Risk score
            reasons: List of reasons
            src_ip: Optional source IP
            dst_ip: Optional destination IP
            intel_summary: Optional intel summary
            prompt: Optional triggering prompt (truncated)
            model: Optional model used
            request_id: Optional request ID for threading
        
        Returns:
            True if sent successfully
        """
        risk_level = classify_risk(score)
        
        # Check if we should notify based on settings
        if not self._should_notify(action, score):
            return False
        
        blocks = self._build_decision_blocks(
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
        
        fallback_text = f"EAON {action.upper()} | Score: {score} | {risk_level}"
        
        message = SlackMessage(
            text=fallback_text,
            blocks=blocks,
        )
        
        return self.send(message)
    
    def notify_mode_change(
        self,
        old_mode: str,
        new_mode: str,
        reason: str,
        triggered_by: Optional[str] = None,
    ) -> bool:
        """Notify about orchestrator mode change."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔄 EAON Mode Change",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*From:*\n`{old_mode}`"},
                    {"type": "mrkdwn", "text": f"*To:*\n`{new_mode}`"},
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Reason:* {reason}"}
            },
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
                    }
                ]
            }
        ]
        
        if triggered_by:
            blocks.insert(3, {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Triggered by:* `{triggered_by}`"}
            })
        
        message = SlackMessage(
            text=f"EAON mode changed: {old_mode} → {new_mode}",
            blocks=blocks,
        )
        
        return self.send(message)
    
    def notify_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[dict] = None,
    ) -> bool:
        """Notify about system error."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚠️ EAON Error",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Type:*\n`{error_type}`"},
                    {"type": "mrkdwn", "text": f"*Time:*\n{datetime.utcnow().strftime('%H:%M:%S')} UTC"},
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"```{error_message[:500]}```"}
            },
        ]
        
        if context:
            context_text = "\n".join(f"• {k}: `{v}`" for k, v in context.items())
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Context:*\n{context_text}"}
            })
        
        message = SlackMessage(
            text=f"EAON Error: {error_type}",
            blocks=blocks,
        )
        
        return self.send(message)
    
    def _should_notify(self, action: str, score: int) -> bool:
        """Check if notification should be sent based on settings."""
        if action == "block" and self.settings.notify_on_block:
            return True
        if action == "review" and self.settings.notify_on_review:
            return True
        if score >= self.settings.high_risk_threshold and self.settings.notify_on_high_risk:
            return True
        return False
    
    def _build_decision_blocks(
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
    ) -> list[dict]:
        """Build Block Kit blocks for decision notification."""
        emoji = self.RISK_EMOJI.get(risk_level, "❓")
        color = self.RISK_COLORS.get(risk_level, "#808080")
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} EAON Decision: {action.upper()}",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Risk Score:*\n`{score}`"},
                    {"type": "mrkdwn", "text": f"*Risk Level:*\n`{risk_level}`"},
                ]
            },
        ]
        
        # IPs
        if src_ip or dst_ip:
            ip_fields = []
            if src_ip:
                ip_fields.append({"type": "mrkdwn", "text": f"*Source:*\n`{obfuscate_ip(src_ip)}`"})
            if dst_ip:
                ip_fields.append({"type": "mrkdwn", "text": f"*Dest:*\n`{obfuscate_ip(dst_ip)}`"})
            blocks.append({"type": "section", "fields": ip_fields})
        
        # Intel summary
        if intel_summary:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Intel:* `{intel_summary}`"}
            })
        
        # Reasons
        if reasons:
            reasons_text = "\n".join(f"• {r}" for r in reasons[:10])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Reasons:*\n{reasons_text}"}
            })
        
        # Prompt (truncated)
        if prompt:
            truncated = prompt[:200] + "..." if len(prompt) > 200 else prompt
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Prompt:*\n```{truncated}```"}
            })
        
        blocks.append({"type": "divider"})
        
        # Footer
        footer_parts = [f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"]
        if model:
            footer_parts.append(f"🤖 {model}")
        if request_id:
            footer_parts.append(f"🔗 {request_id[:8]}")
        
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": " | ".join(footer_parts)}]
        })
        
        return blocks


# Singleton
_notifier: Optional[SlackNotifier] = None


def get_slack_notifier() -> SlackNotifier:
    """Get or create Slack notifier singleton."""
    global _notifier
    if _notifier is None:
        _notifier = SlackNotifier()
    return _notifier


def notify_slack(
    action: str,
    score: int,
    reasons: list[str],
    **kwargs,
) -> bool:
    """Convenience function to send Slack notification."""
    return get_slack_notifier().notify_decision(
        action=action,
        score=score,
        reasons=reasons,
        **kwargs,
    )
