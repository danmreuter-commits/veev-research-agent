import logging, time
from datetime import datetime, timedelta
import anthropic, config
from data.competitors import COMPETITOR_DOMAIN_KEYWORDS, DIRECT_COMPETITOR_NAMES, INDIRECT_COMPETITOR_NAMES

logger = logging.getLogger(__name__)

_SEARCH_SYSTEM = """\
You are a competitive intelligence analyst for Veeva Systems (VEEV), \
the #1 cloud platform for the global life sciences industry (pharma CRM, regulatory, clinical, quality).

DIRECT competitors: Salesforce Life Sciences Cloud, IQVIA OCE, Medidata (Dassault), \
Oracle Health Sciences, OpenText Documentum, Model N, Benchling, Dotmatics.

INDIRECT competitors: Microsoft Cloud for Life Sciences, Palantir pharma, \
Unlearn.AI, Deep 6 AI, Saama Technologies, AI-native clinical trial platforms.

For each finding output one line:
FINDING|||[Company]|||[investment|product|metrics|partnership|platform_shift|vc_signal]|||[HIGH|MEDIUM]|||[VC firm or N/A]|||[One sentence description]|||[Source URL]

HIGH: direct competitor funding/product/major pharma win; large pharma migrating from Veeva;
AI-native platform gaining clinical or regulatory traction; Salesforce/Microsoft life sciences launch.
MEDIUM: life sciences SaaS Series B+; pharma tech partnership; VC thesis on pharma tech disruption.
Skip LOW. When done: BLOCK_COMPLETE
"""

def _date_range():
    today = datetime.now()
    return f"{(today - timedelta(days=7)).strftime('%B %d')}-{today.strftime('%B %d, %Y')}"

_SEARCH_BLOCKS = [
    {"name": "direct_competitors", "prompt_template": "Search for news from the past 7 days ({date_range}) about Veeva direct competitors:\n- Salesforce Life Sciences Cloud / Health Cloud: new features, pharma customer wins, pricing\n- IQVIA OCE: product launches, pharma CRM customer announcements, partnerships\n- Medidata (Dassault): clinical platform news, eTMF/CTMS product updates\n- Oracle Health Sciences: clinical trial software, safety database news\n- OpenText Documentum Life Sciences: regulatory/quality content management news\n- Model N (MODN): earnings, product, pharma customer wins\n- Benchling: funding, product expansion, new biotech/pharma customers\n- Dotmatics: funding, product news, acquisitions\nOutput all HIGH and MEDIUM FINDING||| lines, then: BLOCK_COMPLETE"},
    {"name": "ai_lifesciences_and_vc", "prompt_template": "Search for news from the past 7 days ({date_range}) about:\nPART A - AI platforms expanding into life sciences:\n- Microsoft Cloud for Life Sciences: new features, pharma customer announcements\n- Palantir pharma / clinical analytics: new deals, product news\n- Unlearn.AI, Deep 6 AI, Saama Technologies: funding, product launches, partnerships\n- AI clinical trial platform: funding round OR product launch 2026\n- AI regulatory submission software: new product OR funding 2026\nPART B - VC investments in life sciences technology:\n- Search: Insight Partners OR General Catalyst life sciences software investment 2026\n- Search: Bessemer OR Andreessen Horowitz pharma technology OR biotech software 2026\n- Search: NEA OR Lightspeed clinical trial OR regulatory tech 2026\n- Search: GV OR Sequoia digital health OR pharma cloud platform 2026\nOutput all HIGH and MEDIUM FINDING||| lines, then: BLOCK_COMPLETE"},
    {"name": "market_signals", "prompt_template": "Search for news from the past 7 days ({date_range}) about broader life sciences technology market signals:\n- pharma software Series B OR C OR D 2026\n- clinical trial management OR regulatory submission software funding 2026\n- pharma company replaced OR migrated from Veeva 2026\n- new life sciences cloud platform raised funding {month_year}\n- Veeva competitor announcement {month_year}\n- VC blog pharma technology OR clinical software investment thesis 2026\nAlso: Certinia life sciences, Castor EDC, Medrio EDC, Lorenz regulatory software news.\nOutput all HIGH and MEDIUM FINDING||| lines, then: BLOCK_COMPLETE"},
]

def _parse_findings(text):
    findings = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("FINDING|||"):
            continue
        parts = line.split("|||")
        if len(parts) < 7:
            continue
        findings.append({"company": parts[1].strip(), "type": parts[2].strip().lower(), "relevance": parts[3].strip().upper(), "vc_firm": parts[4].strip(), "description": parts[5].strip(), "source": parts[6].strip(), "found_at": datetime.now().isoformat()})
    return findings

def _run_block(client, block):
    user_prompt = block["prompt_template"].format(date_range=_date_range(), month_year=datetime.now().strftime("%B %Y"))
    messages = [{"role": "user", "content": user_prompt}]
    accumulated = ""
    continuations = 0
    while continuations <= 1:
        response = client.messages.create(model="claude-sonnet-4-6", max_tokens=1500, system=_SEARCH_SYSTEM, tools=[{"type": "web_search_20260209", "name": "web_search"}], messages=messages)
        for cb in response.content:
            if hasattr(cb, "text"):
                accumulated += cb.text + "\n"
        if response.stop_reason == "end_turn":
            break
        elif response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continuations += 1
        else:
            break
    return _parse_findings(accumulated)

BLOCK_PAUSE_SECONDS = 15

def run_research():
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, timeout=180.0)
    all_findings = []
    for i, block in enumerate(_SEARCH_BLOCKS):
        logger.info("Search block %d/%d - %s", i + 1, len(_SEARCH_BLOCKS), block["name"])
        try:
            findings = _run_block(client, block)
            all_findings.extend(findings)
            logger.info("  -> %d finding(s)", len(findings))
        except anthropic.RateLimitError:
            logger.warning("Rate limit on '%s' - waiting 60s", block["name"])
            time.sleep(60)
        except Exception as exc:
            logger.error("Block '%s' failed: %s", block["name"], exc)
        if i < len(_SEARCH_BLOCKS) - 1:
            time.sleep(BLOCK_PAUSE_SECONDS)
    seen = set()
    deduped = []
    for f in all_findings:
        key = f"{f['company'].lower()}|{f['type'].lower()}"
        if key not in seen:
            seen.add(key)
            deduped.append(f)
    deduped.sort(key=lambda f: (0 if f.get("relevance") == "HIGH" else 1))
    logger.info("Research complete - %d unique findings", len(deduped))
    return deduped
