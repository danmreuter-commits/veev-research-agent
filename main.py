#!/usr/bin/env python3
"""
VEEV Research Agent — entry point.

Scans VC firm activity and the broader insurtech market for competitive
developments relevant to Guidewire (GWRE), then sends a ≤100-word daily
email brief.

Usage
-----
Run once (now):
    python main.py

Run on a daily schedule (8 AM by default):
    python main.py --schedule
    python main.py --schedule --time 07:30

Smoke-test email formatting with mock data:
    python main.py --test-email

Override the default lookback window:
    python main.py --lookback-days 3
"""

import argparse
import logging
import sys
import time
from datetime import datetime

import schedule

import config
from agent.database import save_daily_record
from agent.emailer import generate_digest, send_digest
from agent.researcher import run_research
from agent.state import filter_new_findings

# ── Logging setup ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("gwre-agent")


# ── Daily job ─────────────────────────────────────────────────────────────────

def run_daily_job() -> None:
    """Full pipeline: research → dedup → digest → email."""
    start = datetime.now()
    logger.info("=" * 60)
    logger.info("VEEV Research Agent — daily job started %s", start.strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)

    try:
        # 1. Research
        logger.info("Phase 1/3 — Running competitive intelligence research …")
        raw_findings = run_research()
        if not raw_findings:
            logger.info("No findings returned from research phase.")

        # 2. Deduplicate
        logger.info("Phase 2/3 — Deduplicating against previously sent items …")
        new_findings = filter_new_findings(raw_findings)

        # 3. Generate digest text (shared by email + database)
        logger.info("Phase 3/3 — Generating digest and sending email …")
        digest_text = generate_digest(new_findings)
        send_digest(new_findings, digest_text)

        # 4. Save to Airtable (no-op if AIRTABLE_API_KEY not configured)
        logger.info("Phase 4/4 — Saving record to database …")
        save_daily_record(new_findings, digest_text)

        elapsed = (datetime.now() - start).total_seconds()
        logger.info("Job complete in %.1f s | %d new finding(s) in digest", elapsed, len(new_findings))

    except KeyboardInterrupt:
        raise
    except Exception:
        logger.exception("Job failed with unhandled exception")
        raise


# ── Mock data for smoke tests ─────────────────────────────────────────────────

_MOCK_FINDINGS = [
    {
        "company": "Duck Creek Technologies",
        "type": "product",
        "relevance": "HIGH",
        "vc_firm": "Vista Equity",
        "description": (
            "Launched Duck Creek OnDemand v24 with an embedded AI claims-triage engine "
            "targeting mid-market P&C carriers, directly competing with Guidewire ClaimCenter."
        ),
        "source": "https://duckcreek.com/press/v24-launch",
        "found_at": datetime.now().isoformat(),
    },
    {
        "company": "Socotra",
        "type": "investment",
        "relevance": "HIGH",
        "vc_firm": "TCV",
        "description": (
            "Raised $60M Series C led by TCV to expand its API-first policy administration "
            "platform; now serving 35 carriers replacing legacy Guidewire installs."
        ),
        "source": "https://techcrunch.com/socotra-series-c",
        "found_at": datetime.now().isoformat(),
    },
    {
        "company": "Shift Technology",
        "type": "partnership",
        "relevance": "MEDIUM",
        "vc_firm": "N/A",
        "description": (
            "Signed a 5-year claims-automation deal with USAA covering 12M policies; "
            "CEO hinted at plans to launch a full claims-management module in H2 2026."
        ),
        "source": "https://shift-technology.com/news/usaa-deal",
        "found_at": datetime.now().isoformat(),
    },
]


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="GWRE Competitive Intelligence Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run on a daily schedule instead of once.",
    )
    parser.add_argument(
        "--time",
        default="08:00",
        metavar="HH:MM",
        help="Time to run the daily job when --schedule is set (default: 08:00).",
    )
    parser.add_argument(
        "--test-email",
        action="store_true",
        help="Send a test email using mock findings (skips live research).",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=None,
        help="Override LOOKBACK_DAYS from config (default: 7).",
    )
    args = parser.parse_args()

    # Validate config first
    config.validate()

    # Override lookback if requested
    if args.lookback_days is not None:
        config.LOOKBACK_DAYS = args.lookback_days
        logger.info("Lookback window set to %d days", config.LOOKBACK_DAYS)

    # ── Test-email mode ──
    if args.test_email:
        logger.info("TEST-EMAIL mode — sending mock digest (no live research)")
        send_digest(_MOCK_FINDINGS)
        return

    # ── Scheduled mode ──
    if args.schedule:
        logger.info("Scheduling daily job at %s (local time)", args.time)
        schedule.every().day.at(args.time).do(run_daily_job)

        # Run once immediately so the first digest doesn't wait until tomorrow
        logger.info("Running immediately before entering schedule loop …")
        run_daily_job()

        logger.info("Entering schedule loop. Press Ctrl-C to stop.")
        while True:
            schedule.run_pending()
            time.sleep(30)

    # ── One-shot mode (default) ──
    else:
        run_daily_job()


if __name__ == "__main__":
    main()
