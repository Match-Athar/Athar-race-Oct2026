#!/usr/bin/env python3
"""Publish the PUBLIC board (site/index.html) to GitHub Pages — no git needed.

One-time:  save a GitHub token (classic, scope: public_repo) in a text file, e.g. github-token.txt
Every day:
    python publish_github.py --token-file github-token.txt --page site/index.html

First run creates the public repository (default name: athar-race), uploads index.html and turns on
GitHub Pages. The board is then at  https://<your-user>.github.io/athar-race/
Only index.html is ever uploaded (percentages and names, no amounts). Never upload internal.html.
"""
import os
import sys
import json
import time
import base64
import argparse
import urllib.request
import urllib.error

API = "https://api.github.com"


def call(method, path, token, body=None, ok=(200, 201, 204)):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "athar-publisher")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            txt = r.read().decode()
            return r.status, (json.loads(txt) if txt else {})
    except urllib.error.HTTPError as e:
        txt = e.read().decode()
        if e.code in ok:
            return e.code, {}
        return e.code, (json.loads(txt) if txt.startswith("{") else {"message": txt})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token-file", required=True)
    ap.add_argument("--page", default="site/index.html")
    ap.add_argument("--repo", default="athar-race")
    a = ap.parse_args()

    token = open(a.token_file, encoding="utf-8").read().strip()
    html = open(a.page, "rb").read()
    if b'"sales"' in html or b'"target"' in html:
        sys.exit("Refusing: this page looks like it contains amounts. Only the public board may be published.")

    st, me = call("GET", "/user", token)
    if st != 200:
        sys.exit(f"Token not accepted by GitHub ({st}): {me.get('message')}")
    user = me["login"]

    st, repo = call("GET", f"/repos/{user}/{a.repo}", token)
    if st == 404:
        st, repo = call("POST", "/user/repos", token, {
            "name": a.repo, "private": False, "auto_init": True,
            "description": "سباق أثر — Athar sales race board (no amounts)"})
        if st not in (200, 201):
            sys.exit(f"Could not create repository ({st}): {repo.get('message')}")
        print("Created repository", repo["html_url"])
        time.sleep(3)
    branch = repo.get("default_branch", "main")

    st, cur = call("GET", f"/repos/{user}/{a.repo}/contents/index.html?ref={branch}", token)
    body = {"message": "Update board " + time.strftime("%Y-%m-%d %H:%M"),
            "content": base64.b64encode(html).decode(), "branch": branch}
    if st == 200:
        body["sha"] = cur["sha"]
    st, res = call("PUT", f"/repos/{user}/{a.repo}/contents/index.html", token, body)
    if st not in (200, 201):
        sys.exit(f"Upload failed ({st}): {res.get('message')}")
    print("Uploaded index.html")

    st, pages = call("GET", f"/repos/{user}/{a.repo}/pages", token)
    if st == 404:
        st, pages = call("POST", f"/repos/{user}/{a.repo}/pages", token,
                         {"source": {"branch": branch, "path": "/"}})
        if st not in (200, 201):
            sys.exit(f"Could not turn on GitHub Pages ({st}): {pages.get('message')}")
        print("GitHub Pages turned on (first build takes 1–2 minutes)")
    url = pages.get("html_url") or f"https://{user}.github.io/{a.repo}/"
    print("Board link:", url)


if __name__ == "__main__":
    main()
