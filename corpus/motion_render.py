#!/usr/bin/env python3
"""The clips, rendered: each feature's page in motion stepped frame by frame into video, and put on its release.

THE PAGE IS THE CLIP; this is the camera. `wherefore motion` writes a page
per feature whose motion is CSS and which, marked `still` with `--t` set,
stands at that second. This opens each page in a browser at the frame's
size - portrait 1080x1920, landscape 1920x1080 - sets `--t` to each frame's
time, screenshots it, and has ffmpeg join the frames: a silent, captioned
clip of the length the storyboard says, the same every time it is rendered
from the same page. A poster, the claim scene's middle frame, comes with it.

THE BRAND IS THE SITE'S. The pages are written into a checkout of the
company's site (wherefore-build/web), beside its brand stylesheet and fonts,
so the clips are the site's own look; one is cloned when none is given.

ONTO THE RELEASE. With --upload, each feature's clips go on the GitHub
release of the version the feature arrived in (gh, signed in), where the
release notes already are and the inbox's closing note on the issue links
them (corpus/inbox.py). A feature whose release was never cut is said and
skipped.

    python3 corpus/motion_render.py --version 0.20.0 [--upload]    the features since that release
    python3 corpus/motion_render.py --version all [--upload]       every feature, onto its own release
    python3 corpus/motion_render.py published gate --site ../web   named features, this checkout of the site

Needs: playwright (pip install playwright; python3 -m playwright install chromium) and ffmpeg.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wherefore import motion  # noqa: E402

REPO = "wherefore-build/wherefore"
SITE_REPO = "https://github.com/wherefore-build/web"
FRAMES = {"portrait": (1080, 1920), "landscape": (1920, 1080)}
FPS = 24


def site_checkout(given):
    if given:
        root = pathlib.Path(given).resolve()
        if not (root / "site/brand.css").is_file():
            raise SystemExit(f"::error::{root} is not a checkout of the site: no site/brand.css")
        return root
    root = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-site-")) / "web"
    subprocess.run(["git", "clone", "--quiet", "--depth", "1", SITE_REPO, str(root)], check=True)
    return root


def chosen(ids, version):
    feats = motion.features()
    if ids:
        unknown = sorted(set(ids) - {f["id"] for f in feats})
        if unknown:
            raise SystemExit(f"::error::no feature called {', '.join(unknown)}")
        return [f for f in feats if f["id"] in ids]
    if version == "all":
        return feats
    return [f for f in feats if f["since"] == version]


def render(page_path, board, frame, out, fps):
    """out/<id>-<frame>.mp4 from the page at the frame's size; the poster for the portrait frame."""
    from playwright.sync_api import sync_playwright
    w, h = FRAMES[frame]
    n = int(round(board["duration"] * fps))
    frames = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-frames-"))
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            pg = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
            pg.goto(page_path.resolve().as_uri(), wait_until="load")
            pg.evaluate("document.documentElement.classList.add('still')")
            pg.evaluate("document.fonts.ready")
            for i in range(n):
                pg.evaluate("t => document.documentElement.style.setProperty('--t', t)", round(i / fps, 4))
                pg.screenshot(path=str(frames / f"{i:05d}.jpg"), type="jpeg", quality=88)
            poster = None
            if frame == "portrait":
                claim = next(s for s in board["scenes"] if s["kind"] == "claim")
                pg.evaluate("t => document.documentElement.style.setProperty('--t', t)", (claim["start"] + claim["end"]) / 2)
                poster = out / f"{board['id']}.png"
                pg.screenshot(path=str(poster), type="png")
            browser.close()
        clip = out / f"{board['id']}-{frame}.mp4"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(fps), "-i", str(frames / "%05d.jpg"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", str(clip)],
                       check=True)
        return clip, n, poster
    finally:
        shutil.rmtree(frames, ignore_errors=True)


def upload(version, files):
    tag = f"v{version}"
    seen = subprocess.run(["gh", "release", "view", tag, "--repo", REPO, "--json", "tagName"], capture_output=True, text=True)
    if seen.returncode:
        print(f"::notice::no release {tag} to put the clips on; skipped {', '.join(f.name for f in files)}")
        return False
    subprocess.run(["gh", "release", "upload", tag, *map(str, files), "--repo", REPO, "--clobber"], check=True)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ids", nargs="*", help="features to render; none means --version's")
    ap.add_argument("--version", help="the release whose features to render, or all")
    ap.add_argument("--site", help="a checkout of wherefore-build/web; cloned when not given")
    ap.add_argument("--out", default="clips", help="where the clips go (default clips/)")
    ap.add_argument("--fps", type=int, default=FPS)
    ap.add_argument("--upload", action="store_true", help="put each feature's clips on its release")
    a = ap.parse_args(argv)
    if not a.ids and not a.version:
        ap.error("name features, or --version VERSION|all")
    feats = chosen(a.ids, a.version)
    if not feats:
        print(f"no feature arrived in {a.version}: nothing to render")
        return 0
    site = site_checkout(a.site)
    out = pathlib.Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    # THE SITE'S OWN CLIPS: its wherefore.json names the brand stylesheet, its
    # copy of the roadmap and where the clips go, and its own numbers fill
    # each mechanism scene - the clips on a release are the site's.
    from wherefore import config as cfgmod
    cfg = cfgmod.load(site)
    settings = motion.settings_from(cfg)
    boards = motion.storyboards([f["id"] for f in feats], site, settings, cfg)
    pages = site / settings.get("out", "site/motion")
    css = site / settings["css"] if settings.get("css") else site / "site/brand.css"
    motion.write(boards, pages, css, settings.get("vars"), out, site)
    for b in boards:
        files, said = [], []
        for frame in FRAMES:
            clip, n, poster = render(pages / b["id"] / "index.html", b, frame, out, a.fps)
            files.append(clip)
            said.append(f"{frame} {n} frames")
            if poster:
                files.append(poster)
        line = f"  {b['id']:<12} {b['duration']:>4.1f} s  {', '.join(said)}"
        if a.upload:
            line += f"  -> v{b['version']}" if upload(b["version"], files) else "  (not uploaded)"
        print(line)
    print(f"wrote {out}: {len(boards)} feature{'s' if len(boards) != 1 else ''}, two clips and a poster each")
    return 0


if __name__ == "__main__":
    sys.exit(main())
