import json
import random
import time
from typing import Dict
import feedparser
from atproto import Client, client_utils


class ArxivBot:
    def __init__(self, handle: str, password: str):
        self.client = Client()
        self.client.login(handle, password)

    def create_post(self, title: str, link: str, description: str, authors: str):
        """Create a Bluesky post with paper details"""
        # Reserve characters for link and emoji
        post_text = f" 📈🤖\n{title} ({authors}) {description}"[:293]
        post_builder = client_utils.TextBuilder().link("link", link).text(post_text)
        self.client.send_post(post_builder)

    def get_arxiv_feed(self, subject: str = "econ.em+stat.me") -> Dict:
        """Fetch and parse arxiv RSS feed"""
        feed = feedparser.parse(f"https://rss.arxiv.org/rss/{subject}")
        return {
            entry.link.strip(): {
                "title": entry.title.strip(),
                "link": entry.link.strip(),
                "description": (
                    entry.description.split("Abstract:", 1)[1].strip()
                    if "Abstract:" in entry.description
                    else entry.description.strip()
                ),
                "authors": ", ".join(
                    [name.split()[-1] for name in entry.author.split(", ")][:3]
                )
                + (" et al" if len(entry.author.split(", ")) > 3 else ""),
            }
            for entry in feed.entries
        }

    def update_archive(self, feed: Dict, archive_file: str = "combined.json") -> tuple:
        """Update archive with new entries"""
        try:
            with open(archive_file, "r") as f:
                archive = json.load(f)
        except FileNotFoundError:
            archive = {}

        new_archive = archive.copy()
        for k, v in feed.items():
            if k not in archive:
                new_archive[k] = v

        if len(new_archive) > len(archive):
            with open(archive_file, "w") as f:
                json.dump(new_archive, f)

        return feed, archive

    def run(self):
        """Main bot loop"""
        feed, archive = self.update_archive(self.get_arxiv_feed())
        new_posts = 0

        # Post new papers
        for k, v in feed.items():
            if k not in archive:
                self.create_post(v["title"], v["link"], v["description"], v["authors"])
                time.sleep(random.randint(60, 300))
                new_posts += 1

        # Post random paper if no new ones found
        if new_posts == 0 and len(archive) > 2:
            paper = random.choice(list(archive.values()))
            # if paper contains key authors - back-compat
            if "authors" in paper:
                auth = paper["authors"]
            else:
                auth = ""
            self.create_post(paper["title"], paper["link"], paper["description"], auth)
            time.sleep(random.randint(30, 60))


def main():
    import os

    bot = ArxivBot(os.environ["BSKYBOT"], os.environ["BSKYPWD"])
    bot.run()


if __name__ == "__main__":
    main()
