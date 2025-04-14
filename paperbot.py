import json
import random
import time
from typing import Dict
import feedparser
from atproto import Client, client_utils
import os


class ArxivBot:
    def __init__(self, handle: str, password: str):
        self.client = Client()
        self.client.login(handle, password)

    @staticmethod
    def truncate_at_word_boundary(text: str, max_length: int) -> str:
        """
        Truncates text at the nearest word boundary at or before max_length.
        If no space is found, truncates exactly at max_length.
        """
        if len(text) <= max_length:
            return text
        end = text.rfind(' ', 0, max_length)
        if end == -1:
            return text[:max_length]
        return text[:end]

    def create_post(self, title: str, link: str, abstract: str, authors: str):
        """Create and send a post to Bluesky with paper details."""
        # Constructing the post text clearly and reserving space for emojis and link
        raw_text = f"📈🤖\n{title} ({authors}) {abstract}"
        post_text = self.truncate_at_word_boundary(raw_text, 293)

        # Properly creating hyperlink with TextBuilder
        post_builder = client_utils.TextBuilder().text(post_text).text("\n\n").link(link, link)

        try:
            self.client.send_post(post_builder)
            print(f"Posted to Bluesky: {title}")
        except Exception as e:
            print(f"Failed to post '{title}': {e}")

    def get_arxiv_feed(self, subject: str = "econ.EM+stat.ME") -> Dict[str, Dict[str, str]]:
        """
        Fetches and parses the arXiv RSS feed for the given subject,
        handling authors, titles, abstracts, and links robustly.
        """
        feed_url = f"https://rss.arxiv.org/rss/{subject}"
        feed = feedparser.parse(feed_url)
        results = {}

        for entry in feed.entries:
            title = entry.title.strip() if 'title' in entry else ''
            link = entry.link.strip() if 'link' in entry else ''

            description = entry.get('description', '').split('Abstract:', 1)
            abstract = description[1].strip() if len(description) > 1 else description[0].strip()

            authors_raw = entry.get('dc_creator', '')
            authors_list = [author.strip() for author in authors_raw.split(',') if author.strip()]

            formatted_authors = ", ".join([name.split()[-1] for name in authors_list[:3]])
            if len(authors_list) > 3:
                formatted_authors += " et al"

            results[link] = {
                "title": title,
                "link": link,
                "abstract": abstract,
                "authors": formatted_authors,
            }

        return results

    def update_archive(self, feed: Dict, archive_file: str = "combined.json") -> tuple:
        """Update archive with new entries and provide feedback."""
        try:
            with open(archive_file, "r") as f:
                archive = json.load(f)
        except FileNotFoundError:
            archive = {}
            print("Archive not found, creating new one.")

        new_entries = {k: v for k, v in feed.items() if k not in archive}

        if new_entries:
            archive.update(new_entries)
            with open(archive_file, "w") as f:
                json.dump(archive, f)
            print(f"Added {len(new_entries)} new entries to archive.")
        else:
            print("No new entries to add to archive.")

        return feed, archive

    def run(self):
        """Main bot loop with clear logging."""
        feed, archive = self.update_archive(self.get_arxiv_feed())
        new_posts = 0

        # Post new papers
        for link, paper in feed.items():
            if link not in archive:
                self.create_post(paper["title"], paper["link"], paper["abstract"], paper["authors"])
                new_posts += 1
                # Random sleep to avoid rate limiting
                time.sleep(random.randint(60, 300))

        # Post random archived paper if no new ones
        if new_posts == 0 and archive:
            paper = random.choice(list(archive.values()))
            authors = paper.get("authors", "")
            self.create_post(paper["title"], paper["link"], paper["abstract"], authors)
            time.sleep(random.randint(30, 60))
            print("No new papers today; posted a random archived paper.")

def main():
    handle = os.getenv("BSKYBOT")
    password = os.getenv("BSKYPWD")

    if not handle or not password:
        raise ValueError("BSKYBOT and BSKYPWD environment variables must be set.")

    bot = ArxivBot(handle, password)
    bot.run()

if __name__ == "__main__":
    main()
