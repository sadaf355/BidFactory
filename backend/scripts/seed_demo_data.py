#!/usr/bin/env python3
"""
Optional demo convenience script — seeds a running BidFactory backend with
a small fictional company, a handful of knowledge-base documents, and one
example RFP, entirely through the same public HTTP API a real user's own
data goes through. Nothing here is read by the pipeline (retrieval, agents,
LLM prompts) directly; delete the "Acme Cloud Solutions" documents from the
Knowledge Base page whenever you're ready to add your own.

Usage:
    cd backend
    uvicorn app.main:app --reload &      # backend must already be running
    python scripts/seed_demo_data.py [--base-url http://127.0.0.1:8000]
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid

COMPANY_NAME = "Acme Cloud Solutions"

KB_DOCS = [
    ("certifications", "ISO_27001.md",
     "Acme Cloud Solutions holds active ISO/IEC 27001:2022 certification, "
     "audited annually by an accredited third party."),
    ("security_policies", "Encryption_Standard.md",
     "All customer data in transit is encrypted using TLS 1.2 or higher. "
     "All customer data at rest is encrypted using AES-256. Fleet-wide "
     "TLS 1.3 support is not yet available."),
    ("support_policies", "SLA_Policy.md",
     "Acme Cloud Solutions provides a 99.9% uptime SLA for Enterprise "
     "customers, with 24/7 technical support and a 30-minute critical "
     "response target. Does not currently offer a guaranteed 99.99% "
     "uptime SLA."),
    ("case_studies", "Healthcare_Case_Study.md",
     "Acme Cloud Solutions delivered a data platform for a regional "
     "healthcare network, including role-based access control and full "
     "audit logging. This engagement does not constitute FedRAMP "
     "authorization or certification."),
    ("technical_docs", "API_Platform.md",
     "The Acme platform exposes REST APIs secured with OAuth 2.0 and "
     "supports role-based access control (RBAC) down to the individual "
     "resource level."),
    ("pricing", "Pricing_Overview.md",
     "Enterprise pricing is quoted per seat with volume discounts "
     "starting at 50 seats. Implementation services are billed "
     "separately on a fixed-fee basis."),
]

SAMPLE_REQUIREMENTS = [
    "Vendor must have ISO 27001 certification.",
    "All customer data in transit must be encrypted using TLS 1.3 or higher.",
    "All customer data at rest must be encrypted using AES-256 or stronger.",
    "The system must enforce Role-Based Access Control (RBAC).",
    "Vendor must provide 24/7 technical support.",
    "Vendor must provide a 99.99% uptime SLA.",
    "Vendor must have FedRAMP authorization.",
    "Vendor must support REST APIs.",
    "Vendor must provide a detailed pricing structure.",
]


def _request(base_url, method, path, json_body=None, multipart=None):
    url = base_url.rstrip("/") + path
    headers = {}
    data = None

    if multipart is not None:
        boundary = uuid.uuid4().hex
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        parts = []
        for field_name, value in multipart["fields"].items():
            parts.append(f"--{boundary}\r\n"
                         f'Content-Disposition: form-data; name="{field_name}"\r\n\r\n'
                         f"{value}\r\n")
        filename, content = multipart["file"]
        parts.append(f"--{boundary}\r\n"
                     f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                     f"Content-Type: text/markdown\r\n\r\n")
        body = "".join(parts).encode("utf-8") + content.encode("utf-8") + f"\r\n--{boundary}--\r\n".encode("utf-8")
        data = body
    elif json_body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(json_body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"Request failed: {method} {url} — {e}", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    args = parser.parse_args()

    print(f"Seeding {args.base_url} with demo data for '{COMPANY_NAME}'...")

    _request(args.base_url, "PUT", "/company", json_body={"name": COMPANY_NAME})
    print(f"  Set company name to '{COMPANY_NAME}'")

    for category, filename, text in KB_DOCS:
        _request(args.base_url, "POST", "/knowledge-base/upload",
                  multipart={"fields": {"category": category}, "file": (filename, text)})
        print(f"  Uploaded {category}/{filename}")

    result = _request(args.base_url, "POST", "/analysis/batch", json_body={"requirements": SAMPLE_REQUIREMENTS})
    summary = result["summary"]
    print(f"  Analyzed {summary['total']} example requirements: "
          f"{summary['pass']} PASS, {summary['partial']} PARTIAL, {summary['missing']} MISSING")

    bid = _request(args.base_url, "POST", "/bids/assemble", json_body={
        "analysis_results": result["results"],
        "company_name": COMPANY_NAME,
        "title": "Sample Cloud Services RFP — Response",
    })
    print(f"  Assembled bid {bid['id']} ({len(bid['sections'].get('Open Gaps', []))} item(s) routed to Open Gaps)")
    print("\nDone. Note: this seeds the backend (knowledge base + a persisted bid) — "
          "the app's Bids page is per-browser-session, so open the frontend and use "
          "Settings → Load Sample Data instead if you want it to show up there too.")


if __name__ == "__main__":
    main()
