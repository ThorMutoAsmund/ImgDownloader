#!/usr/bin/env python3
# Download JPEG stock photos from Lorem Picsum (Unsplash-sourced images).

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_LIST = "https://picsum.photos/v2/list"
USER_AGENT = "download-stock-photos/1.0 (+https://picsum.photos)"
# Picsum currently exposes about 10 full list pages at limit=100 (~1000 images).
MAX_LIST_PAGE = 10
LIST_PAGE_SIZE = 100


# Create and return the CLI argument parser with all download options.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download JPEG photos from Lorem Picsum "
            "(free Unsplash-sourced stock images, no API key)."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=10,
        help="Number of photos to download",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("photos"),
        help="Output directory for downloaded JPEGs",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1280,
        help="Image width in pixels",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=720,
        help="Image height in pixels",
    )
    parser.add_argument(
        "--page",
        type=int,
        default=None,
        help="Use this Picsum API page only (1-based). Default: pick random pages",
    )
    parser.add_argument(
        "--seed",
        type=str,
        default=None,
        help="Reproducible mode: download Picsum seed images instead of random ones",
    )
    parser.add_argument(
        "--grayscale",
        action="store_true",
        help="Download grayscale versions",
    )
    parser.add_argument(
        "--blur",
        type=int,
        choices=range(1, 11),
        metavar="1-10",
        default=None,
        help="Apply Picsum blur level (1-10)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="Delay between downloads in seconds (be polite to the API)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files with the same name",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only print errors",
    )
    return parser


# Fetch a URL and parse the response body as JSON.
def http_get_json(url: str, timeout: float) -> list | dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


# Download a JPEG from url and write it to destination.
def http_download(url: str, destination: Path, timeout: float) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
        content_type = response.headers.get("Content-Type", "")
    if "jpeg" not in content_type.lower() and "jpg" not in content_type.lower():
        # Picsum may omit a precise type; accept binary payloads that look like JPEG.
        if not data.startswith(b"\xff\xd8"):
            raise ValueError(f"Expected JPEG, got Content-Type={content_type!r}")
    destination.write_bytes(data)


# Fetch one page of image metadata from the Picsum list API.
def fetch_page(page: int, timeout: float, limit: int = LIST_PAGE_SIZE) -> list[dict]:
    params = urllib.parse.urlencode({"page": page, "limit": limit})
    url = f"{API_LIST}?{params}"
    chunk = http_get_json(url, timeout)
    if not isinstance(chunk, list):
        return []
    return chunk


# Return `count` unique images randomly sampled from Picsum list pages.
# If page is set, only that page is used; otherwise pages are shuffled so
# each run tends to pick a different set of photos.
def fetch_random_image_list(count: int, timeout: float, page: int | None = None) -> list[dict]:
    pool: list[dict] = []
    seen_ids: set[str] = set()

    if page is not None:
        pages = [page]
    else:
        # Shuffle all known pages so each run draws from a different mix.
        pages = list(range(1, MAX_LIST_PAGE + 1))
        random.shuffle(pages)

    for current_page in pages:
        try:
            chunk = fetch_page(current_page, timeout)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
            continue
        if not chunk:
            continue
        for item in chunk:
            image_id = str(item.get("id", ""))
            if not image_id or image_id in seen_ids:
                continue
            seen_ids.add(image_id)
            pool.append(item)
        # Stop once we have a large enough pool to sample from.
        if page is None and len(pool) >= max(count * 5, 100):
            break

    if not pool:
        return []
    if len(pool) <= count:
        random.shuffle(pool)
        return pool
    return random.sample(pool, count)


# Build a Picsum JPEG URL for a specific id or seed, with optional effects.
def image_url(
    image_id: str | int,
    width: int,
    height: int,
    *,
    seed: str | None,
    grayscale: bool,
    blur: int | None,
) -> str:
    if seed is not None:
        # Seed mode ignores list IDs and produces a stable sequence per index.
        base = f"https://picsum.photos/seed/{urllib.parse.quote(seed)}/{width}/{height}.jpg"
    else:
        base = f"https://picsum.photos/id/{image_id}/{width}/{height}.jpg"

    query: list[str] = []
    if grayscale:
        query.append("grayscale")
    if blur is not None:
        query.append(f"blur={blur}")
    if query:
        return f"{base}?{'&'.join(query)}"
    return base


# Exit with an error message if any CLI argument values are invalid.
def validate_args(args: argparse.Namespace) -> None:
    if args.count < 1:
        raise SystemExit("--count must be at least 1")
    if args.width < 1 or args.height < 1:
        raise SystemExit("--width and --height must be positive")
    if args.page is not None and args.page < 1:
        raise SystemExit("--page must be at least 1")
    if args.timeout <= 0:
        raise SystemExit("--timeout must be positive")
    if args.delay < 0:
        raise SystemExit("--delay cannot be negative")


# Resolve the image list, download JPEGs into the output directory, and
# return a process exit code (0 on success, non-zero on failure).
def download_photos(args: argparse.Namespace) -> int:
    validate_args(args)
    args.output.mkdir(parents=True, exist_ok=True)

    log = (lambda *_a, **_k: None) if args.quiet else print

    if args.seed is not None:
        # Deterministic sequence: seed, seed-1, seed-2, ...
        targets = [
            {
                "id": f"{args.seed}-{i}",
                "author": "picsum-seed",
                "url": image_url(
                    0,
                    args.width,
                    args.height,
                    seed=f"{args.seed}-{i}",
                    grayscale=args.grayscale,
                    blur=args.blur,
                ),
                "filename": f"seed_{args.seed}_{i:02d}.jpg",
            }
            for i in range(1, args.count + 1)
        ]
    else:
        try:
            listing = fetch_random_image_list(args.count, args.timeout, page=args.page)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"Failed to fetch image list: {exc}", file=sys.stderr)
            return 1

        if not listing:
            print("No images found from Picsum.", file=sys.stderr)
            return 1

        if len(listing) < args.count:
            print(
                f"Only found {len(listing)} images (requested {args.count}).",
                file=sys.stderr,
            )

        targets = []
        for item in listing:
            image_id = item["id"]
            author = item.get("author", "unknown").replace(" ", "_")
            filename = f"picsum_{image_id}_{author}.jpg"
            targets.append(
                {
                    "id": image_id,
                    "author": item.get("author", "unknown"),
                    "url": image_url(
                        image_id,
                        args.width,
                        args.height,
                        seed=None,
                        grayscale=args.grayscale,
                        blur=args.blur,
                    ),
                    "filename": filename,
                }
            )

    downloaded = 0
    skipped = 0
    failed = 0

    for index, target in enumerate(targets, start=1):
        destination = args.output / target["filename"]
        if destination.exists() and not args.overwrite:
            log(f"[{index}/{len(targets)}] skip (exists): {destination.name}")
            skipped += 1
            continue

        try:
            http_download(target["url"], destination, args.timeout)
            size_kb = destination.stat().st_size / 1024
            log(
                f"[{index}/{len(targets)}] saved {destination.name} "
                f"({size_kb:.0f} KB) - {target['author']}"
            )
            downloaded += 1
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, OSError) as exc:
            print(f"[{index}/{len(targets)}] failed {target['filename']}: {exc}", file=sys.stderr)
            failed += 1

        if index < len(targets) and args.delay:
            time.sleep(args.delay)

    log(
        f"Done. downloaded={downloaded} skipped={skipped} failed={failed} "
        f"dir={args.output.resolve()}"
    )
    return 1 if failed and not downloaded else 0


# Parse command-line arguments and run the download workflow.
def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return download_photos(args)


if __name__ == "__main__":
    raise SystemExit(main())
