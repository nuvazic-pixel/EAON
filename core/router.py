"""
EAON 2.0 — Router
==================
Semantic routing with intent detection.
Uses keyword matching as fallback; upgrade to MiniLM for production.
"""

from typing import Optional, Tuple
from dataclasses import dataclass, field

from config import IntentCategory, INTENT_PRIORITY
from utils import get_logger

logger = get_logger("router")


@dataclass
class RouteMatch:
    """Result of route matching."""
    intent: str
    confidence: float
    model: str
    keywords_matched: list[str] = field(default_factory=list)


# Keyword mappings for intent detection
INTENT_KEYWORDS = {
    IntentCategory.SECURITY: [
        "threat", "attack", "malicious", "vulnerability", "exploit",
        "breach", "intrusion", "malware", "ransomware", "phishing",
        "ddos", "firewall", "incident", "compromise", "cve",
    ],
    IntentCategory.CODE: [
        "code", "function", "debug", "program", "script", "python",
        "javascript", "api", "bug", "error", "compile", "syntax",
        "class", "method", "variable", "loop", "algorithm",
    ],
    IntentCategory.DATA: [
        "data", "analyze", "csv", "database", "sql", "query",
        "pandas", "dataset", "statistics", "visualization", "chart",
        "graph", "report", "metrics", "dashboard",
    ],
    IntentCategory.SYSTEM: [
        "system", "server", "deploy", "config", "configuration",
        "install", "setup", "docker", "kubernetes", "linux",
        "windows", "network", "service", "process", "memory",
    ],
    IntentCategory.ANALYSIS: [
        "analyze", "review", "evaluate", "assess", "compare",
        "investigate", "research", "study", "examine", "audit",
    ],
    IntentCategory.CREATIVE: [
        "write", "story", "poem", "creative", "imagine", "design",
        "brainstorm", "idea", "concept", "draft", "compose",
    ],
    IntentCategory.GENERAL: [
        "help", "explain", "what", "how", "why", "when", "where",
        "tell", "describe", "define", "meaning", "example",
    ],
}

# Model mapping per intent
INTENT_MODELS = {
    IntentCategory.SECURITY: "mistral",  # More cautious
    IntentCategory.CODE: "llama3",       # Better at code
    IntentCategory.DATA: "llama3",
    IntentCategory.SYSTEM: "llama3",
    IntentCategory.ANALYSIS: "llama3",
    IntentCategory.CREATIVE: "llama3",
    IntentCategory.GENERAL: "llama3",
    IntentCategory.UNKNOWN: "llama3",
}


class Router:
    """
    Routes requests to appropriate handlers based on intent.
    
    Current implementation: keyword matching
    Future: MiniLM semantic embeddings with KNN
    """
    
    def __init__(self, default_model: str = "llama3"):
        self.default_model = default_model
        self._embedder = None  # Placeholder for MiniLM
        
        logger.info("router_init", method="keyword", default_model=default_model)
    
    def route(self, prompt: str) -> RouteMatch:
        """
        Route a prompt to the appropriate intent and model.
        
        Args:
            prompt: User prompt
        
        Returns:
            RouteMatch with intent, confidence, and model
        """
        # Try semantic routing first (if embedder available)
        if self._embedder:
            return self._route_semantic(prompt)
        
        # Fall back to keyword matching
        return self._route_keywords(prompt)
    
    def _route_keywords(self, prompt: str) -> RouteMatch:
        """Route using keyword matching."""
        prompt_lower = prompt.lower()
        
        scores: dict[str, Tuple[int, list[str]]] = {}
        
        for intent, keywords in INTENT_KEYWORDS.items():
            matched = [kw for kw in keywords if kw in prompt_lower]
            if matched:
                scores[intent] = (len(matched), matched)
        
        if not scores:
            return RouteMatch(
                intent=IntentCategory.UNKNOWN,
                confidence=0.0,
                model=self.default_model,
            )
        
        # Sort by match count, then by priority
        best_intent = max(
            scores.keys(),
            key=lambda i: (scores[i][0], -INTENT_PRIORITY.get(i, 99))
        )
        
        match_count, matched_keywords = scores[best_intent]
        max_keywords = len(INTENT_KEYWORDS[best_intent])
        confidence = min(1.0, match_count / max(3, max_keywords / 2))
        
        model = INTENT_MODELS.get(best_intent, self.default_model)
        
        logger.debug(
            "route_match",
            intent=best_intent,
            confidence=round(confidence, 2),
            keywords=matched_keywords,
            model=model,
        )
        
        return RouteMatch(
            intent=best_intent,
            confidence=confidence,
            model=model,
            keywords_matched=matched_keywords,
        )
    
    def _route_semantic(self, prompt: str) -> RouteMatch:
        """
        Route using semantic embeddings.
        
        Placeholder for MiniLM integration:
        1. Embed prompt with MiniLM
        2. Compare against intent centroids
        3. Return best match
        """
        # TODO: Implement when sentence-transformers available
        return self._route_keywords(prompt)
    
    def init_semantic(self, model_name: str = "all-MiniLM-L6-v2") -> bool:
        """
        Initialize semantic router with MiniLM.
        
        Args:
            model_name: Sentence transformer model name
        
        Returns:
            True if successful
        """
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info("loading_embedder", model=model_name)
            self._embedder = SentenceTransformer(model_name)
            
            # Pre-compute intent centroids
            self._compute_intent_centroids()
            
            logger.info("semantic_router_ready", model=model_name)
            return True
        
        except ImportError:
            logger.warning("sentence_transformers_not_installed")
            return False
        except Exception as e:
            logger.error("embedder_init_error", error=str(e))
            return False
    
    def _compute_intent_centroids(self) -> None:
        """Pre-compute embedding centroids for each intent."""
        if not self._embedder:
            return
        
        self._intent_centroids = {}
        
        for intent, keywords in INTENT_KEYWORDS.items():
            # Create representative sentences from keywords
            sentences = [f"This is about {kw}" for kw in keywords[:10]]
            embeddings = self._embedder.encode(sentences)
            
            # Compute centroid (mean embedding)
            import numpy as np
            centroid = np.mean(embeddings, axis=0)
            self._intent_centroids[intent] = centroid
        
        logger.debug("centroids_computed", intents=list(self._intent_centroids.keys()))


# Singleton
_router: Optional[Router] = None


def get_router() -> Router:
    """Get or create router singleton."""
    global _router
    if _router is None:
        from config import get_settings
        settings = get_settings()
        _router = Router(default_model=settings.orchestrator.default_model)
    return _router


def route_prompt(prompt: str) -> RouteMatch:
    """Convenience function to route a prompt."""
    return get_router().route(prompt)
