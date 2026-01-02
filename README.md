# bsky_paperbot

sourcecode for paper poster bot. Bot on bluesky that pings arxiv rss feeds and posts them on bluesky. Querier + archiver may be of independent interest.

## make your own bsky bot 

+ fork this repository
+ create a bluesky account 
+ get a bluesky password / username, and set them in `Settings > Secrets and Variables > BSKYBOT, BSKYPWD`
+ use different RSS feeds, or do something else

### Abstract Image Rendering

The bot uses [Typst](https://typst.app/) for professional typesetting of abstract images when available, with automatic fallback to PIL for local development.

- **GitHub Actions**: Typst is automatically installed via `typst-community/setup-typst` action
- **Local development**: Works without Typst (PIL fallback), but installing Typst gives better quality
  - macOS: `brew install typst`
  - Linux: Download from https://github.com/typst/typst/releases

[![GH Arxiv Posterbot](https://github.com/apoorvalal/bsky_paperbot/actions/workflows/post.yml/badge.svg?branch=master)](https://github.com/apoorvalal/bsky_paperbot/actions/workflows/post.yml)
