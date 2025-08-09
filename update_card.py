#!/usr/bin/env python3
"""
Minimal dynamic GitHub profile "terminal card".
- Queries GitHub GraphQL (v4) for: stars, repos, followers, total contributions last 12 months.
- Writes values into two SVG templates by replacing text nodes by id.
- Designed to run in GitHub Actions. Requires envs: GH_TOKEN, USER_NAME.
"""
import os, sys, datetime
import requests
from lxml import etree

GH_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("ACCESS_TOKEN")
USER_NAME = os.environ.get("USER_NAME")

if not GH_TOKEN or not USER_NAME:
    raise SystemExit("Missing envs GH_TOKEN and/or USER_NAME")

HEADERS = {"authorization": f"bearer {GH_TOKEN}"}

def gql(query, variables=None):
    r = requests.post("https://api.github.com/graphql", json={"query": query, "variables": variables or {}}, headers=HEADERS)
    if r.status_code != 200:
        raise RuntimeError(f"GraphQL error: {r.status_code} {r.text}")
    j = r.json()
    if "errors" in j:
        raise RuntimeError(f"GraphQL errors: {j['errors']}")
    return j["data"]

def get_user_core(login):
    q = """
    query($login: String!){
      user(login:$login){
        createdAt
        followers { totalCount }
        repositories(ownerAffiliations: OWNER, privacy: PUBLIC) { totalCount }
        starredRepositories { totalCount }
        contributionsCollection {
          contributionCalendar { totalContributions }
        }
      }
    }
    """
    d = gql(q, {"login": login})["user"]
    return {
        "createdAt": d["createdAt"],
        "followers": d["followers"]["totalCount"],
        "repos": d["repositories"]["totalCount"],
        "stars": d["starredRepositories"]["totalCount"],
        "commits": d["contributionsCollection"]["contributionCalendar"]["totalContributions"],
    }

def human_time_since(iso_str):
    start = datetime.datetime.fromisoformat(iso_str.replace("Z","+00:00"))
    now = datetime.datetime.now(datetime.timezone.utc)
    delta = now - start
    days = delta.days
    years, days = divmod(days, 365)
    months, days = divmod(days, 30)
    parts = []
    if years: parts.append(f"{years} year{'s' if years!=1 else ''}")
    if months: parts.append(f"{months} month{'s' if months!=1 else ''}")
    parts.append(f"{days} day{'s' if days!=1 else ''}")
    return ", ".join(parts)

def set_text(root, element_id, value):
    el = root.find(f".//*[@id='{element_id}']")
    if el is not None:
        el.text = str(value)

def update_svg(path, stats):
    tree = etree.parse(str(path))
    root = tree.getroot()
    set_text(root, "uptime", human_time_since(stats["createdAt"]))
    set_text(root, "repos", f"{stats['repos']:,}")
    set_text(root, "stars", f"{stats['stars']:,}")
    set_text(root, "followers", f"{stats['followers']:,}")
    set_text(root, "commits", f"{stats['commits']:,}")
    # Write
    tree.write(str(path), encoding="utf-8", xml_declaration=True)

def main():
    stats = get_user_core(USER_NAME)
    for p in ["assets/card_dark.svg", "assets/card_light.svg"]:
        update_svg(p, stats)
    print("Updated SVGs with stats:", stats)

if __name__ == "__main__":
    main()
