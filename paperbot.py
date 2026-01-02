import json
import random
import time
from typing import Dict
import feedparser
from atproto import Client, client_utils
import shutil
import subprocess
import hashlib
import tempfile
import os


class ArxivBot:
    def __init__(self, handle: str, password: str):
        self.client = Client()
        self.client.login(handle, password)

    def _render_with_typst(self, title: str, abstract: str, authors: str) -> bytes:
        """Render abstract image using Typst. Returns PNG bytes or raises exception."""
        # Read template
        template_path = os.path.join(os.path.dirname(__file__), 'abstract_template.typ')
        with open(template_path, 'r') as f:
            template = f.read()

        # Escape special Typst characters in user data
        def escape_typst(text: str) -> str:
            # Escape backslashes first, then special chars
            text = text.replace('\\', '\\\\')
            text = text.replace('#', '\\#')
            text = text.replace('[', '\\[')
            text = text.replace(']', '\\]')
            text = text.replace('{', '\\{')
            text = text.replace('}', '\\}')
            return text

        # Populate template
        content = template.replace('{{TITLE}}', escape_typst(title))
        content = content.replace('{{AUTHORS}}', escape_typst(authors))
        content = content.replace('{{ABSTRACT}}', escape_typst(abstract))

        # Create temp files with unique names
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        temp_dir = tempfile.gettempdir()
        typ_path = os.path.join(temp_dir, f'abstract_{content_hash}.typ')
        png_path = os.path.join(temp_dir, f'abstract_{content_hash}.png')

        try:
            # Write populated template
            with open(typ_path, 'w') as f:
                f.write(content)

            # Compile with Typst
            result = subprocess.run(
                ['typst', 'compile', typ_path, png_path, '--format', 'png'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                raise Exception(f"Typst compilation failed: {result.stderr}")

            # Read PNG bytes
            with open(png_path, 'rb') as f:
                return f.read()

        finally:
            # Cleanup temp files
            for path in [typ_path, png_path]:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass  # Ignore cleanup errors

    def create_abstract_image(self, title: str, abstract: str, authors: str) -> bytes:
        """Generate a formatted PNG image of the paper abstract using Typst"""
        return self._render_with_typst(title, abstract, authors)

    def create_post(self, title: str, link: str, description: str, authors: str):
        """Create a Bluesky post with paper details and abstract image"""
        # Shortened post text (abstract will be in image)
        post_text = f"📈🤖 New Paper\n{title}\nBy {authors}\n"

        # Generate abstract image
        image_data = self.create_abstract_image(title, description, authors)

        # Upload image with abstract as alt text
        upload = self.client.upload_blob(image_data)

        # Create embed with image
        embed = {
            "$type": "app.bsky.embed.images",
            "images": [{
                "alt": description,  # Full abstract as alt text for accessibility
                "image": upload.blob
            }]
        }

        # Create and send post with image
        post_builder = client_utils.TextBuilder().link("arXiv", link).text(post_text)
        self.client.send_post(post_builder, embed=embed)

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
