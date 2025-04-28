#!/usr/bin/env python3
import feedparser
from atproto import Client, client_utils
import os
import re
import grapheme

class ArxivBot:
    def __init__(self, handle: str, password: str):
        self.client = Client()
        self.client.login(handle, password)

    @staticmethod
    def truncate_at_word_boundary(text: str, max_graphemes: int) -> str:
        """
        Truncate at nearest space within `max_graphemes` graphemes.
        """
        if grapheme.length(text) <= max_graphemes:
            return text
        seg = grapheme.slice(text, 0, max_graphemes)
        idx = seg.rfind(' ')
        return seg if idx == -1 else seg[:idx]

    def create_post(self, title: str, link: str, description: str, authors: str):
        """Build and send a Bluesky post: title. authors. description. then a 'link' facet."""
        prefix = "📈🤖"
        sep = "\n\n"
        link_label = "link"
        max_total = 300  # grapheme limit

        # Format header: title with period
        header = f"{prefix} {title}."
        if authors:
            header += f" {authors}."

        # Reserve space for separator and link facet
        reserved = grapheme.length(sep) + grapheme.length(link_label)
        content_limit = max_total - reserved

        # Build body with optional description
        if grapheme.length(header) >= content_limit:
            body = self.truncate_at_word_boundary(header, content_limit)
        else:
            remaining = content_limit - grapheme.length(header) - 1
            if remaining > 0 and description:
                desc = self.truncate_at_word_boundary(description, remaining)
                body = f"{header} {desc}" if desc else header
            else:
                body = header

        # Safety check
        if grapheme.length(body) > content_limit:
            body = self.truncate_at_word_boundary(body, content_limit)

        # Construct and send post
        builder = (
            client_utils.TextBuilder()
            .text(body)
            .text(sep)
            .link(link_label, link)
        )
        try:
            self.client.send_post(builder)
            print(f"Posted to Bluesky: {title}")
        except Exception as e:
            print(f"Failed to post '{title}': {e}")

    def get_arxiv_feed(self, subject: str = "econ.EM+stat.ME") -> dict:
        """Parse RSS, extract title, link, description, authors."""
        url = f"https://rss.arxiv.org/rss/{subject}"
        feed = feedparser.parse(url)
        results = {}
        for entry in feed.entries:
            title = entry.get('title', '').strip()
            link = entry.get('link', '').strip()

            raw = entry.get('description', '')
            m = re.search(r'Abstract:\s*(.*)', raw, re.DOTALL)
            desc = m.group(1).strip() if m else (raw.split('\n',1)[1].strip() if '\n' in raw else raw.strip())

            # Extract authors via dc_creator or entry.author
            creators = entry.get('dc_creator') or entry.get('author', '')
            names = [n.strip() for n in creators.split(',') if n.strip()]
            if names:
                last_names = [n.split()[-1] for n in names]
                if len(last_names) == 1:
                    auth = last_names[0]
                elif len(last_names) == 2:
                    auth = f"{last_names[0]} and {last_names[1]}"
                else:
                    if len(last_names) > 3:
                        auth = f"{last_names[0]}, {last_names[1]}, and {last_names[2]} et al."
                    else:
                        auth = f"{', '.join(last_names[:-1])}, and {last_names[-1]}"
            else:
                auth = ''

            results[link] = {"title": title, "link": link, "description": desc, "authors": auth}
        return results

    def run(self):
        feed = self.get_arxiv_feed()
        for link, paper in feed.items():
            print(f"DEBUG AUTHORS for {paper['title']}: '{paper['authors']}'")
            self.create_post(paper['title'], paper['link'], paper['description'], paper['authors'])
        print(f"Run complete. Posted {len(feed)} papers.")

if __name__ == '__main__':
    handle = os.getenv('BSKYBOT')
    pwd = os.getenv('BSKYPWD')
    if not handle or not pwd:
        raise ValueError('BSKYBOT and BSKYPWD env vars must be set.')
    ArxivBot(handle, pwd).run()
