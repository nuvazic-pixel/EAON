"""
EAON 2.0 — Constants & Defaults
================================
Static values that don't change based on environment.
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RISK SCORING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class RiskLevel:
    """Risk level classifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskThresholds:
    """Score thresholds for risk classification."""
    LOW_MAX = 19
    MEDIUM_MAX = 39
    HIGH_MAX = 69
    # Above HIGH_MAX = CRITICAL


class ScoreDeltas:
    """Score adjustments for various intel signals."""
    # GeoIP-based
    HIGH_RISK_COUNTRY = 25
    MEDIUM_RISK_COUNTRY = 10
    TOR_EXIT_NODE = 30
    VPN_DETECTED = 5
    PROXY_DETECTED = 10
    HOSTING_PROVIDER = 8
    
    # Threat intelligence
    ABUSEIPDB_HIGH_CONFIDENCE = 35      # confidence > 80
    ABUSEIPDB_MEDIUM_CONFIDENCE = 20    # confidence 50-80
    ABUSEIPDB_LOW_CONFIDENCE = 10       # confidence 20-50
    
    OTX_PULSE_FOUND = 15
    OTX_MULTIPLE_PULSES = 25            # 3+ pulses
    
    VIRUSTOTAL_MALICIOUS = 40           # 3+ engines flagged
    VIRUSTOTAL_SUSPICIOUS = 20          # 1-2 engines flagged
    
    # ASN reputation
    BULLETPROOF_HOSTING = 35
    KNOWN_BAD_ASN = 20
    
    # Behavioral (for future use)
    UNUSUAL_PORT = 5
    UNUSUAL_PROTOCOL = 5
    HIGH_REQUEST_RATE = 15


class ActionClassification:
    """Action labels based on score."""
    ALLOW = "allow"
    REVIEW = "review"
    BLOCK = "block"
    ESCALATE = "escalate"


def classify_risk(score: int) -> str:
    """Classify risk level based on score."""
    if score <= RiskThresholds.LOW_MAX:
        return RiskLevel.LOW
    elif score <= RiskThresholds.MEDIUM_MAX:
        return RiskLevel.MEDIUM
    elif score <= RiskThresholds.HIGH_MAX:
        return RiskLevel.HIGH
    else:
        return RiskLevel.CRITICAL


def classify_action(score: int) -> str:
    """Classify action based on score."""
    if score <= RiskThresholds.LOW_MAX:
        return ActionClassification.ALLOW
    elif score <= RiskThresholds.MEDIUM_MAX:
        return ActionClassification.REVIEW
    elif score <= RiskThresholds.HIGH_MAX:
        return ActionClassification.BLOCK
    else:
        return ActionClassification.ESCALATE


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ORCHESTRATOR MODES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class OrchestratorMode:
    """Orchestrator operating modes."""
    NORMAL = "normal"
    BALANCED = "balanced"
    SAFE = "safe"
    LOCKDOWN = "lockdown"


MODE_CONFIGS = {
    OrchestratorMode.NORMAL: {
        "model": "llama3",
        "enable_critic": False,
        "require_confirmation": False,
        "log_level": "INFO",
    },
    OrchestratorMode.BALANCED: {
        "model": "llama3",
        "enable_critic": True,
        "require_confirmation": False,
        "log_level": "INFO",
    },
    OrchestratorMode.SAFE: {
        "model": "mistral",
        "enable_critic": True,
        "require_confirmation": True,
        "log_level": "WARNING",
    },
    OrchestratorMode.LOCKDOWN: {
        "model": "mistral",
        "enable_critic": True,
        "require_confirmation": True,
        "log_level": "ERROR",
    },
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTENT CATEGORIES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class IntentCategory:
    """Intent classification categories."""
    GENERAL = "general"
    CODE = "code"
    SECURITY = "security"
    DATA = "data"
    SYSTEM = "system"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    UNKNOWN = "unknown"


INTENT_PRIORITY = {
    IntentCategory.SECURITY: 1,     # Highest
    IntentCategory.SYSTEM: 2,
    IntentCategory.CODE: 3,
    IntentCategory.DATA: 4,
    IntentCategory.ANALYSIS: 5,
    IntentCategory.GENERAL: 6,
    IntentCategory.CREATIVE: 7,
    IntentCategory.UNKNOWN: 10,     # Lowest
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ASN TYPES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ASNType:
    """ASN classification types."""
    RESIDENTIAL = "residential"
    BUSINESS = "business"
    HOSTING = "hosting"
    EDUCATION = "education"
    GOVERNMENT = "government"
    MOBILE = "mobile"
    UNKNOWN = "unknown"


ASN_RISK_WEIGHTS = {
    ASNType.RESIDENTIAL: 0,
    ASNType.BUSINESS: 0,
    ASNType.EDUCATION: 0,
    ASNType.GOVERNMENT: 0,
    ASNType.MOBILE: 2,
    ASNType.HOSTING: 8,
    ASNType.UNKNOWN: 5,
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KNOWN BAD ACTORS (sample — extend as needed)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BULLETPROOF_ASNS = {
    "AS202425",  # IP Volume Inc
    "AS51852",   # Private Layer Inc
    "AS44477",   # Stark Industries
    "AS62904",   # Eonix Corporation
    "AS398101",  # GoDaddy abuse-heavy
}

KNOWN_TOR_PORTS = {9001, 9030, 9050, 9051, 9150}

KNOWN_VPN_PORTS = {1194, 1723, 500, 4500, 51820}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HTTP / API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HTTP_TIMEOUT = 10  # seconds
HTTP_RETRIES = 2

USER_AGENT = "EAON/2.0 ThreatIntel (+https://github.com/eaon)"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COLORS (for console output)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Colors:
    """ANSI color codes for console output."""
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    
    @classmethod
    def risk(cls, level: str) -> str:
        """Get color for risk level."""
        return {
            RiskLevel.LOW: cls.GREEN,
            RiskLevel.MEDIUM: cls.YELLOW,
            RiskLevel.HIGH: cls.RED,
            RiskLevel.CRITICAL: cls.MAGENTA,
        }.get(level, cls.WHITE)
