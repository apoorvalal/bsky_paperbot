#!/home/alal/anaconda3/bin/python3

"""
Script to post new articles from arxiv stat.ME and econ.EM. Bring your own handle and app-password.
"""

# %%
import time
import re
import os
import sys
import json
from typing import List, Dict
from datetime import datetime, timezone
import random

import requests
import feedparser


# %%
def bsky_login_session(pds_url: str, handle: str, password: str) -> Dict:
    """login to blueksy

    Args:
        pds_url (str): bsky platform (default for now)
        handle (str): username
        password (str): app password

    Returns:
        Dict: json blob with login
    """
    resp = requests.post(
        pds_url + "/xrpc/com.atproto.server.createSession",
        json={"identifier": handle, "password": password},
    )
    resp.raise_for_status()
    return resp.json()


def parse_urls(text: str) -> List[Dict]:
    """parse URLs in string blob

    Args:
        text (str): string

    Returns:
        List[Dict]: span of url
    """
    spans = []
    # partial/naive URL regex based on: https://stackoverflow.com/a/3809435
    # tweaked to disallow some training punctuation
    url_regex = rb"[$|\W](https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*[-a-zA-Z0-9@%_\+~#//=])?)"
    text_bytes = text.encode("UTF-8")
    for m in re.finditer(url_regex, text_bytes):
        spans.append(
            {
                "start": m.start(1),
                "end": m.end(1),
                "url": m.group(1).decode("UTF-8"),
            }
        )
    return spans


def parse_facets(text: str) -> List[Dict]:
    """
    parses post text and returns a list of app.bsky.richtext.facet objects for any URLs (https://example.com)
    """
    facets = []
    for u in parse_urls(text):
        facets.append(
            {
                "index": {
                    "byteStart": u["start"],
                    "byteEnd": u["end"],
                },
                "features": [
                    {
                        "$type": "app.bsky.richtext.facet#link",
                        # NOTE: URI ("I") not URL ("L")
                        "uri": u["url"],
                    }
                ],
            }
        )
    return facets


def create_post(
    text: str,
    pds_url: str = "https://bsky.social",
    handle: str = os.environ["BSKYBOT"],
    password: str = os.environ["BSKYPWD"],
):
    """post on bluesky

    Args:
        text (str): text
        pds_url (str, optional): bsky Defaults to "https://bsky.social".
        handle (_type_, optional):  Defaults to os.environ["BSKYBOT"]. Set this environmental variable in your dotfile (bashrc/zshrc).
        password (_type_, optional): _description_. Defaults to os.environ["BSKYPWD"].
    """
    session = bsky_login_session(pds_url, handle, password)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    # these are the required fields which every post must include
    post = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": now,
    }

    # parse out mentions and URLs as "facets"
    if len(text) > 0:
        facets = parse_facets(post["text"])
        if facets:
            post["facets"] = facets

    resp = requests.post(
        pds_url + "/xrpc/com.atproto.repo.createRecord",
        headers={"Authorization": "Bearer " + session["accessJwt"]},
        json={
            "repo": session["did"],
            "collection": "app.bsky.feed.post",
            "record": post,
        },
    )
    print("createRecord response:", file=sys.stderr)
    print(json.dumps(resp.json(), indent=2))
    resp.raise_for_status()


def get_arxiv_feed(subject: str):
    """get skeetable list of paper title, link, and (fragment of) abstract

    Args:
        subject (str): valid arxiv subject, e.g. "stat.ME" or "econ.EM" or "cs.LG"

    Returns:
        list of skeets
    """
    feed_url = f"https://export.arxiv.org/rss/{subject}"
    feed = feedparser.parse(feed_url)
    # dict of all entries
    res = {
        entry.link.strip(): {
            "title": entry.title.split(".")[0].strip(),
            "link": entry.link.strip(),
            "description": entry.description.replace("<p>", "")
            .replace("</p>", "")
            .strip(),
        }
        for entry in feed.entries
    }
    return res


# %%
def main():
    ######################################################################
    # stats
    ######################################################################
    # read existing data from "stat_me_draws.json" file
    try:
        with open("stat_me_draws.json", "r") as f:
            stat_me_archive = json.load(f)
    except FileNotFoundError:
        stat_me_archive = {}
    # Get new data from arxiv feed
    new_pull = get_arxiv_feed("stat.ME")
    new_posts = 0
    # Append new data to existing data
    for k, v in new_pull.items():
        if k not in stat_me_archive:  # if not already posted
            create_post(f"{v['title']}\n{v['link']}\n{v['description']}"[:297] + "\n📈🤖")
            time.sleep(random.randint(300, 1200))
            stat_me_archive[k] = v
            new_posts += 1
    if new_posts == 0:
        random_paper = random.choice(list(stat_me_archive.values()))
        create_post(f"{random_paper['title']}\n{random_paper['link']}\n{random_paper['description']}"[:297] + "\n📈🤖")
        time.sleep(random.randint(300, 1200))
    # Write updated data back to "stat_me_draws.json" file - once every run
    with open("stat_me_draws.json", "a+") as f:
        json.dump(stat_me_archive, f)
    print("wrote stat_me_draws.json")
    ######################################################################
    # econometrics
    ######################################################################
    try:
        with open("econ_em_draws.json", "r") as f:
            econ_em_archive = json.load(f)
    except FileNotFoundError:
        econ_em_archive = {}
    # Get new data from arxiv feed
    new_pull = get_arxiv_feed("econ.EM")
    new_posts = 0
    # Append new data to existing data
    for k, v in new_pull.items():
        if k not in econ_em_archive:
            create_post(f"{v['title']}\n{v['link']}\n{v['description']}"[:297] + "\n📈🤖")
            time.sleep(random.randint(300, 1200))
            econ_em_archive[k] = v
            new_posts += 1
    if new_posts == 0:
        random_paper = random.choice(list(econ_em_archive.values()))
        create_post(f"{random_paper['title']}\n{random_paper['link']}\n{random_paper['description']}"[:297] + "\n📈🤖")
    # Write updated data back to "econ_em_draws.json" file
    with open("econ_em_draws.json", "a+") as f:
        json.dump(econ_em_archive, f)
    print("wrote econ_em_draws.json")
# %%
if __name__ == "__main__":
    main()

# %%
