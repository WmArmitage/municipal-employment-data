#!/usr/bin/env python3
"""
rediscover_employment_links.py

Attempts to rediscover Employment Page URLs (and optionally Application Form URLs)
when the current Employment Page URL is broken (404/soft-404/errors).

Strategy:
1) Use Town Website homepage as the anchor.
2) Try common paths: /employment, /jobs, /careers, etc.
3) Crawl homepage links, score candidates by keywords and path hints.
4) Prefer same-domain employment pages, but also detect common ATS vendors.
5) If a new employment page is found, update:
   - Employment Page URL
   - employment_url_change_reason, employment_url_confidence
6) Optionally scan the employment page for a likely "Application" PDF and update:
   - Application Form URL (+ metadata)

Inputs:
- JSON file containing list of records
Output:
- Updated JSON
- CSV report of towns changed / not found / needs review

Usage:
  python rediscover_employment_links.py input.json output.json rediscovery_report.csv
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from pathlib import Path



# -------------------- Config --------------------
TIMEOUT_SECS = 25
VERIFY_TLS = True
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Throttle between requests to the same town (be polite)
SLEEP_BETWEEN_REQUESTS_SECS = 0.25

# Only attempt rediscovery if current employment URL looks broken like these:
REDISCOVER_IF_STATUS_IN = {404, 410, None, -1}  # None/-1 means errors/unset
REDISCOVER_IF_SOFT404_TRUE = True

# Do NOT rewrite canonical URLs for statuses that often mean bot-blocking
DO_NOT_REWRITE_IF_STATUS_IN = {401, 403}

# Common candidate paths to try first (fast wins)
COMMON_PATHS = [
    "/employment",
    "/employment-opportunities",
    "/jobs",
    "/job-opportunities",
    "/careers",
    "/career-opportunities",
    "/human-resources",
    "/departments/human-resources",
    "/government/departments/human-resources",
]

# Keywords to look for in link text/href
KEYWORDS = [
    "employment", "job", "jobs", "ca
