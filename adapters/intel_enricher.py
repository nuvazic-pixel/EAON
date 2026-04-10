"""
EAON 2.0 — Intel Enricher
==========================
Multi-source threat intelligence enrichment layer.
Sources: GeoIP (MaxMind + ip-api fallback), AbuseIPDB, OTX AlienVault, VirusTotal.
"""

import time
from typing import Optional, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from config import get_settings, ScoreDeltas
from config.constants import (
    ASNType,
    ASN_RISK_WEIGHTS,
    BULLETPROOF_ASNS,
    HTTP_TIMEOUT,
    USER_AGENT,
)
from utils import get_logger, is_valid_ip, is_public_ip
from adapters.intel_cache import get_cache, cached

logger = get_logger("intel_enricher")


@dataclass
class GeoData:
    """Geographic data for an IP."""
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    isp: Optional[str] = None
    org: Optional[str] = None
    asn: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class ThreatData:
    """Threat intelligence data for an IP."""
    is_malicious: bool = False
    confidence_score: int = 0
    abuse_score: int = 0
    total_reports: int = 0
    categories: list[str] = field(default_factory=list)
    last_reported: Optional[str] = None
    sources: list[str] = field(default_factory=list)
    is_tor: bool = False
    is_vpn: bool = False
    is_proxy: bool = False
    is_hosting: bool = False
    
    @property
    def composite_threat_score(self) -> int:
        """Calculate composite threat score (0-100)."""
        score = self.abuse_score
        if self.is_tor:
            score = max(score, 50)
        if self.is_malicious:
            score = max(score, 60)
        return min(100, score)
    
    def to_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if v}
        d["composite_threat_score"] = self.composite_threat_score
        return d


@dataclass
class ASNData:
    """ASN classification data."""
    asn: Optional[str] = None
    asn_name: Optional[str] = None
    asn_type: str = ASNType.UNKNOWN
    is_bulletproof: bool = False
    
    def to_dict(self) -> dict:
        return self.__dict__


@dataclass
class IntelResult:
    """Complete intel enrichment result for an IP."""
    ip: str
    geo: Optional[GeoData] = None
    threat: Optional[ThreatData] = None
    asn: Optional[ASNData] = None
    score_delta: int = 0
    intel_reasons: list[str] = field(default_factory=list)
    intel_summary: str = ""
    lookup_time_ms: float = 0
    sources_queried: list[str] = field(default_factory=list)
    sources_failed: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "ip": self.ip,
            "geo": self.geo.to_dict() if self.geo else None,
            "threat": self.threat.to_dict() if self.threat else None,
            "asn": self.asn.to_dict() if self.asn else None,
            "score_delta": self.score_delta,
            "intel_reasons": self.intel_reasons,
            "intel_summary": self.intel_summary,
            "lookup_time_ms": round(self.lookup_time_ms, 2),
            "sources_queried": self.sources_queried,
            "sources_failed": self.sources_failed,
        }


class IntelEnricher:
    """
    Orchestrates threat intelligence lookups from multiple sources.
    Fail-soft design: partial failures don't block enrichment.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.cache = get_cache()
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
    
    def enrich(self, ip: str) -> IntelResult:
        """
        Enrich an IP with threat intelligence.
        
        Args:
            ip: IP address to enrich
        
        Returns:
            IntelResult with all available data
        """
        start = time.time()
        result = IntelResult(ip=ip)
        
        # Validate IP
        if not is_valid_ip(ip):
            result.intel_summary = "invalid IP"
            return result
        
        # Skip private IPs
        if not is_public_ip(ip):
            result.intel_summary = "private IP"
            return result
        
        # Check if enrichment is enabled
        if not self.settings.intel.enabled:
            result.intel_summary = "intel disabled"
            return result
        
        # Parallel lookups
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self._lookup_geoip, ip): "geoip",
                executor.submit(self._lookup_abuseipdb, ip): "abuseipdb",
                executor.submit(self._lookup_otx, ip): "otx",
                executor.submit(self._lookup_virustotal, ip): "virustotal",
            }
            
            for future in as_completed(futures, timeout=HTTP_TIMEOUT + 2):
                source = futures[future]
                result.sources_queried.append(source)
                
                try:
                    data = future.result()
                    if data:
                        self._merge_result(result, source, data)
                except Exception as e:
                    result.sources_failed.append(source)
                    logger.debug("intel_lookup_failed", source=source, ip=ip, error=str(e))
        
        # Calculate score delta and reasons
        self._calculate_score(result)
        
        # Generate summary
        result.intel_summary = self._generate_summary(result)
        
        result.lookup_time_ms = (time.time() - start) * 1000
        
        logger.debug(
            "intel_enriched",
            ip=ip,
            score_delta=result.score_delta,
            sources=result.sources_queried,
            time_ms=result.lookup_time_ms,
        )
        
        return result
    
    @cached("geoip", ttl=86400)  # 24h cache for geo
    def _lookup_geoip(self, ip: str) -> Optional[dict]:
        """Lookup GeoIP data."""
        # Try MaxMind first
        geo = self._lookup_maxmind(ip)
        if geo:
            return geo
        
        # Fallback to ip-api.com
        return self._lookup_ipapi(ip)
    
    def _lookup_maxmind(self, ip: str) -> Optional[dict]:
        """Lookup using MaxMind GeoLite2 database."""
        try:
            import geoip2.database
            
            db_path = self.settings.intel.geoip_db_path
            with geoip2.database.Reader(db_path) as reader:
                response = reader.city(ip)
                return {
                    "country_code": response.country.iso_code,
                    "country_name": response.country.name,
                    "city": response.city.name,
                    "region": response.subdivisions.most_specific.name if response.subdivisions else None,
                    "latitude": response.location.latitude,
                    "longitude": response.location.longitude,
                    "timezone": response.location.time_zone,
                }
        except Exception:
            return None
    
    def _lookup_ipapi(self, ip: str) -> Optional[dict]:
        """Fallback to ip-api.com for GeoIP."""
        try:
            url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,city,regionName,lat,lon,timezone,isp,org,as"
            resp = self.session.get(url, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("status") != "success":
                return None
            
            return {
                "country_code": data.get("countryCode"),
                "country_name": data.get("country"),
                "city": data.get("city"),
                "region": data.get("regionName"),
                "latitude": data.get("lat"),
                "longitude": data.get("lon"),
                "timezone": data.get("timezone"),
                "isp": data.get("isp"),
                "org": data.get("org"),
                "asn": data.get("as", "").split()[0] if data.get("as") else None,
            }
        except Exception:
            return None
    
    @cached("abuseipdb", ttl=3600)
    def _lookup_abuseipdb(self, ip: str) -> Optional[dict]:
        """Lookup AbuseIPDB data."""
        api_key = self.settings.intel.abuseipdb_api_key
        if not api_key:
            return None
        
        try:
            url = "https://api.abuseipdb.com/api/v2/check"
            headers = {
                "Key": api_key,
                "Accept": "application/json",
            }
            params = {
                "ipAddress": ip,
                "maxAgeInDays": 90,
                "verbose": True,
            }
            
            resp = self.session.get(url, headers=headers, params=params, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
            data = resp.json().get("data", {})
            
            return {
                "abuse_score": data.get("abuseConfidenceScore", 0),
                "total_reports": data.get("totalReports", 0),
                "is_tor": data.get("isTor", False),
                "is_public_proxy": data.get("isPublicProxy", False),
                "last_reported": data.get("lastReportedAt"),
                "categories": [str(c) for c in data.get("reports", [{}])[0].get("categories", [])],
                "isp": data.get("isp"),
                "usage_type": data.get("usageType"),
            }
        except Exception as e:
            logger.debug("abuseipdb_error", ip=ip, error=str(e))
            return None
    
    @cached("otx", ttl=3600)
    def _lookup_otx(self, ip: str) -> Optional[dict]:
        """Lookup OTX AlienVault data."""
        api_key = self.settings.intel.otx_api_key
        if not api_key:
            return None
        
        try:
            url = f"https://otx.alienvault.com/api/v1/indicators/IPv4/{ip}/general"
            headers = {"X-OTX-API-KEY": api_key}
            
            resp = self.session.get(url, headers=headers, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            
            pulses = data.get("pulse_info", {}).get("pulses", [])
            
            return {
                "pulse_count": len(pulses),
                "pulses": [p.get("name") for p in pulses[:5]],
                "reputation": data.get("reputation", 0),
                "asn": data.get("asn"),
            }
        except Exception as e:
            logger.debug("otx_error", ip=ip, error=str(e))
            return None
    
    @cached("virustotal", ttl=3600)
    def _lookup_virustotal(self, ip: str) -> Optional[dict]:
        """Lookup VirusTotal data."""
        api_key = self.settings.intel.virustotal_api_key
        if not api_key:
            return None
        
        try:
            url = f"https://www.virustotal.com/api/v3/ip_addresses/{ip}"
            headers = {"x-apikey": api_key}
            
            resp = self.session.get(url, headers=headers, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
            data = resp.json().get("data", {}).get("attributes", {})
            
            stats = data.get("last_analysis_stats", {})
            
            return {
                "malicious": stats.get("malicious", 0),
                "suspicious": stats.get("suspicious", 0),
                "harmless": stats.get("harmless", 0),
                "undetected": stats.get("undetected", 0),
                "reputation": data.get("reputation", 0),
                "asn": data.get("asn"),
                "as_owner": data.get("as_owner"),
                "network": data.get("network"),
            }
        except Exception as e:
            logger.debug("virustotal_error", ip=ip, error=str(e))
            return None
    
    def _merge_result(self, result: IntelResult, source: str, data: dict) -> None:
        """Merge source data into result."""
        if source == "geoip":
            result.geo = GeoData(**{k: v for k, v in data.items() if k in GeoData.__annotations__})
            
            # Extract ASN if present
            if data.get("asn"):
                if result.asn is None:
                    result.asn = ASNData()
                result.asn.asn = data["asn"]
                result.asn.is_bulletproof = data["asn"] in BULLETPROOF_ASNS
        
        elif source == "abuseipdb":
            if result.threat is None:
                result.threat = ThreatData()
            
            result.threat.abuse_score = data.get("abuse_score", 0)
            result.threat.total_reports = data.get("total_reports", 0)
            result.threat.is_tor = data.get("is_tor", False)
            result.threat.is_proxy = data.get("is_public_proxy", False)
            result.threat.last_reported = data.get("last_reported")
            result.threat.sources.append("abuseipdb")
            
            if data.get("categories"):
                result.threat.categories.extend(data["categories"])
            
            # Classify ASN type from usage_type
            usage = data.get("usage_type", "").lower()
            if result.asn is None:
                result.asn = ASNData()
            if "hosting" in usage or "datacenter" in usage:
                result.asn.asn_type = ASNType.HOSTING
                result.threat.is_hosting = True
        
        elif source == "otx":
            if result.threat is None:
                result.threat = ThreatData()
            
            pulse_count = data.get("pulse_count", 0)
            if pulse_count > 0:
                result.threat.is_malicious = True
                result.threat.sources.append("otx")
        
        elif source == "virustotal":
            if result.threat is None:
                result.threat = ThreatData()
            
            malicious = data.get("malicious", 0)
            suspicious = data.get("suspicious", 0)
            
            if malicious >= 3:
                result.threat.is_malicious = True
                result.threat.confidence_score = min(100, malicious * 10)
            elif malicious > 0 or suspicious > 0:
                result.threat.confidence_score = max(
                    result.threat.confidence_score,
                    (malicious + suspicious) * 5
                )
            
            if malicious > 0 or suspicious > 0:
                result.threat.sources.append("virustotal")
    
    def _calculate_score(self, result: IntelResult) -> None:
        """Calculate risk score delta and reasons."""
        score = 0
        reasons = []
        settings = self.settings.intel
        
        # GeoIP scoring
        if result.geo and result.geo.country_code:
            cc = result.geo.country_code
            if cc in settings.high_risk_cc:
                score += ScoreDeltas.HIGH_RISK_COUNTRY
                reasons.append(f"high-risk country: {cc}")
            elif cc in settings.medium_risk_cc:
                score += ScoreDeltas.MEDIUM_RISK_COUNTRY
                reasons.append(f"medium-risk country: {cc}")
        
        # Threat scoring
        if result.threat:
            t = result.threat
            
            # AbuseIPDB
            if t.abuse_score >= 80:
                score += ScoreDeltas.ABUSEIPDB_HIGH_CONFIDENCE
                reasons.append(f"AbuseIPDB: {t.abuse_score}% confidence")
            elif t.abuse_score >= 50:
                score += ScoreDeltas.ABUSEIPDB_MEDIUM_CONFIDENCE
                reasons.append(f"AbuseIPDB: {t.abuse_score}% confidence")
            elif t.abuse_score >= 20:
                score += ScoreDeltas.ABUSEIPDB_LOW_CONFIDENCE
            
            # VirusTotal
            if t.is_malicious and "virustotal" in t.sources:
                score += ScoreDeltas.VIRUSTOTAL_MALICIOUS
                reasons.append("VirusTotal: flagged malicious")
            
            # OTX
            if t.is_malicious and "otx" in t.sources:
                score += ScoreDeltas.OTX_PULSE_FOUND
                reasons.append("OTX: pulse found")
            
            # Anonymizers
            if t.is_tor:
                score += ScoreDeltas.TOR_EXIT_NODE
                reasons.append("TOR exit node")
            if t.is_vpn:
                score += ScoreDeltas.VPN_DETECTED
                reasons.append("VPN detected")
            if t.is_proxy:
                score += ScoreDeltas.PROXY_DETECTED
                reasons.append("proxy detected")
            if t.is_hosting:
                score += ScoreDeltas.HOSTING_PROVIDER
                reasons.append("hosting provider")
        
        # ASN scoring
        if result.asn:
            if result.asn.is_bulletproof:
                score += ScoreDeltas.BULLETPROOF_HOSTING
                reasons.append(f"bulletproof ASN: {result.asn.asn}")
            else:
                asn_risk = ASN_RISK_WEIGHTS.get(result.asn.asn_type, 0)
                if asn_risk > 0:
                    score += asn_risk
        
        result.score_delta = score
        result.intel_reasons = reasons
    
    def _generate_summary(self, result: IntelResult) -> str:
        """Generate human-readable summary."""
        parts = []
        
        if result.geo and result.geo.country_code:
            loc = result.geo.country_code
            if result.geo.city:
                loc = f"{result.geo.city}, {loc}"
            parts.append(loc)
        
        if result.threat:
            if result.threat.is_tor:
                parts.append("TOR")
            if result.threat.is_malicious:
                parts.append("MALICIOUS")
            elif result.threat.abuse_score >= 50:
                parts.append(f"abuse:{result.threat.abuse_score}%")
        
        if result.asn and result.asn.is_bulletproof:
            parts.append("BULLETPROOF")
        
        if not parts:
            parts.append("clean")
        
        return " | ".join(parts)


# Singleton
_enricher: Optional[IntelEnricher] = None


def get_enricher() -> IntelEnricher:
    """Get or create enricher singleton."""
    global _enricher
    if _enricher is None:
        _enricher = IntelEnricher()
    return _enricher


def enrich_event(src: Optional[str], dst: Optional[str] = None) -> dict:
    """
    Convenience function to enrich source (and optionally dest) IP.
    
    Args:
        src: Source IP address
        dst: Optional destination IP address
    
    Returns:
        Combined intel dict with src/dst results and aggregate score
    """
    enricher = get_enricher()
    
    result = {
        "src": None,
        "dst": None,
        "score_delta": 0,
        "intel_reasons": [],
        "intel_summary": "",
    }
    
    if src and is_valid_ip(src):
        src_intel = enricher.enrich(src)
        result["src"] = src_intel.to_dict()
        result["score_delta"] += src_intel.score_delta
        result["intel_reasons"].extend(src_intel.intel_reasons)
        result["intel_summary"] = src_intel.intel_summary
    
    if dst and is_valid_ip(dst) and dst != src:
        dst_intel = enricher.enrich(dst)
        result["dst"] = dst_intel.to_dict()
        # Only add dst score if it's higher risk
        if dst_intel.score_delta > 0:
            result["score_delta"] = max(result["score_delta"], dst_intel.score_delta // 2)
    
    return result
