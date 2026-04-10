# EAON 2.0

**Emergent Autonomous Orchestration Network**

EAON is a local-first AI orchestration system with threat intelligence integration, semantic routing, and enterprise-grade observability.

## Features

- 🧠 **Semantic Intent Routing** — Routes prompts to optimal models based on detected intent
- 🔍 **INTEL Layer** — Multi-source threat intelligence (GeoIP, AbuseIPDB, OTX, VirusTotal)
- 🚨 **Risk-Based Mode Switching** — Automatic escalation to safe mode on high-risk events
- 📊 **Structured Logging** — JSON logs with structlog for production observability
- 💬 **Slack Integration** — Rich Block Kit notifications for security events
- 🎫 **JIRA Integration** — Automatic ticket creation for incidents
- ⚡ **Redis Caching** — Fast intel lookups with fallback to in-memory LRU

## Quick Start

```bash
# 1. Clone and setup
cd eaon
cp .env.example .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start Redis (optional)
docker-compose up -d redis

# 4. Run EAON
python main.py
```

## Project Structure

```
eaon/
├── main.py                 # CLI entry point
├── config/
│   ├── settings.py         # Environment-based configuration
│   └── constants.py        # Risk thresholds, defaults
├── core/
│   ├── orchestrator.py     # Central decision engine
│   └── router.py           # Intent detection & routing
├── adapters/
│   ├── intel_enricher.py   # Multi-source threat intel
│   ├── intel_cache.py      # Redis + memory cache
│   ├── notify_slack.py     # Slack notifications
│   └── notify_jira.py      # JIRA ticket creation
├── utils/
│   ├── logging_setup.py    # structlog configuration
│   └── ip_utils.py         # IP extraction & validation
├── requirements.txt
├── docker-compose.yml
└── .env.example
```

## Configuration

All settings via environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `EAON_DEFAULT_MODEL` | Primary model | `llama3` |
| `EAON_HIGH_RISK_THRESHOLD` | Score to trigger SAFE mode | `40` |
| `INTEL_ENABLED` | Enable threat intel | `true` |
| `REDIS_ENABLED` | Use Redis for caching | `true` |
| `SLACK_ENABLED` | Enable Slack notifications | `false` |
| `JIRA_ENABLED` | Enable JIRA ticket creation | `false` |

## Usage

### Interactive Mode

```bash
python main.py
```

Commands:
- `help` — Show available commands
- `stats` — System statistics
- `cache` — Cache statistics  
- `mode <name>` — Change mode (normal/balanced/safe/lockdown)
- `exit` — Quit

### Single Prompt

```bash
python main.py -p "Analyze threat from 185.220.101.42"
```

### Modes

| Mode | Model | Critic | Confirmation |
|------|-------|--------|--------------|
| `normal` | llama3 | ❌ | ❌ |
| `balanced` | llama3 | ✅ | ❌ |
| `safe` | mistral | ✅ | ✅ |
| `lockdown` | mistral | ✅ | ✅ |

## INTEL Sources

Configure API keys in `.env`:

- **GeoIP**: MaxMind GeoLite2 (local) + ip-api.com (fallback)
- **AbuseIPDB**: `ABUSEIPDB_API_KEY`
- **OTX AlienVault**: `OTX_API_KEY`  
- **VirusTotal**: `VIRUSTOTAL_API_KEY`

## Requirements

- Python 3.11+
- Ollama with llama3 and mistral models
- Redis (optional, recommended)
- GeoLite2-City.mmdb (optional, for local GeoIP)

## License

MIT
