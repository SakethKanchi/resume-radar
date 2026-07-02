#!/usr/bin/env python3
"""Reproduce the GitHub enrichment that hiring-agent runs on a candidate.

hiring-agent (interviewstreet/hiring-agent) does NOT just read the resume text.
It extracts the GitHub username from the resume, calls the GitHub REST API, and
classifies every repo. That classification is what caps the open_source score.
This script reproduces that step exactly so a candidate can see what the agent
sees, using only the Python standard library (no pip install needed).

Rules reproduced from github.py in the upstream repo:
  - Skip forks whose forks_count < 5.
  - project_type = "open_source" if a repo has >1 contributor, else "self_project".
  - A repo is only an eligible "top project" if the candidate's own commit
    count on it is >= 4.
  - If EVERY repo is self_project, the rubric caps open_source at ~10/35.

Usage:
    python scripts/github_enrich.py <github_username_or_url> [--token TOKEN]

Set a token (or the GITHUB_TOKEN env var) to raise the API limit from 60/hr to
5000/hr. Without one, the script still works but may hit the limit on large
profiles; it degrades gracefully and reports how many repos it inspected.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"
# Inspect the top-N repos by stars for contributor classification. The agent
# fetches up to 100 repos; contributor lookups are the expensive call, so we
# cap the deep inspection to keep unauthenticated runs under the rate limit.
MAX_CONTRIB_LOOKUPS = 15


def extract_username(value):
    """Pull a GitHub username out of a URL, @handle, or bare name."""
    value = (value or "").strip().replace(" ", "")
    for pattern in (r"https?://github\.com/([^/?#]+)", r"github\.com/([^/?#]+)",
                    r"@([^/]+)", r"^([A-Za-z0-9-]+)$"):
        m = re.search(pattern, value)
        if m:
            return m.group(1).split("?", 1)[0]
    return None


def _get(url, token, params=None):
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(url, headers={"User-Agent": "resume-screener-audit"})
    token = token or os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"token {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            # 204 No Content (e.g. contributors of an empty repo) has no body.
            return resp.status, (json.loads(body) if body.strip() else [])
    except urllib.error.HTTPError as e:
        if e.code == 403 and "rate limit" in e.read().decode("utf-8", "ignore").lower():
            return 403, {"error": "rate_limited"}
        return e.code, {}
    except (urllib.error.URLError, TimeoutError) as e:
        return 0, {"error": str(e)}
    except json.JSONDecodeError:
        return 0, {"error": "invalid_json"}


def find_external_merged_prs(username, token=None, max_prs=30):
    """Find merged PRs the candidate made to OTHER people's repos.

    This is the single strongest open_source signal in the rubric, and it is
    exactly what hiring-agent's owned-repo scan MISSES. A candidate can have
    zero multi-contributor owned repos yet many merged PRs to popular projects.
    Surfacing these tells the candidate what to put on the resume so the agent
    credits it. Uses the GitHub search API.
    """
    status, data = _get(f"{API}/search/issues", token,
                        {"q": f"type:pr+author:{username}+is:merged", "per_page": max_prs})
    if status != 200 or not isinstance(data, dict):
        return {"error": f"pr search returned {status}", "external_merged_prs": []}
    external = []
    for item in data.get("items", []):
        url = item.get("html_url", "")
        # A PR is "external" if the owning repo is not the candidate's own.
        if f"/{username}/".lower() in url.lower():
            continue
        repo_full = "/".join(url.split("/")[3:5]) if url.count("/") >= 4 else url
        external.append({"repo": repo_full, "title": item.get("title"), "url": url})
    return {
        "external_merged_pr_count": len(external),
        "external_merged_prs": external[:max_prs],
    }


def enrich(username_or_url, token=None):
    username = extract_username(username_or_url)
    if not username:
        return {"error": f"could not parse a GitHub username from {username_or_url!r}"}

    status, profile = _get(f"{API}/users/{username}", token)
    if status == 404:
        return {"error": f"GitHub user not found: {username}"}
    if status != 200:
        return {"error": f"GitHub API returned {status} for user {username}"}

    status, repos = _get(f"{API}/users/{username}/repos", token,
                         {"per_page": 100, "sort": "updated", "type": "owner"})
    if status != 200 or not isinstance(repos, list):
        return {"error": f"could not list repos for {username} (status {status})"}

    # Apply the same fork filter the agent uses.
    repos = [r for r in repos if not (r.get("fork") and r.get("forks_count", 0) < 5)]
    repos.sort(key=lambda r: r.get("stargazers_count", 0), reverse=True)

    inspected, open_source, self_project, eligible = [], 0, 0, 0
    rate_limited = False
    for repo in repos[:MAX_CONTRIB_LOOKUPS]:
        name = repo.get("name")
        status, contributors = _get(f"{API}/repos/{username}/{name}/contributors",
                                    token, {"per_page": 100})
        if status == 403:
            rate_limited = True
            break
        n = len(contributors) if isinstance(contributors, list) else 1
        mine = 0
        if isinstance(contributors, list):
            mine = next((c.get("contributions", 0) for c in contributors
                         if isinstance(c, dict)
                         and c.get("login", "").lower() == username.lower()), 0)
        ptype = "open_source" if n > 1 else "self_project"
        open_source += ptype == "open_source"
        self_project += ptype == "self_project"
        is_eligible = mine >= 4
        eligible += is_eligible
        inspected.append({
            "name": name, "stars": repo.get("stargazers_count", 0),
            "contributors": n, "your_commits": mine, "project_type": ptype,
            "eligible_top_project": is_eligible,
            "has_live_demo": bool(repo.get("homepage")),
            "language": repo.get("language"),
        })
        time.sleep(0.05)

    all_self = open_source == 0 and self_project > 0
    prs = find_external_merged_prs(username, token)
    ext_pr_count = prs.get("external_merged_pr_count", 0)
    return {
        "username": username,
        "public_repos": profile.get("public_repos"),
        "followers": profile.get("followers"),
        "blog": profile.get("blog") or None,
        "inspected_count": len(inspected),
        "open_source_repos": open_source,
        "self_project_repos": self_project,
        "eligible_top_projects": eligible,
        "all_repos_are_self_project": all_self,
        # The agent would cap open_source at ~10 based on owned repos alone.
        # But merged PRs to external repos are the strongest open_source signal
        # and are NOT visible in the owned-repo scan. If they exist, the fix is
        # to LIST them on the resume, not to accept the cap.
        "open_source_cap_triggered": all_self,
        "external_merged_pr_count": ext_pr_count,
        "external_merged_prs": prs.get("external_merged_prs", []),
        "hidden_open_source_signal": all_self and ext_pr_count > 0,
        "rate_limited": rate_limited,
        "repos": inspected,
    }


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    token = None
    for a in sys.argv[1:]:
        if a.startswith("--token="):
            token = a.split("=", 1)[1]
    if not args:
        print(__doc__)
        sys.exit(1)
    result = enrich(args[0], token)
    print(json.dumps(result, indent=2))
    if result.get("hidden_open_source_signal"):
        n = result["external_merged_pr_count"]
        print(f"\nOPPORTUNITY: owned repos are all self_project (agent would cap "
              f"open_source at ~10), BUT you have {n} merged PR(s) to OTHER "
              "people's repos. That is the strongest open_source signal in the "
              "rubric and the agent misses it. LIST these PRs on the resume so "
              "it gets credited. See external_merged_prs above.", file=sys.stderr)
    elif result.get("open_source_cap_triggered"):
        print("\nNOTE: every inspected repo is single-contributor (self_project) "
              "and no external merged PRs were found. The rubric caps open_source "
              "at ~10/35. Highest-leverage fix: land one merged PR to a popular "
              "(1000+ star) repo. See references/RUBRIC.md.", file=sys.stderr)


if __name__ == "__main__":
    main()
