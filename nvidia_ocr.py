#!/usr/bin/env python3
"""
NVIDIA Nemotron Parse OCR Tool

Converts documents (PDF, images, video frames) to text using NVIDIA's Nemotron Parse API.

Requirements:
  - NVIDIA_API_KEY environment variable set
  - pdftoppm (for PDF conversion)
  - ffmpeg (for video/image conversion)

Usage:
  python nvidia_ocr.py document.pdf
  python nvidia_ocr.py *.pdf --output results.txt
  python nvidia_ocr.py video.mp4 --frames 10
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

# Default values
DEFAULT_MODEL = "nvidia/nemotron-parse"
DEFAULT_DPI = 200
DEFAULT_MAX_TOKENS = 4096
API_RATE_LIMIT = 0.3  # seconds between requests


def check_dependencies() -> dict:
    """Check which conversion tools are available."""
    tools = {
        "pdftoppm": None,
        "ffmpeg": None,
        "sips": None,  # macOS built-in
        "magick": None,  # ImageMagick
    }

    for tool in tools:
        try:
            result = subprocess.run(
                ["which", tool],
                capture_output=True,
                text=True,
                timeout=5
            )
            tools[tool] = result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            tools[tool] = None

    # Special check for sips (macOS)
    if sys.platform == "darwin":
        try:
            subprocess.run(["sips", "--version"], capture_output=True, timeout=5)
            tools["sips"] = "/usr/bin/sips"
        except Exception:
            pass

    return tools


def pdf_to_pages(pdf_path: str, output_dir: str, dpi: int = DEFAULT_DPI, max_pages: int = None) -> List[str]:
    """Convert PDF to individual PNG pages using pdftoppm."""
    pdf_name = Path(pdf_path).stem
    cmd = [
        "pdftoppm",
        "-png",
        "-r", str(dpi),
    ]

    # Add page range limit if specified
    if max_pages:
        cmd.extend(["-l", str(max_pages)])

    cmd.extend([pdf_path, f"{output_dir}/{pdf_name}"])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"pdftoppm failed: {result.stderr}")

    # Find generated files
    pattern = f"{pdf_name}-*.png"
    files = sorted(Path(output_dir).glob(pattern))
    return [str(f) for f in files]


def image_to_png(image_path: str, output_dir: str) -> str:
    """Convert image to PNG using sips (macOS) or ffmpeg."""
    input_path = Path(image_path)
    output_path = Path(output_dir) / f"{input_path.stem}.png"

    if sys.platform == "darwin":
        cmd = ["sips", "-s", "format", "png", str(input_path), "--out", str(output_path)]
    else:
        cmd = ["ffmpeg", "-i", str(input_path), "-frames:v", "1", str(output_path)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Image conversion failed: {result.stderr}")

    return str(output_path)


def video_to_frames(video_path: str, output_dir: str, num_frames: int = 10) -> List[str]:
    """Extract frames from video using ffmpeg."""
    video_name = Path(video_path).stem
    output_pattern = str(Path(output_dir) / f"{video_name}_%03d.png")

    # Calculate frame interval
    probe_cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-count_packets", "-show_entries", "stream=nb_read_packets",
        "-of", "csv=p=0", str(video_path)
    ]

    try:
        result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
        total_frames = int(result.stdout.strip().split(",")[0])
        interval = max(1, total_frames // num_frames)
    except Exception:
        interval = 1

    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", f"select='not(mod(n\\,{interval}))'",
        "-vsync", "0", "-frames:v", str(num_frames),
        output_pattern
    ]

    subprocess.run(cmd, capture_output=True, text=True)

    files = sorted(Path(output_dir).glob(f"{video_name}_*.png"))
    return [str(f) for f in files]


def prepare_images(input_paths: List[str], output_dir: str, **kwargs) -> List[dict]:
    """
    Convert input files to PNG images ready for OCR.

    Returns list of dicts with: {path, source_file, page/frame}
    """
    tools = check_dependencies()
    images = []

    print(f"Available tools: {', '.join([k for k,v in tools.items() if v])}")

    for input_path in input_paths:
        path = Path(input_path)

        if not path.exists():
            print(f"Warning: {input_path} does not exist, skipping")
            continue

        if path.suffix.lower() == ".pdf":
            if not tools.get("pdftoppm"):
                print(f"Error: pdftoppm required for PDFs. Install: brew install poppler")
                continue
            print(f"Converting PDF: {input_path}")
            pages = pdf_to_pages(str(path), output_dir, dpi=kwargs.get("dpi", DEFAULT_DPI), max_pages=kwargs.get("max_pages"))
            for i, page_path in enumerate(pages, 1):
                images.append({"path": page_path, "source": str(path), "page": i})

        elif path.suffix.lower() in [".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"]:
            print(f"Converting image: {input_path}")
            png_path = image_to_png(str(path), output_dir)
            images.append({"path": png_path, "source": str(path), "page": 1})

        elif path.suffix.lower() in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
            if not tools.get("ffmpeg"):
                print(f"Error: ffmpeg required for video. Install: brew install ffmpeg")
                continue
            num_frames = kwargs.get("frames", 10)
            print(f"Extracting {num_frames} frames from: {input_path}")
            frames = video_to_frames(str(path), output_dir, num_frames)
            for i, frame_path in enumerate(frames, 1):
                images.append({"path": frame_path, "source": str(path), "page": i})

        elif path.suffix.lower() == ".png":
            images.append({"path": str(path), "source": str(path), "page": 1})

        else:
            print(f"Warning: Unsupported format: {path.suffix}")

    return images


def ocr_with_nvidia(image_path: str, api_key: str, model: str = DEFAULT_MODEL) -> Optional[str]:
    """Send image to NVIDIA Nemotron Parse API and return extracted text."""
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    payload = {
        "model": model,
        "tools": [{"type": "function", "function": {"name": "markdown_no_bbox"}}],
        "messages": [{
            "role": "user",
            "content": [{
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"}
            }]
        }],
        "temperature": 0.0,
        "max_tokens": DEFAULT_MAX_TOKENS
    }

    # Write payload to temp file to avoid argument list length limit
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(payload, f)
        payload_file = f.name

    try:
        result = subprocess.run([
            "curl", "-s", "https://integrate.api.nvidia.com/v1/chat/completions",
            "-H", f"Authorization: Bearer {api_key}",
            "-H", "Content-Type: application/json",
            "-d", f"@{payload_file}"
        ], capture_output=True, text=True, timeout=60)
    finally:
        os.unlink(payload_file)

    try:
        resp = json.loads(result.stdout)
        tool_calls = resp.get('choices', [{}])[0].get('message', {}).get('tool_calls', [])
        if tool_calls:
            args = tool_calls[0].get('function', {}).get('arguments', '[]')
            return json.loads(args)[0].get('text', '')
    except Exception as e:
        print(f"  API error: {e}")

    return None


def main():
    parser = argparse.ArgumentParser(
        description="OCR documents using NVIDIA Nemotron Parse API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("inputs", nargs="+", help="Input files (PDF, images, video)")
    parser.add_argument("-o", "--output", help="Output text file")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="PDF DPI (default: 200)")
    parser.add_argument("--frames", type=int, default=10, help="Frames per video (default: 10)")
    parser.add_argument("--max-pages", type=int, default=None, help="Max pages per PDF to process")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="NVIDIA model name")
    parser.add_argument("--temp-dir", help="Temporary directory for conversions")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without OCR")

    args = parser.parse_args()

    # Check API key
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        print("Error: NVIDIA_API_KEY environment variable not set")
        sys.exit(1)

    # Create temp directory
    with tempfile.TemporaryDirectory(prefix="nvidia_ocr_") as temp_dir:
        if args.temp_dir:
            temp_dir = args.temp_dir
            os.makedirs(temp_dir, exist_ok=True)

        print(f"Using temp directory: {temp_dir}")

        # Prepare images
        images = prepare_images(args.inputs, temp_dir, dpi=args.dpi, frames=args.frames, max_pages=args.max_pages)

        if not images:
            print("No images to process")
            sys.exit(1)

        print(f"\nPrepared {len(images)} images for OCR")

        if args.dry_run:
            for img in images:
                print(f"  {img['path']} <- {img['source']} (page {img['page']})")
            sys.exit(0)

        # Process images
        results = []
        for i, img in enumerate(images, 1):
            print(f"\n[{i}/{len(images)}] OCR: {Path(img['path']).name}")
            text = ocr_with_nvidia(img['path'], api_key, args.model)

            if text:
                separator = f"\n{'='*60}\n"
                source_info = f"SOURCE: {img['source']}"
                page_info = f"PAGE: {img['page']}" if img['page'] > 1 else ""
                header = f"{separator}{source_info} {page_info}\n{separator}"
                results.append(header + text)
                print(f"  Extracted {len(text)} characters")
            else:
                print(f"  Failed to extract text")

            import time
            time.sleep(API_RATE_LIMIT)

        # Output results
        output_text = "\n".join(results)

        if args.output:
            with open(args.output, "w") as f:
                f.write(output_text)
            print(f"\nSaved to {args.output}")
            print(f"  Total characters: {len(output_text)}")
            print(f"  Total lines: {output_text.count(chr(10))}")
        else:
            print("\n" + "="*60)
            print(output_text)

        # Keep temp files if requested
        if args.keep_temp and args.temp_dir:
            print(f"\nTemp files saved in: {temp_dir}")


if __name__ == "__main__":
    main()
