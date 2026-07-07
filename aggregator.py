#!/usr/bin/env python3
"""Build a static X market-intelligence feed using the local OpenCLI login.

Vercel cannot reuse the user's local Chrome/X session, so this script runs on
the trusted local machine and writes data.json for the deployed static app.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_LIMIT = 8
OPENCLI_ENV = Path("/Users/vic/Documents/agent_reach/agent-reach/agent-reach-env.sh")


@dataclass(frozen=True)
class Channel:
    id: str
    handle: str
    name: str
    lane: str
    note: str


CHANNELS = [
    Channel("serenity", "aleabitoreddit", "Serenity / 白毛股神", "AI supply chain", "AI/semi chokepoints, memory, photonics, data centers"),
    Channel("wizard", "0xCryptoWizard", "0xWizard / 巫师", "Crypto + market regime", "Speculation cycles, AI equity risk, crypto narratives"),
    Channel("leopold", "leopoldasch", "Leopold Aschenbrenner", "AI frontier", "AGI, AI infrastructure, Situational Awareness"),
    Channel("qinba", "qinbafrank", "qinbafrank", "Macro + AI", "Macro liquidity, CPI/FOMC, AI ROI, semis"),
    Channel("trumoo", "xiaomustock", "川沐 / Trumoo", "Semis trading", "AI stocks, memory, Korea semis, options tone"),
    Channel("maojie", "maojietrading", "猫姐美股交易", "US equity trading", "Rotation, flows, HOOD, tactical market notes"),
    Channel("morgan", "morganhousel", "Morgan Housel", "Investor psychology", "Long-term thinking, behavior, financial advice"),
    Channel("bilello", "charliebilello", "Charlie Bilello", "Market data", "Charts, macro snapshots, cross-asset data"),
    Channel("herman", "ShanghaoJin", "Herman Jin", "FICC + tech", "Macro, AI infra, crypto-to-equity rotation"),
    Channel("trumptracker", "TrumpsPortfolio", "Trump Portfolio Tracker", "Policy trades", "Trump-related disclosures, policy-linked equities"),
    Channel("okbro", "artinmemes", "美股OK哥", "Asia semis", "Korea memory, ADRs, supply-chain commentary"),
    Channel("whales", "unusual_whales", "unusual_whales", "Market tape", "Breaking market/policy headlines and options flow"),
    Channel("kindig", "Beth_Kindig", "Beth Kindig", "AI equities", "AI infrastructure, semis, data centers"),
]


TICKER_RE = re.compile(r"(?<![A-Z0-9])\$[A-Z][A-Z0-9.\-]{1,9}\b")
URL_RE = re.compile(r"https?://\S+")
TAG_RULES = [
    ("AI", ("AI", "大模型", "算力", "token", "AGI", "model")),
    ("Memory", ("HBM", "DRAM", "NAND", "memory", "存储", "海力士", "三星", "Micron", "美光")),
    ("Semis", ("semiconductor", "半导体", "GPU", "CPU", "ASIC", "NVDA", "AMD", "MRVL", "AVGO")),
    ("Data centers", ("data center", "datacenter", "DC", "数据中心", "power", "电力", "colo", "neocloud")),
    ("Macro", ("CPI", "FOMC", "Fed", "liquidity", "流动性", "Treasury", "TGA", "unemployment")),
    ("Crypto", ("BTC", "Bitcoin", "crypto", "币圈", "大饼", "ETH")),
    ("Policy", ("Trump", "ICE", "SEC", "White House", "特朗普", "government")),
    ("Risk", ("short", "leverage", "杠杆", "泡沫", "risk", "down", "跌", "回撤")),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh X Market Radar data.json")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="tweets per channel")
    parser.add_argument("--output", default=str(ROOT / "data.json"), help="output JSON path")
    return parser.parse_args()


def parse_created_at(value: str) -> tuple[str, int]:
    if not value:
        return "", 0
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return "", 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.isoformat(), int(dt.timestamp())


def command_for(handle: str, limit: int) -> str:
    env_prefix = f"source {OPENCLI_ENV} && " if OPENCLI_ENV.exists() else ""
    return (
        f"{env_prefix}OPENCLI_BROWSER_COMMAND_TIMEOUT=180000 "
        f"opencli twitter tweets {handle} --limit {limit} -f json"
    )


def fetch_channel(channel: Channel, limit: int) -> tuple[list[dict], str | None]:
    cmd = command_for(channel.handle, limit)
    proc = subprocess.run(
        ["zsh", "-lc", cmd],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=240,
    )
    if proc.returncode != 0:
        return [], (proc.stderr or proc.stdout).strip()
    try:
        rows = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return [], f"JSON decode failed: {exc}"
    return [normalize_tweet(channel, row) for row in rows], None


def summarize(text: str, max_len: int = 280) -> str:
    clean = URL_RE.sub("", text or "")
    clean = re.sub(r"\s+", " ", clean).strip()
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 1].rstrip() + "…"


def tags_for(text: str) -> list[str]:
    lowered = text.lower()
    tags = []
    for tag, needles in TAG_RULES:
        if any(needle.lower() in lowered for needle in needles):
            tags.append(tag)
    return tags[:5]


def normalize_tweet(channel: Channel, row: dict) -> dict:
    text = row.get("text", "") or ""
    published, published_ts = parse_created_at(row.get("created_at", ""))
    tickers = sorted(set(TICKER_RE.findall(text)))
    views = int(row.get("views") or 0)
    likes = int(row.get("likes") or 0)
    retweets = int(row.get("retweets") or 0)
    replies = int(row.get("replies") or 0)
    hot_score = likes * 2 + retweets * 5 + replies + min(views // 1000, 500)
    return {
        "id": str(row.get("id") or ""),
        "title": summarize(text, 120),
        "summary": summarize(text),
        "link": row.get("url") or f"https://x.com/{channel.handle}",
        "source": channel.name,
        "source_id": channel.id,
        "handle": channel.handle,
        "lane": channel.lane,
        "published": published,
        "published_ts": published_ts,
        "metrics": {
            "likes": likes,
            "retweets": retweets,
            "replies": replies,
            "views": views,
            "hot_score": hot_score,
        },
        "categories": tags_for(text),
        "tickers": tickers[:8],
        "is_retweet": bool(row.get("is_retweet")),
        "has_media": bool(row.get("has_media")),
        "media": (row.get("media_posters") or row.get("media_urls") or [])[:2],
        "quoted_tweet": row.get("quoted_tweet"),
    }


def build_payload(limit: int) -> dict:
    all_items: list[dict] = []
    errors: dict[str, str] = {}
    for channel in CHANNELS:
        print(f"Fetching @{channel.handle}...", file=sys.stderr)
        items, error = fetch_channel(channel, limit)
        all_items.extend(items)
        if error:
            errors[channel.id] = error

    seen = set()
    articles = []
    for item in sorted(all_items, key=lambda x: x.get("published_ts", 0), reverse=True):
        key = item["link"] or item["id"]
        if not key or key in seen:
            continue
        seen.add(key)
        articles.append(item)

    counts = {channel.id: 0 for channel in CHANNELS}
    for item in articles:
        counts[item["source_id"]] = counts.get(item["source_id"], 0) + 1

    generated = datetime.now(timezone.utc)
    return {
        "schema_version": 1,
        "generated_at": generated.isoformat(),
        "generated_ts": int(generated.timestamp()),
        "articles": articles,
        "sources": [
            {**asdict(channel), "count": counts.get(channel.id, 0), "url": f"https://x.com/{channel.handle}"}
            for channel in CHANNELS
        ],
        "errors": errors,
    }


def main() -> int:
    args = parse_args()
    payload = build_payload(args.limit)
    out = Path(args.output)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload['articles'])} tweets to {out}")
    if payload["errors"]:
        print("Completed with channel errors:", file=sys.stderr)
        for source_id, error in payload["errors"].items():
            print(f"- {source_id}: {error[:300]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
