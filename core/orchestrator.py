"""
EAON 2.0 — Orchestrator
========================
Central decision engine with INTEL-aware routing and mode switching.
"""

import time
import uuid
from typing import Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from config import (
    get_settings,
    OrchestratorMode,
    MODE_CONFIGS,
    RiskLevel,
    classify_risk,
    classify_action,
)
from utils import get_logger, extract_ip, AuditLogger
from adapters import enrich_event, notify_slack, create_jira_ticket

logger = get_logger("orchestrator")
audit = AuditLogger()


class Priority(Enum):
    """Request priority levels."""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


@dataclass
class RoutingDecision:
    """Result of routing decision."""
    intent: str
    model: str
    priority: Priority
    reason: str
    mode: str
    enable_critic: bool = False
    require_confirmation: bool = False
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass
class ExecutionReport:
    """Result of execution."""
    ok: bool
    output_text: Optional[str] = None
    error: Optional[str] = None
    model_used: str = ""
    inference_time_ms: float = 0
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass
class IntelContext:
    """Intel enrichment context."""
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    score_delta: int = 0
    intel_reasons: list[str] = field(default_factory=list)
    intel_summary: str = ""
    raw: dict = field(default_factory=dict)


class Orchestrator:
    """
    Central orchestration engine.
    
    Responsibilities:
    - Intent detection and routing
    - INTEL-aware mode switching
    - Model selection and execution
    - Notification dispatch
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.orch_config = self.settings.orchestrator
        
        # Current operating mode
        self._mode = OrchestratorMode.NORMAL
        self._mode_config = MODE_CONFIGS[self._mode]
        
        # Override (can be set per-request based on INTEL)
        self.override_mode: Optional[str] = None
        
        # Stats
        self._request_count = 0
        self._error_count = 0
        
        logger.info(
            "orchestrator_init",
            mode=self._mode,
            default_model=self.orch_config.default_model,
        )
    
    @property
    def mode(self) -> str:
        """Current operating mode."""
        return self.override_mode or self._mode
    
    @property
    def mode_config(self) -> dict:
        """Current mode configuration."""
        return MODE_CONFIGS.get(self.mode, MODE_CONFIGS[OrchestratorMode.NORMAL])
    
    def set_mode(self, new_mode: str, reason: str = "manual") -> None:
        """
        Change operating mode.
        
        Args:
            new_mode: New mode to set
            reason: Reason for change
        """
        if new_mode not in MODE_CONFIGS:
            logger.warning("invalid_mode", mode=new_mode)
            return
        
        old_mode = self._mode
        self._mode = new_mode
        self._mode_config = MODE_CONFIGS[new_mode]
        
        audit.log_mode_change(old_mode, new_mode, reason)
        
        # Notify on mode change
        from adapters import get_slack_notifier
        notifier = get_slack_notifier()
        if notifier.enabled:
            notifier.notify_mode_change(old_mode, new_mode, reason)
    
    def run(self, prompt: str) -> Tuple[RoutingDecision, ExecutionReport]:
        """
        Main entry point: route and execute prompt.
        
        Args:
            prompt: User prompt
        
        Returns:
            Tuple of (RoutingDecision, ExecutionReport)
        """
        self._request_count += 1
        start_time = time.time()
        
        # Step 1: Extract IPs and enrich with INTEL
        intel_ctx = self._enrich_intel(prompt)
        
        # Step 2: Adjust mode based on risk
        self._adjust_mode_for_risk(intel_ctx)
        
        # Step 3: Route request
        decision = self._route(prompt, intel_ctx)
        
        # Step 4: Execute
        report = self._execute(prompt, decision)
        
        # Step 5: Post-process (notifications, logging)
        self._post_process(prompt, decision, report, intel_ctx)
        
        total_time = (time.time() - start_time) * 1000
        logger.info(
            "request_complete",
            request_id=decision.request_id,
            intent=decision.intent,
            model=decision.model,
            mode=decision.mode,
            time_ms=round(total_time, 2),
        )
        
        return decision, report
    
    def _enrich_intel(self, prompt: str) -> IntelContext:
        """Extract IPs and enrich with threat intelligence."""
        ctx = IntelContext()
        
        # Extract IP from prompt
        ip = extract_ip(prompt)
        if not ip:
            return ctx
        
        ctx.src_ip = ip
        
        try:
            intel = enrich_event(ip, None)
            ctx.score_delta = intel.get("score_delta", 0)
            ctx.intel_reasons = intel.get("intel_reasons", [])
            ctx.intel_summary = intel.get("intel_summary", "")
            ctx.raw = intel
        except Exception as e:
            logger.debug("intel_error", error=str(e))
        
        return ctx
    
    def _adjust_mode_for_risk(self, intel_ctx: IntelContext) -> None:
        """Adjust operating mode based on intel risk score."""
        risk_score = intel_ctx.score_delta
        
        if risk_score >= self.orch_config.high_risk_threshold:
            self.override_mode = OrchestratorMode.SAFE
            logger.warning(
                "mode_override",
                mode="safe",
                risk_score=risk_score,
                reason="high risk intel",
            )
        
        elif risk_score >= self.orch_config.medium_risk_threshold:
            self.override_mode = OrchestratorMode.BALANCED
            logger.info(
                "mode_override",
                mode="balanced",
                risk_score=risk_score,
            )
        
        else:
            self.override_mode = None
    
    def _route(self, prompt: str, intel_ctx: IntelContext) -> RoutingDecision:
        """
        Route request to appropriate model.
        
        Args:
            prompt: User prompt
            intel_ctx: Intel context
        
        Returns:
            RoutingDecision
        """
        # Detect intent
        intent = self._detect_intent(prompt)
        
        # Get model from current mode config
        mode_cfg = self.mode_config
        model = mode_cfg["model"]
        
        # Determine priority
        priority = Priority.NORMAL
        if intel_ctx.score_delta >= self.orch_config.high_risk_threshold:
            priority = Priority.HIGH
        elif "security" in intent.lower():
            priority = Priority.HIGH
        
        # Build reason
        reasons = [f"intent={intent}"]
        if intel_ctx.intel_summary:
            reasons.append(f"intel={intel_ctx.intel_summary}")
        if self.override_mode:
            reasons.append(f"mode_override={self.override_mode}")
        
        return RoutingDecision(
            intent=intent,
            model=model,
            priority=priority,
            reason=" | ".join(reasons),
            mode=self.mode,
            enable_critic=mode_cfg.get("enable_critic", False),
            require_confirmation=mode_cfg.get("require_confirmation", False),
        )
    
    def _detect_intent(self, prompt: str) -> str:
        """
        Detect intent from prompt.
        
        This is a simplified version — in production you'd use
        semantic routing with MiniLM or similar.
        """
        prompt_lower = prompt.lower()
        
        # Security keywords
        if any(kw in prompt_lower for kw in ["threat", "attack", "malicious", "vulnerability", "security"]):
            return "security"
        
        # Code keywords
        if any(kw in prompt_lower for kw in ["code", "function", "debug", "program", "script"]):
            return "code"
        
        # Data keywords
        if any(kw in prompt_lower for kw in ["data", "analyze", "csv", "database", "sql"]):
            return "data"
        
        # System keywords
        if any(kw in prompt_lower for kw in ["system", "server", "deploy", "config"]):
            return "system"
        
        return "general"
    
    def _execute(self, prompt: str, decision: RoutingDecision) -> ExecutionReport:
        """
        Execute prompt with selected model.
        
        This is a stub — integrate with your actual model handlers.
        """
        start_time = time.time()
        
        try:
            # Import model handler based on decision
            if decision.model == "llama3":
                output = self._call_llama(prompt, decision)
            elif decision.model == "mistral":
                output = self._call_mistral(prompt, decision)
            else:
                output = f"[{decision.model}] Response to: {prompt[:50]}..."
            
            inference_time = (time.time() - start_time) * 1000
            
            return ExecutionReport(
                ok=True,
                output_text=output,
                model_used=decision.model,
                inference_time_ms=inference_time,
            )
        
        except Exception as e:
            self._error_count += 1
            logger.error("execution_error", error=str(e), model=decision.model)
            
            return ExecutionReport(
                ok=False,
                error=str(e),
                model_used=decision.model,
            )
    
    def _call_llama(self, prompt: str, decision: RoutingDecision) -> str:
        """Call Llama model via Ollama."""
        try:
            import requests
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=self.orch_config.timeout_seconds,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            logger.warning("llama_fallback", error=str(e))
            return f"[llama3 unavailable] {prompt[:100]}..."
    
    def _call_mistral(self, prompt: str, decision: RoutingDecision) -> str:
        """Call Mistral model via Ollama."""
        try:
            import requests
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "mistral",
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=self.orch_config.timeout_seconds,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            logger.warning("mistral_fallback", error=str(e))
            return f"[mistral unavailable] {prompt[:100]}..."
    
    def _post_process(
        self,
        prompt: str,
        decision: RoutingDecision,
        report: ExecutionReport,
        intel_ctx: IntelContext,
    ) -> None:
        """Handle notifications and audit logging."""
        
        # Determine action based on risk
        action = classify_action(intel_ctx.score_delta)
        risk_level = classify_risk(intel_ctx.score_delta)
        
        # Audit log
        audit.log_decision(
            action=action,
            score=intel_ctx.score_delta,
            reasons=intel_ctx.intel_reasons,
            src_ip=intel_ctx.src_ip,
            intel_summary=intel_ctx.intel_summary,
        )
        
        # Slack notification
        if action in ("block", "review") or intel_ctx.score_delta >= self.orch_config.high_risk_threshold:
            notify_slack(
                action=action,
                score=intel_ctx.score_delta,
                reasons=intel_ctx.intel_reasons,
                src_ip=intel_ctx.src_ip,
                intel_summary=intel_ctx.intel_summary,
                prompt=prompt[:200],
                model=decision.model,
                request_id=decision.request_id,
            )
        
        # JIRA ticket
        if action == "block" or intel_ctx.score_delta >= self.settings.jira.high_risk_threshold:
            create_jira_ticket(
                action=action,
                score=intel_ctx.score_delta,
                reasons=intel_ctx.intel_reasons,
                src_ip=intel_ctx.src_ip,
                intel_summary=intel_ctx.intel_summary,
                prompt=prompt,
                model=decision.model,
                request_id=decision.request_id,
            )
    
    def get_stats(self) -> dict:
        """Get orchestrator statistics."""
        return {
            "mode": self.mode,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "error_rate": (
                self._error_count / self._request_count
                if self._request_count > 0
                else 0
            ),
            "config": {
                "default_model": self.orch_config.default_model,
                "high_risk_threshold": self.orch_config.high_risk_threshold,
                "medium_risk_threshold": self.orch_config.medium_risk_threshold,
            },
        }
