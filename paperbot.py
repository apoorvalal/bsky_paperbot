import json
import random
import time
from typing import Dict
from io import BytesIO
import textwrap
import feedparser
from atproto import Client, client_utils
from PIL import Image, ImageDraw, ImageFont


class ArxivBot:
    def __init__(self, handle: str, password: str):
        self.client = Client()
        self.client.login(handle, password)

    def create_abstract_image(self, title: str, abstract: str, authors: str) -> bytes:
        """Generate a formatted PNG image of the paper abstract"""
        # Image settings - 4 inches at 150 DPI
        dpi = 150
        width = int(4 * dpi)  # 600 pixels
        max_height = int(11 * dpi)  # Start with max letter height
        bg_color = (255, 255, 255)  # White background
        text_color = (0, 0, 0)  # Black text
        margin_left = 40
        margin_right = 40
        margin_top = 40
        margin_bottom = 40

        # Create temporary large image
        temp_img = Image.new('RGB', (width, max_height), bg_color)
        draw = ImageDraw.Draw(temp_img)

        # Try to load fonts, fall back to default if not available
        title_font = None
        author_font = None
        header_font = None
        body_font = None

        try:
            # Try common font paths for different operating systems
            font_paths = [
                "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",  # macOS
                "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",  # Linux
                "C:\\Windows\\Fonts\\timesbd.ttf",  # Windows
            ]
            for path in font_paths:
                try:
                    title_font = ImageFont.truetype(path, 18)
                    author_font = ImageFont.truetype(path.replace("Bold", "Italic"), 12)
                    header_font = ImageFont.truetype(path, 14)
                    body_font = ImageFont.truetype(path.replace("Bold.ttf", ".ttf"), 11)
                    break
                except:
                    continue
        except:
            pass

        # Fallback to default font if none found
        if title_font is None:
            title_font = ImageFont.load_default()
            author_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            body_font = ImageFont.load_default()

        y_position = margin_top
        text_width = width - margin_left - margin_right

        # Helper function to draw justified text
        def draw_justified_text(text_line, y_pos, font, is_last_line=False):
            if is_last_line or len(text_line.strip()) == 0:
                # Don't justify the last line or empty lines
                draw.text((margin_left, y_pos), text_line, font=font, fill=text_color)
            else:
                words = text_line.split()
                if len(words) == 1:
                    draw.text((margin_left, y_pos), text_line, font=font, fill=text_color)
                else:
                    # Calculate word widths
                    word_widths = [draw.textlength(word, font=font) for word in words]
                    total_word_width = sum(word_widths)
                    total_space_width = text_width - total_word_width
                    space_width = total_space_width / (len(words) - 1)

                    # Draw words with calculated spacing
                    x_pos = margin_left
                    for i, word in enumerate(words):
                        draw.text((x_pos, y_pos), word, font=font, fill=text_color)
                        x_pos += word_widths[i] + space_width

        # Draw title (single-spaced, left-aligned)
        title_wrapped = textwrap.fill(title, width=70)
        for line in title_wrapped.split('\n'):
            draw.text((margin_left, y_position), line, font=title_font, fill=text_color)
            y_position += 22

        y_position += 8

        # Draw authors (left-aligned)
        authors_wrapped = textwrap.fill(authors, width=80)
        for line in authors_wrapped.split('\n'):
            draw.text((margin_left, y_position), line, font=author_font, fill=text_color)
            y_position += 16

        y_position += 16

        # Draw "Abstract" header
        draw.text((margin_left, y_position), "Abstract", font=header_font, fill=text_color)
        y_position += 20

        # Draw abstract text (justified, single-spaced)
        abstract_wrapped = textwrap.fill(abstract, width=85)
        lines = abstract_wrapped.split('\n')
        for i, line in enumerate(lines):
            is_last = (i == len(lines) - 1)
            draw_justified_text(line, y_position, body_font, is_last_line=is_last)
            y_position += 14

        # Crop to actual content with bottom margin
        final_height = y_position + margin_bottom
        img = temp_img.crop((0, 0, width, final_height))

        # Convert to bytes
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG', dpi=(dpi, dpi))
        img_bytes.seek(0)
        return img_bytes.read()

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
