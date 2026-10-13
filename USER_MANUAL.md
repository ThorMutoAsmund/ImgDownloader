# Stock Photo Downloader - User Manual

## Overview

`download_stock_photos.py` downloads JPEG photos from [Lorem Picsum](https://picsum.photos), a free service that serves Unsplash-sourced stock images. No API key is required. The script uses only the Python standard library.

## Requirements

- Python 3.10 or newer
- Internet connection

## Quick start

From the folder that contains the script:

```bat
python download_stock_photos.py
```

This downloads **10** random JPEGs (1280x720) into a `photos` folder.

Show all options:

```bat
python download_stock_photos.py --help
```

## Common examples

Download 10 photos into `photos`:

```bat
python download_stock_photos.py -n 10 -o photos
```

Larger images:

```bat
python download_stock_photos.py --width 1920 --height 1080
```

Grayscale with a light blur:

```bat
python download_stock_photos.py --grayscale --blur 2
```

Same images every time (reproducible):

```bat
python download_stock_photos.py --seed demo
```

Force overwrite of existing files:

```bat
python download_stock_photos.py --overwrite
```

## Command-line options

| Option | Default | Description |
|--------|---------|-------------|
| `-n`, `--count` | `10` | Number of photos to download |
| `-o`, `--output` | `photos` | Output directory |
| `--width` | `1280` | Image width in pixels |
| `--height` | `720` | Image height in pixels |
| `--page` | *(random)* | Use one Picsum list page only (1-10) |
| `--seed` | *(none)* | Reproducible Picsum seed mode |
| `--grayscale` | off | Download grayscale images |
| `--blur 1-10` | off | Apply blur level 1-10 |
| `--timeout` | `30` | HTTP timeout in seconds |
| `--delay` | `0.2` | Pause between downloads (seconds) |
| `--overwrite` | off | Replace existing files with the same name |
| `-q`, `--quiet` | off | Print errors only |
| `-h`, `--help` | - | Show help and exit |

## How image selection works

- **Default:** each run samples **random** images from the Picsum catalog, so calling the script twice usually yields different photos.
- **`--page N`:** take images from list page `N` only (still shuffled within that page's pool when sampling).
- **`--seed NAME`:** download a fixed, reproducible set based on Picsum seeds.

Files are named like `picsum_<id>_<author>.jpg`. If a file already exists and `--overwrite` is not set, that download is skipped.

## Output

- Progress lines show each saved, skipped, or failed file.
- A summary line reports counts and the absolute output directory path.
- Exit code `0` means success (or only skips); a non-zero code indicates a hard failure or that nothing could be downloaded.

## Notes

- Be polite to the service; the default `--delay` adds a short pause between requests.
- Image availability depends on Lorem Picsum; occasional network or empty-result errors can occur.
- Photos are for use under the terms of Lorem Picsum / the original Unsplash photographers' licenses.

## License / attribution

Images come from Lorem Picsum (https://picsum.photos). Credit photographers when your use case requires it.
