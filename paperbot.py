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


# %%
def get_arxiv_feed(subject: str):
    """get skeetable list of paper title, link, and (fragment of) abstract

    Args:
        subject (str): valid arxiv subject, e.g. "stat.ME" or "econ.EM" or "cs.LG"

    Returns:
        list of skeets
    """
    feed_url = f"https://export.arxiv.org/rss/{subject}"
    feed = feedparser.parse(feed_url)
    items = [
        f"{entry.title.split('.')[0].strip()}\n{entry.link.strip()}\n{entry.description.replace('<p>', '').replace('</p>', '').strip()}"
        for entry in feed.entries
    ]
    return [item[:296].replace("\n", " ") + "\n📈🤖" for item in items]


# %%
def main():
    # stats
    stat_entries = get_arxiv_feed("stat.ME")
    for entry in stat_entries:
        create_post(text=entry)
        time.sleep(random.randint(10, 120))
    # metrics
    em_entries = get_arxiv_feed("econ.EM")
    for entry in em_entries:
        create_post(text=entry)
        time.sleep(random.randint(10, 120))
    # ml - #toomuchcontent
    # ml_entries = get_arxiv_feed("stat.ML")
    # for entry in ml_entries:
    #     create_post(text=entry)
    #     time.sleep(random.randint(0, 2))

# %%
if __name__ == "__main__":

    main()
