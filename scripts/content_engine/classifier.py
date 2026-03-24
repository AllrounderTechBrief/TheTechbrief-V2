"""
classifier.py — The Tech Brief V3
Topic Classification Engine: maps any topic to a niche category,
which then drives tone, depth, structure, and prompt strategy.
"""

import re
from typing import Literal

Category = Literal[
    "cybersecurity",
    "enterprise_tech",
    "consumer_tech",
    "evs_automotive",
    "ai_ml",
    "space_science",
    "mobile_gadgets",
    "gaming",
    "startups_business",
    "broadcast_tech",
]

# ── Keyword taxonomy ────────────────────────────────────────────────────────
_TAXONOMY: dict[Category, list[str]] = {
    "cybersecurity": [
        "ransomware", "phishing", "malware", "zero-day", "cve", "vulnerability",
        "exploit", "threat", "breach", "hack", "ddos", "firewall", "vpn",
        "encryption", "siem", "soc", "apt", "attack surface", "pen test",
        "pentesting", "incident response", "zero trust", "identity", "iam",
        "mfa", "authentication", "privilege escalation", "lateral movement",
        "dark web", "botnet", "spyware", "adware", "keylogger", "worm",
        "supply chain attack", "social engineering", "credential stuffing",
        "security posture", "endpoint", "edr", "xdr", "osint",
    ],
    "enterprise_tech": [
        "enterprise", "saas", "cloud", "kubernetes", "docker", "devops",
        "ci/cd", "microservices", "api", "erp", "crm", "salesforce",
        "azure", "aws", "gcp", "infrastructure", "data center", "networking",
        "wan", "sd-wan", "server", "virtualization", "hybrid cloud",
        "multi-cloud", "database", "sql", "nosql", "data warehouse",
        "business intelligence", "bi", "digital transformation", "roi",
        "scalability", "compliance", "gdpr", "hipaa", "it governance",
        "sla", "managed service", "msp", "outsourcing",
    ],
    "consumer_tech": [
        "review", "buying guide", "best", "vs", "comparison", "unboxing",
        "smartwatch", "earbuds", "headphones", "laptop", "tablet", "pc",
        "mac", "windows", "smart home", "router", "wifi", "streaming",
        "netflix", "4k", "oled", "monitor", "keyboard", "mouse",
        "webcam", "camera", "drone", "printer", "smart tv", "alexa",
        "google home", "apple",
    ],
    "evs_automotive": [
        "electric vehicle", "ev", "tesla", "charging", "battery", "range",
        "autonomous", "self-driving", "adas", "lidar", "motor", "torque",
        "emissions", "hybrid", "phev", "bev", "fuel cell", "hydrogen",
        "rivian", "lucid", "volkswagen id", "gm ev", "ford lightning",
        "charging station", "fast charging", "vehicle software", "ota update",
        "autopilot", "full self-driving", "carplay", "android auto",
    ],
    "ai_ml": [
        "artificial intelligence", "machine learning", "llm", "large language model",
        "gpt", "claude", "gemini", "llama", "neural network", "deep learning",
        "transformer", "fine-tuning", "rag", "retrieval augmented", "embedding",
        "vector database", "inference", "training", "dataset", "prompt",
        "prompt engineering", "agent", "agentic", "reinforcement learning",
        "diffusion model", "stable diffusion", "midjourney", "computer vision",
        "nlp", "natural language processing", "chatbot", "generative ai",
        "foundation model", "multimodal", "ai safety",
    ],
    "space_science": [
        "nasa", "spacex", "rocket", "satellite", "orbit", "iss",
        "international space station", "mars", "moon", "lunar", "artemis",
        "james webb", "telescope", "black hole", "dark matter", "exoplanet",
        "asteroid", "comet", "solar", "space launch", "starship",
        "quantum", "physics", "biology", "genomics", "crispr",
        "climate", "ocean", "energy", "nuclear fusion", "particle",
    ],
    "mobile_gadgets": [
        "iphone", "android", "smartphone", "pixel", "samsung galaxy",
        "oneplus", "nothing phone", "foldable", "snapdragon", "a17",
        "camera system", "5g", "wi-fi 7", "bluetooth", "nfc", "usb-c",
        "wearable", "fitness tracker", "smartwatch", "apple watch",
        "galaxy watch", "airpods", "galaxy buds",
    ],
    "gaming": [
        "gaming", "game", "playstation", "xbox", "nintendo", "pc gaming",
        "gpu", "rtx", "graphics card", "frame rate", "fps", "esports",
        "game engine", "unity", "unreal", "steam", "epic games",
        "xbox game pass", "ps5", "switch 2", "indie game", "aaa",
        "ray tracing", "dlss", "fsr",
    ],
    "startups_business": [
        "startup", "funding", "seed round", "series a", "vc", "venture capital",
        "unicorn", "ipo", "acquisition", "merger", "valuation", "founders",
        "product market fit", "pivot", "burn rate", "runway", "saas metrics",
        "arr", "mrr", "churn", "growth hacking", "b2b", "b2c",
        "accelerator", "y combinator", "techcrunch", "crunchbase",
    ],
    "broadcast_tech": [
        "broadcast", "streaming", "ott", "ip video", "hdr", "hls",
        "live production", "sdi", "ndi", "codec", "h.265", "av1",
        "encoder", "decoder", "playout", "mam", "dam", "workflow",
        "virtual production", "led wall", "xr stage", "remote production",
        "cloud playout", "multiviewer", "newsroom", "teleprompter",
    ],
}

# ── Priority override patterns ──────────────────────────────────────────────
_PRIORITY_PATTERNS: list[tuple[str, Category]] = [
    (r"\b(ransomware|zero.?day|cve-\d|apt\d|phishing campaign)\b", "cybersecurity"),
    (r"\b(llm|gpt-\d|claude \d|gemini \d|llama \d|stable diffusion)\b", "ai_ml"),
    (r"\b(tesla model|rivian r\d|lucid air|mustang mach|f-150 lightning)\b", "evs_automotive"),
    (r"\b(iphone \d+|galaxy s\d+|pixel \d+|snapdragon \d+)\b", "mobile_gadgets"),
    (r"\b(ps\d|xbox series|rtx \d{4}|switch \d|steam deck)\b", "gaming"),
]


def classify_topic(topic: str) -> Category:
    """
    Classify a topic string into a Category.
    Priority order:
      1. Hard regex patterns (named products/CVEs)
      2. Keyword taxonomy scoring (most keyword matches wins)
      3. Default: enterprise_tech
    """
    topic_lower = topic.lower()

    # Priority regex check
    for pattern, cat in _PRIORITY_PATTERNS:
        if re.search(pattern, topic_lower):
            return cat

    # Keyword scoring
    scores: dict[Category, int] = {cat: 0 for cat in _TAXONOMY}
    for cat, keywords in _TAXONOMY.items():
        for kw in keywords:
            if kw in topic_lower:
                # Longer keyword = higher specificity weight
                scores[cat] += len(kw.split())

    best_cat = max(scores, key=lambda c: scores[c])
    if scores[best_cat] > 0:
        return best_cat

    return "enterprise_tech"  # fallback


def get_category_config(category: Category) -> dict:
    """
    Return niche-specific configuration that informs tone, depth,
    structure choices, and high-CPC keyword clusters.
    """
    configs = {
        "cybersecurity": {
            "tone": "authoritative, precise, threat-aware",
            "depth": "high — technical detail required",
            "focus_areas": ["threats", "vulnerabilities", "mitigation", "frameworks", "incident response"],
            "required_sections": ["Executive Summary", "Threat Analysis", "Technical Details",
                                  "Mitigation Strategy", "Detection Indicators", "FAQ"],
            "high_cpc_keywords": ["cybersecurity software", "endpoint protection", "zero trust security",
                                  "managed security services", "cloud security platform", "siem solution"],
            "tone_instruction": "Write like a senior threat intelligence analyst. Be specific about CVE IDs, MITRE ATT&CK techniques, and CVSS scores where relevant. Avoid vague warnings.",
            "avoid": ["generic security advice", "fear-mongering without specifics", "outdated frameworks"],
        },
        "enterprise_tech": {
            "tone": "strategic, ROI-focused, executive-friendly",
            "depth": "high — business case + technical detail",
            "focus_areas": ["ROI", "scalability", "integration", "compliance", "total cost of ownership"],
            "required_sections": ["Executive Summary", "Business Case", "Technical Architecture",
                                  "Implementation Roadmap", "ROI Analysis", "Vendor Comparison", "FAQ"],
            "high_cpc_keywords": ["enterprise software", "cloud migration", "digital transformation",
                                  "SaaS management platform", "IT infrastructure", "ERP system"],
            "tone_instruction": "Write for CTOs and IT directors. Quantify benefits where possible. Include TCO, scalability considerations, and integration complexity.",
            "avoid": ["consumer-level explanations", "oversimplified architecture", "missing cost analysis"],
        },
        "consumer_tech": {
            "tone": "conversational, helpful, buyer-focused",
            "depth": "moderate — practical, decision-enabling",
            "focus_areas": ["specs", "value for money", "real-world performance", "buying decision"],
            "required_sections": ["Quick Verdict", "Key Specs", "Detailed Review",
                                  "Who Should Buy", "Who Should Skip", "Alternatives", "FAQ"],
            "high_cpc_keywords": ["best laptop 2025", "tech buying guide", "product comparison",
                                  "gadget review", "value for money tech"],
            "tone_instruction": "Write like a trusted friend who has used the product. Be specific about real-world performance, not just spec sheets. Give a clear buying verdict.",
            "avoid": ["spec regurgitation", "vague praise", "no real verdict"],
        },
        "evs_automotive": {
            "tone": "analytical, spec-precise, range-focused",
            "depth": "high — technical specs + adoption context",
            "focus_areas": ["range", "charging speed", "real-world performance", "total cost", "OTA updates"],
            "required_sections": ["Overview", "Range & Charging", "Performance Analysis",
                                  "Interior & Technology", "Cost Analysis", "vs Competitors", "FAQ"],
            "high_cpc_keywords": ["best electric car 2025", "EV range comparison", "electric vehicle tax credit",
                                  "home EV charger", "Tesla competitor"],
            "tone_instruction": "Write for EV-curious buyers who want data over hype. Include EPA range vs real-world range, charging curve data, and total 5-year cost of ownership.",
            "avoid": ["hype without data", "ignoring charging infrastructure", "missing price analysis"],
        },
        "ai_ml": {
            "tone": "clear, insight-driven, application-focused",
            "depth": "high — concept + practical application",
            "focus_areas": ["how it works", "practical applications", "limitations", "enterprise use cases", "risks"],
            "required_sections": ["Plain-English Overview", "How It Works", "Real-World Applications",
                                  "Limitations & Risks", "Comparison with Alternatives", "FAQ"],
            "high_cpc_keywords": ["AI software platform", "machine learning tools", "LLM API",
                                  "generative AI enterprise", "AI automation"],
            "tone_instruction": "Explain the concept from first principles, then immediately connect to practical applications. Use analogies for complex concepts. Never assume the reader knows ML jargon.",
            "avoid": ["unexplained jargon", "hype claims", "missing limitations", "no practical use cases"],
        },
        "space_science": {
            "tone": "engaging, context-rich, significance-focused",
            "depth": "moderate-high — explain why it matters",
            "focus_areas": ["scientific significance", "technology involved", "timeline", "broader implications"],
            "required_sections": ["What Happened / What It Is", "The Science Behind It",
                                  "Why This Matters", "What Comes Next", "FAQ"],
            "high_cpc_keywords": ["space technology", "NASA mission", "SpaceX launch",
                                  "astronomy discovery", "science news"],
            "tone_instruction": "Write with the enthusiasm of a science communicator. Explain significance in human terms. Avoid assuming physics background — but don't dumb it down to inaccuracy.",
            "avoid": ["dry reporting", "missing context", "no broader implications"],
        },
        "mobile_gadgets": {
            "tone": "enthusiast-friendly, spec-aware, practical",
            "depth": "moderate — hands-on focused",
            "focus_areas": ["performance", "camera", "battery life", "software", "value"],
            "required_sections": ["Quick Take", "Design & Build", "Display", "Performance",
                                  "Camera System", "Battery & Charging", "Software", "Verdict", "FAQ"],
            "high_cpc_keywords": ["best smartphone 2025", "phone buying guide", "camera phone comparison"],
            "tone_instruction": "Write for gadget enthusiasts who read The Verge. Be specific about benchmark scores, camera samples context, and daily-use impressions.",
            "avoid": ["spec sheet regurgitation", "no real-world context", "missing alternatives"],
        },
        "gaming": {
            "tone": "gamer-native, informed, opinionated",
            "depth": "moderate — gameplay + technical + community",
            "focus_areas": ["gameplay mechanics", "performance", "graphics", "value", "community/longevity"],
            "required_sections": ["Overview", "Gameplay", "Graphics & Performance",
                                  "Content & Value", "Who Is This For", "Verdict", "FAQ"],
            "high_cpc_keywords": ["best gaming GPU 2025", "gaming laptop guide", "PC gaming setup"],
            "tone_instruction": "Write for players who take gaming seriously. Include frame rate data, resolution options, input lag. Don't just describe — evaluate.",
            "avoid": ["plot spoilers without warning", "ignoring technical performance", "vague praise"],
        },
        "startups_business": {
            "tone": "insider, analytical, founder-aware",
            "depth": "high — market context + strategic implications",
            "focus_areas": ["market opportunity", "business model", "competitive landscape", "risks", "investor view"],
            "required_sections": ["The Opportunity", "Business Model Analysis", "Competitive Landscape",
                                  "Risks & Challenges", "Strategic Outlook", "FAQ"],
            "high_cpc_keywords": ["startup funding", "SaaS business model", "venture capital strategy",
                                  "B2B growth strategy", "startup valuation"],
            "tone_instruction": "Write for founders and investors. Use SaaS metrics correctly (ARR, MRR, NRR). Analyse business model sustainability, not just growth.",
            "avoid": ["cheerleading without analysis", "missing competitive context", "no risk assessment"],
        },
        "broadcast_tech": {
            "tone": "industry-specific, workflow-focused, production-aware",
            "depth": "high — technical workflow + business case",
            "focus_areas": ["workflow integration", "signal chain", "latency", "redundancy", "IP vs SDI"],
            "required_sections": ["Overview", "Technical Specifications", "Workflow Integration",
                                  "Advantages & Trade-offs", "Deployment Considerations", "FAQ"],
            "high_cpc_keywords": ["broadcast technology", "IP video production", "live production workflow",
                                  "broadcast automation", "cloud playout"],
            "tone_instruction": "Write for broadcast engineers and production managers. Be specific about codecs, bit rates, latency figures, and protocol compatibility.",
            "avoid": ["consumer-level explanations", "missing technical specs", "ignoring workflow integration"],
        },
    }
    return configs.get(category, configs["enterprise_tech"])
