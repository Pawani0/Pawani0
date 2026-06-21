#!/usr/bin/env python3
"""Fetch a user's contribution calendar from the GitHub GraphQL API.

Writes a JSON file shaped like {"weeks": [...]} that generate_trex.py reads.

Environment:
    GH_TOKEN  - a token with read access (the Actions GITHUB_TOKEN works for
                public contributions; use a PAT if your graph is private).
    GH_LOGIN  - the GitHub username to fetch.
"""
import json
import os
import sys
import urllib.request

QUERY = """
query($login:String!){
  user(login:$login){
    contributionsCollection{
      contributionCalendar{
        weeks{
          contributionDays{ contributionCount weekday date }
        }
      }
    }
  }
}
"""


def main():
    token = os.environ.get("GH_TOKEN")
    login = os.environ.get("GH_LOGIN")
    out = sys.argv[1] if len(sys.argv) > 1 else "contributions.json"
    if not token or not login:
        sys.exit("GH_TOKEN and GH_LOGIN must be set")

    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "trex-contribution-game",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)

    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")

    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    with open(out, "w") as f:
        json.dump(cal, f)
    weeks = len(cal["weeks"])
    total = sum(d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"])
    print(f"Fetched {weeks} weeks, {total} total contributions -> {out}")


if __name__ == "__main__":
    main()
