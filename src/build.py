#!/usr/bin/env python3
"""Generate embed feed assets from blog post markdown files."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

FRONT_MATTER_KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
MARKDOWN_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
MARKDOWN_TAG_RE = re.compile(r"<[^>]+>")
POSTS_PLACEHOLDER = "null/*##__POSTS__##*/"


def parse_front_matter(raw: str) -> tuple[dict[str, str], str]:
    if not raw.startswith("---\n"):
        return {}, raw

    lines = raw.splitlines()
    meta: dict[str, str] = {}
    body_start = 0

    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body_start = idx + 1
            break
        match = FRONT_MATTER_KEY_RE.match(line)
        if match:
            key, value = match.groups()
            meta[key.strip().lower()] = value.strip().strip('"').strip("'")
    else:
        return {}, raw

    return meta, "\n".join(lines[body_start:])


def strip_markdown(text: str) -> str:
    text = MARKDOWN_LINK_RE.sub(r"\1", text)
    text = MARKDOWN_INLINE_CODE_RE.sub(r"\1", text)
    text = MARKDOWN_TAG_RE.sub("", text)
    text = re.sub(r"^[#>*\-\s]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return html.unescape(text).strip()


def pick_excerpt(body: str, max_len: int = 160) -> str:
    for line in body.splitlines():
        candidate = strip_markdown(line)
        if not candidate:
            continue
        if len(candidate) > max_len:
            return candidate[: max_len - 1].rstrip() + "..."
        return candidate
    return ""


def title_from_slug(slug: str) -> str:
    return slug.replace("-", " ").strip().title()


def build_post_path(date_str: str, slug: str) -> str:
    return f"/posts/{date_str}-{slug}"


def collect_posts(posts_dir: Path, blog_base_url: str) -> list[dict[str, str]]:
    post_paths = sorted(posts_dir.glob("*.md"), reverse=True)
    items: list[dict[str, str]] = []

    for post_path in post_paths:
        name = post_path.name
        if len(name) < 15 or not re.match(r"^\d{4}-\d{2}-\d{2}-", name):
            continue

        date_str = name[:10]
        slug = name[11:-3]
        raw = post_path.read_text(encoding="utf-8")
        meta, body = parse_front_matter(raw)

        path = build_post_path(date_str, slug)
        items.append(
            {
                "title": html.unescape(meta.get("title") or title_from_slug(slug)),
                "date": f"{date_str}T00:00:00Z",
                "path": path,
                "url": f"{blog_base_url.rstrip('/')}{path}",
                "excerpt": pick_excerpt(body),
            }
        )

    return items


def copy_runtime_files(runtime_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "feed.css", "feed.js"):
        source = runtime_dir / name
        if not source.exists():
            raise SystemExit(f"Missing runtime file: {source}")
        shutil.copy2(source, output_dir / name)


def embed_payload_into_feed_js(output_dir: Path, payload: dict[str, object]) -> None:
    feed_js_path = output_dir / "feed.js"
    if not feed_js_path.exists():
        raise SystemExit(f"Missing output JS file: {feed_js_path}")

    runtime_js = feed_js_path.read_text(encoding="utf-8")
    if POSTS_PLACEHOLDER not in runtime_js:
        raise SystemExit("Missing POSTS placeholder in feed.js runtime template")

    payload_js = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    patched_js = runtime_js.replace(POSTS_PLACEHOLDER, payload_js, 1)
    feed_js_path.write_text(patched_js, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build embed feed assets")
    parser.add_argument("--posts-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--runtime-dir", default="")
    parser.add_argument("--default-limit", type=int, default=5)
    parser.add_argument("--blog-base-url", default="https://blog.jonghyeon.me")
    args = parser.parse_args()

    posts_dir = Path(args.posts_dir)
    output_dir = Path(args.output_dir)
    runtime_dir = (
        Path(args.runtime_dir)
        if args.runtime_dir
        else Path(__file__).resolve().parent.parent / "runtime"
    )

    if not posts_dir.exists():
        raise SystemExit(f"Posts directory does not exist: {posts_dir}")

    copy_runtime_files(runtime_dir, output_dir)

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "defaultLimit": max(1, int(args.default_limit)),
        "count": 0,
        "items": [],
    }

    payload["items"] = collect_posts(posts_dir, args.blog_base_url)
    payload["count"] = len(payload["items"])

    embed_payload_into_feed_js(output_dir, payload)

    posts_json_path = output_dir / "posts.json"
    if posts_json_path.exists():
        posts_json_path.unlink()


if __name__ == "__main__":
    main()
