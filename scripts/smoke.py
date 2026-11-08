"""Read-only local health/gateway checks; does not claim database functionality."""
import argparse
import json
import urllib.error
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("--expect-database-unavailable", action="store_true")
args = parser.parse_args()
checks = [
    ("http://127.0.0.1:8000/health", None, 200),
    ("http://127.0.0.1:5080/health", None, 200),
    ("http://127.0.0.1:5080/health/ready", None, 503 if args.expect_database_unavailable else 200),
    ("http://127.0.0.1:4200/", None, 200),
    ("http://127.0.0.1:5080/api/v1/knowledge/search", {"query": "risk", "limit": 99}, 400),
    ("http://127.0.0.1:4200/api/v1/knowledge/search", {"query": "risk", "limit": 99}, 400),
]
if args.expect_database_unavailable:
    checks.append(("http://127.0.0.1:5080/api/v1/knowledge/documents", None, 503))

for url, body, expected in checks:
    request = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
    print(json.dumps({"url": url, "actual": status, "expected": expected}))
    if status != expected:
        raise SystemExit(1)
