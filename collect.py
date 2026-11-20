#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2)
"""Collect monthly counts of Algora-funded GitHub bounty issues and claim PRs.

Standard library only. Uses the public GitHub search API without a token, so it
paces itself to stay under the unauthenticated search limit (10 requests/minute).

Outputs (in --out-dir):
  counts.jsonl  one line per (month, series): total_count from GitHub search
  issues.jsonl  one line per sampled bounty issue (up to --pages x 100 per month)
  meta.json     collection time, query templates, request log summary
"""
import argparse
import calendar
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://api.github.com/search/issues"
UA = "munimtechnologies-bounty-flood/0.1 (+https://github.com/munimtechnologies/bounty-flood)"

# Series counted every month. {r} is replaced by a created:YYYY-MM-DD..YYYY-MM-DD range.
# app/algora-pbc is the GitHub App that posts Algora's bounty and claim comments, so
# "commenter:app/algora-pbc" selects issues and PRs where Algora's bot really acted
# (labels alone can be copied by anyone, including bounty farms).
SERIES = {
    "bot_issues": "is:issue commenter:app/algora-pbc created:{r}",
    "bot_prs": "is:pr commenter:app/algora-pbc created:{r}",
    "bot_prs_merged": "is:pr is:merged commenter:app/algora-pbc created:{r}",
    "label_issues": 'is:issue label:"\U0001F48E Bounty" created:{r}',
}
SAMPLE_QUERY = "is:issue commenter:app/algora-pbc created:{r}"


def months(start, end):
    """Yield (year, month) from 'YYYY-MM' start to end inclusive."""
    y, m = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    while (y, m) <= (ey, em):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def month_key(y, m):
    return f"{y:04d}-{m:02d}"


def month_range(y, m):
    last = calendar.monthrange(y, m)[1]
    return f"{y:04d}-{m:02d}-01..{y:04d}-{m:02d}-{last:02d}"


def build_url(q, per_page=1, page=1, sort=None, order=None):
    params = {"q": q, "per_page": str(per_page), "page": str(page)}
    if sort:
        params["sort"] = sort
    if order:
        params["order"] = order
    return API + "?" + urllib.parse.urlencode(params)


def parse_item(item, month):
    """Keep only the fields the analysis needs (no personal data beyond public logins)."""
    repo_url = item.get("repository_url") or ""
    repo = "/".join(repo_url.rstrip("/").split("/")[-2:]) if repo_url else ""
    labels = [l.get("name", "") if isinstance(l, dict) else str(l) for l in item.get("labels") or []]
    return {
        "month": month,
        "repo": repo,
        "number": item.get("number"),
        "created_at": item.get("created_at"),
        "closed_at": item.get("closed_at"),
        "state": item.get("state"),
        "state_reason": item.get("state_reason"),
        "comments": item.get("comments"),
        "labels": labels,
        "author_association": item.get("author_association"),
    }


class Client:
    def __init__(self, min_interval=6.5, max_retries=8, log=None):
        self.min_interval = min_interval
        self.max_retries = max_retries
        self.last = 0.0
        self.requests = 0
        self.retries = 0
        self.log = log or sys.stderr

    def get(self, url):
        for attempt in range(self.max_retries + 1):
            wait = self.min_interval - (time.time() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.time()
            self.requests += 1
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            })
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code in (403, 429) or e.code >= 500:
                    self.retries += 1
                    reset = e.headers.get("X-RateLimit-Reset") if e.headers else None
                    retry_after = e.headers.get("Retry-After") if e.headers else None
                    if retry_after and retry_after.isdigit():
                        sleep_s = int(retry_after) + 1
                    elif reset and reset.isdigit():
                        sleep_s = max(5, int(reset) - int(time.time()) + 2)
                    else:
                        sleep_s = min(300, 15 * (attempt + 1))
                    print(f"HTTP {e.code} on attempt {attempt}; sleeping {sleep_s}s", file=self.log)
                    time.sleep(min(sleep_s, 400))
                    continue
                raise
            except (urllib.error.URLError, TimeoutError) as e:
                self.retries += 1
                print(f"network error {e!r}; retrying", file=self.log)
                time.sleep(10 * (attempt + 1))
        raise RuntimeError(f"gave up after {self.max_retries} retries: {url}")


def collect(out_dir, start, end, pages, client):
    os.makedirs(out_dir, exist_ok=True)
    counts_path = os.path.join(out_dir, "counts.jsonl")
    issues_path = os.path.join(out_dir, "issues.jsonl")
    with open(counts_path, "w", encoding="utf-8") as fc, open(issues_path, "w", encoding="utf-8") as fi:
        for y, m in months(start, end):
            key, r = month_key(y, m), month_range(y, m)
            bot_issue_total = None
            for name, tmpl in SERIES.items():
                q = tmpl.format(r=r)
                data = client.get(build_url(q))
                total = int(data.get("total_count", 0))
                if name == "bot_issues":
                    bot_issue_total = total
                fc.write(json.dumps({"month": key, "series": name, "q": q, "total_count": total,
                                     "incomplete": bool(data.get("incomplete_results"))}) + "\n")
                fc.flush()
                print(f"{key} {name} {total}", file=client.log)
            n_pages = min(pages, (bot_issue_total + 99) // 100) if bot_issue_total else 0
            for p in range(1, n_pages + 1):
                q = SAMPLE_QUERY.format(r=r)
                data = client.get(build_url(q, per_page=100, page=p, sort="created", order="asc"))
                for item in data.get("items") or []:
                    fi.write(json.dumps(parse_item(item, key)) + "\n")
                fi.flush()
    return counts_path, issues_path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--start", default="2022-01")
    ap.add_argument("--end", default="2026-10")
    ap.add_argument("--pages", type=int, default=3, help="max pages of 100 sampled bounty issues per month")
    ap.add_argument("--min-interval", type=float, default=6.5)
    a = ap.parse_args(argv)
    t0 = datetime.now(timezone.utc).isoformat()
    client = Client(min_interval=a.min_interval)
    collect(a.out_dir, a.start, a.end, a.pages, client)
    meta = {"collected_started": t0, "collected_finished": datetime.now(timezone.utc).isoformat(),
            "start": a.start, "end": a.end, "pages": a.pages, "series": SERIES,
            "sample_query": SAMPLE_QUERY, "requests": client.requests, "retries": client.retries}
    with open(os.path.join(a.out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
