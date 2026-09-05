#!/usr/bin/env python3
"""
Weekly Deterministic Demand Ledger — Swapp Technologies LLC / Enacted
Founder Eyes Only — Aggregate counts are strictly confidential and private.

Aggregates:
1. Waitlist requests by jurisdiction × topic
2. Feed subscriptions / readership by jurisdiction (Cloudflare Analytics API or unavailable — NEVER estimated)
3. Google Search Console queries (unmet demand)

Zero model calls. Pure deterministic sorting and ranking.
"""

import os
import sys
import json
import csv
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from collections import defaultdict

POSTURE = "Records what changed in enacted land-use law and public water quality. Does not advise, approve, determine, or certify anything."

def fetch_cloudflare_feed_readership():
    """
    Queries Cloudflare GraphQL Analytics API for request counts to /feeds/*
    Only executed if CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID are set.
    Returns (counts_dict, status_message).
    NEVER estimates or invents readership metrics.
    """
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    zone_id = os.environ.get("CLOUDFLARE_ZONE_ID")
    
    if not api_token or not zone_id:
        return None, "Unavailable (pending Cloudflare Analytics API credentials — metric is never estimated)"
        
    start_time = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    query = """
    query GetFeedRequests($zoneTag: String!, $filter: ZoneHttpRequestsAdaptiveGroupsFilter_InputObject) {
      viewer {
        zones(filter: {zoneTag: $zoneTag}) {
          httpRequestsAdaptiveGroups(filter: $filter, limit: 1000) {
            count
            dimensions {
              clientRequestPath
            }
          }
        }
      }
    }
    """
    variables = {
        "zoneTag": zone_id,
        "filter": {
            "datetime_geq": start_time,
            "clientRequestPath_like": "%/feeds/%"
        }
    }
    
    req = urllib.request.Request(
        "https://api.cloudflare.com/client/v4/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("errors"):
                return None, f"Unavailable (Cloudflare API error: {data['errors'][0].get('message')})"
            
            zones = data.get("data", {}).get("viewer", {}).get("zones", [])
            if not zones:
                return None, "Unavailable (zone not found in Cloudflare response)"
                
            groups = zones[0].get("httpRequestsAdaptiveGroups", [])
            jur_counts = defaultdict(int)
            for group in groups:
                path = group.get("dimensions", {}).get("clientRequestPath", "")
                cnt = group.get("count", 0)
                # Parse /feeds/<jurisdiction>/...
                parts = [p for p in path.split("/") if p]
                if "feeds" in parts:
                    f_idx = parts.index("feeds")
                    if len(parts) > f_idx + 1:
                        jur = parts[f_idx + 1]
                        if jur.endswith((".atom", ".json")):
                            jur = "statewide"
                        jur_counts[jur.lower()] += cnt
            return dict(jur_counts), "Active (Cloudflare Analytics API, past 7 days)"
    except Exception as e:
        return None, f"Unavailable (Cloudflare request failed: {e})"

def generate_demand_ledger(data_dir=None, output_path=None):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(base_dir, ".."))
    
    if data_dir is None:
        data_dir = os.path.join(repo_root, "data")
    
    waitlist_file = os.path.join(data_dir, "waitlist.json")
    search_file = os.path.join(data_dir, "search_console_queries.tsv")
    
    # 1. Waitlist ingestion
    waitlist_data = []
    if os.path.exists(waitlist_file):
        try:
            with open(waitlist_file, "r", encoding="utf-8") as f:
                waitlist_data = json.load(f)
        except Exception as e:
            print(f"Warning: Could not parse waitlist.json: {e}")
            
    jur_topic_counts = defaultdict(int)
    jur_topic_details = defaultdict(list)
    for entry in waitlist_data:
        jur = entry.get("jurisdiction", "unspecified").strip().lower()
        topic = entry.get("topic", "unspecified").strip().lower()
        desc = entry.get("change_description", "").strip()
        jur_topic_counts[(jur, topic)] += 1
        if desc:
            jur_topic_details[(jur, topic)].append(desc[:120])
            
    # 2. Feed readership (Cloudflare Analytics or unavailable)
    feed_counts, feed_status = fetch_cloudflare_feed_readership()
    if feed_counts is None:
        feed_counts = {}
            
    # 3. Search Console queries ingestion
    search_queries = []
    if os.path.exists(search_file):
        try:
            with open(search_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    q = row.get("query", "").strip()
                    impressions = int(row.get("impressions", 0))
                    clicks = int(row.get("clicks", 0))
                    if q:
                        search_queries.append((q, impressions, clicks))
            search_queries.sort(key=lambda x: x[1], reverse=True)
        except Exception as e:
            print(f"Warning: Could not parse search_console_queries.tsv: {e}")
            
    # Build Report
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    lines = []
    lines.append(f"# CONFIDENTIAL — FOUNDER EYES ONLY: Weekly Enacted Demand Ledger")
    lines.append(f"**Generated:** {now_iso}  ")
    lines.append(f"**Legal Posture:** {POSTURE}  ")
    lines.append(f"**Privacy Notice:** Aggregate demand counts are strictly private and internal. Never publish or surface publicly.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Waitlist Demand by Jurisdiction × Topic")
    lines.append("")
    lines.append("| Jurisdiction | Topic | Request Count | Sample Interests / Specific Changes |")
    lines.append("| :--- | :--- | :--- | :--- |")
    
    sorted_jt = sorted(jur_topic_counts.items(), key=lambda x: x[1], reverse=True)
    if sorted_jt:
        for (jur, top), count in sorted_jt:
            sample_notes = "; ".join(jur_topic_details[(jur, top)][:2])
            if not sample_notes: sample_notes = "—"
            lines.append(f"| **{jur.title()}** | {top} | {count} | {sample_notes} |")
    else:
        lines.append("| *(None recorded)* | — | 0 | Pre-launch baseline / No incoming records |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. Feed Subscriptions & Readership Signals")
    lines.append(f"**Status:** {feed_status}")
    lines.append("")
    lines.append("| Jurisdiction | Request / Reader Count |")
    lines.append("| :--- | :--- |")
    if feed_counts:
        sorted_feeds = sorted(feed_counts.items(), key=lambda x: x[1], reverse=True)
        for jur, cnt in sorted_feeds:
            lines.append(f"| **{jur.title()}** | {cnt} |")
    else:
        lines.append("| *(All jurisdictions)* | Unavailable (Cloudflare Analytics API credentials required — never estimated) |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. Search Console Unmet Demand Signals")
    lines.append("")
    lines.append("| Query | Impressions | Clicks | Inferred Intent |")
    lines.append("| :--- | :--- | :--- | :--- |")
    if search_queries:
        for q, imp, clk in search_queries[:25]:
            lines.append(f"| {q} | {imp} | {clk} | Primary search lookup |")
    else:
        lines.append("| *(No search data)* | 0 | 0 | Pre-launch baseline |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 4. Deterministic Ingestion Priority Ranking")
    lines.append("Prioritization score = `Waitlist Requests × 3 + Feed Requests × 2 + Search Impressions × 0.1`")
    lines.append("*(Note: When a signal is unavailable, its term is 0; metrics are never imputed.)*")
    lines.append("")
    
    # Calculate score
    jur_scores = defaultdict(float)
    for (jur, _), cnt in jur_topic_counts.items():
        jur_scores[jur] += cnt * 3.0
    for jur, cnt in feed_counts.items():
        jur_scores[jur] += cnt * 2.0
    for q, imp, _ in search_queries:
        for jur in jur_scores.keys():
            if jur in q.lower():
                jur_scores[jur] += imp * 0.1
                
    sorted_priorities = sorted(jur_scores.items(), key=lambda x: x[1], reverse=True)
    lines.append("| Rank | Jurisdiction | Priority Score | Primary Topic Demand |")
    lines.append("| :--- | :--- | :--- | :--- |")
    if sorted_priorities:
        for rank, (jur, score) in enumerate(sorted_priorities, 1):
            topics = [top for (j, top) in jur_topic_counts.keys() if j == jur]
            t_str = ", ".join(topics) if topics else "general"
            lines.append(f"| {rank} | **{jur.title()}** | {score:.1f} | {t_str} |")
    else:
        lines.append("| 1 | *Corpus Baseline* | 0.0 | Maintain existing Maryland populated jurisdictions |")
    lines.append("")
    lines.append("---")
    lines.append("*Report generated deterministically by Enacted Demand Engine.*")
    
    report_content = "\n".join(lines) + "\n"
    
    if output_path is None:
        reports_dir = os.path.join(repo_root, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        output_path = os.path.join(reports_dir, f"demand_ledger_{report_date}.md")
        
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"Demand ledger compiled successfully: {output_path}")
    return output_path

if __name__ == "__main__":
    generate_demand_ledger()
