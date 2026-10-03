"""Captioned 120-second walkthrough assembled from actual deployed UI captures.

Optional tooling: pip install Pillow imageio-ffmpeg
This is a screenshot walkthrough, not a continuous screen recording.
"""
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
steps = [
    ("01-comparison.png", "COMPARE RECOVERY POLICIES", [
        "A fictional supplier outage affects", "an electronics assembly business.",
        "Existing sourcing: 41 / 149 units.", "Greedy and optimized: 138 / 149.",
        "Optimization ties greedy here.", "All three plans pass independent checks."]),
    ("02-network.png", "TRACE THE EXPOSURE", [
        "Supplier -> component -> product", "shows potentially affected products.",
        "BOM quantities determine shortages.", "Stock and capacity cannot be reused.",
        "Location labels are not risk scores.", "Every supplier record is synthetic."]),
    ("03-recommendation.png", "REVIEW BEFORE ACTING", [
        "Inspect purchase units and lead times.", "Respect qualification and deadlines.",
        "The selected plan costs JPY 119,420.", "Eleven demand units remain unfilled.",
        "Export the recommendation and inputs.", "No actual purchase is executed."]),
    ("04-evidence.png", "CHECK THE EVIDENCE", [
        "Run the six live browser checks.", "41 Python / UI tests also pass.",
        "23 checks exercise a live HTTP server.", "25 browser / Python parity cases pass.",
        "Daily and stress extensions run in Python.", "External procurement validation is pending."])
]
font_dir = Path("C:/Windows/Fonts")
title_font = ImageFont.truetype(str(font_dir / "arialbd.ttf"), 27)
body_font = ImageFont.truetype(str(font_dir / "arial.ttf"), 22)
small_font = ImageFont.truetype(str(font_dir / "arial.ttf"), 16)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
with tempfile.TemporaryDirectory(prefix="supplyshield-video-") as temp:
    clips = []
    for i, (filename, title, lines) in enumerate(steps):
        canvas = Image.new("RGB", (1280, 720), "#f3f5f0")
        draw = ImageDraw.Draw(canvas)
        draw.text((30, 32), "SUPPLYSHIELD / DEMO WALKTHROUGH", font=small_font, fill="#16786c")
        draw.text((30, 75), title, font=title_font, fill="#173c34")
        for j, line in enumerate(lines):
            draw.text((30, 160 + j * 48), line, font=body_font, fill="#27473e")
        draw.text((30, 650), "Synthetic results; screenshot walkthrough.", font=small_font, fill="#54665f")
        capture = Image.open(root / "test-results/screenshots" / filename).convert("RGB")
        capture.thumbnail((730, 670), Image.Resampling.LANCZOS)
        canvas.paste(capture, (530 + (730 - capture.width) // 2, 25))
        still = Path(temp) / f"slide-{i}.png"
        clip = Path(temp) / f"clip-{i}.mp4"
        canvas.save(still)
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-loop", "1", "-i", str(still),
                        "-t", "30", "-r", "10", "-c:v", "libx264", "-preset", "ultrafast",
                        "-crf", "22", "-pix_fmt", "yuv420p", str(clip)], check=True)
        clips.append(clip)
    manifest = Path(temp) / "clips.txt"
    manifest.write_text("\n".join("file '" + str(p).replace("\\", "/") + "'" for p in clips), encoding="utf-8")
    output = root / "docs/walkthrough.mp4"
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(manifest), "-c", "copy", "-movflags", "+faststart", str(output)], check=True)
    print(f"Created {output.name}: 120 seconds, {output.stat().st_size:,} bytes")
