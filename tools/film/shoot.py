"""Film index.html with headless Chrome. stills: python3 shoot.py stills 4.6 12.4 ...   film: python3 shoot.py film"""
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
FPS = 30
SEAMS = [0, 7.6, 16.2, 24.6, 32.4, 41.0]


def page_of(p):
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox", "--allow-file-access-from-files"])
    pg = b.new_page(viewport={"width": 1280, "height": 720})
    pg.goto(f"file://{HERE}/index.html")
    pg.wait_for_function("window.READY === true")
    return b, pg


with sync_playwright() as p:
    b, pg = page_of(p)
    if sys.argv[1] == "stills":
        (HERE / "stills").mkdir(exist_ok=True)
        for t in sys.argv[2:]:
            pg.evaluate(f"window.render({t})")
            pg.screenshot(path=str(HERE / "stills" / f"t{t}.png"))
        print("stills done")
    else:
        (HERE / "scenes").mkdir(exist_ok=True)
        only = [int(x) for x in sys.argv[2:]] or range(len(SEAMS) - 1)
        for i in only:
            a, z = SEAMS[i], SEAMS[i + 1]
            tmp, out = HERE / "scenes" / f"s{i}.part.mp4", HERE / "scenes" / f"s{i}.mp4"
            ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS),
                                   "-c:v", "mjpeg", "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
                                   "-pix_fmt", "yuv420p", "-r", str(FPS), str(tmp)], stdin=subprocess.PIPE)
            n0, n1 = round(a * FPS), round(z * FPS)
            for n in range(n0, n1):
                pg.evaluate(f"window.render({n / FPS})")
                ff.stdin.write(pg.screenshot(type="jpeg", quality=92))
            ff.stdin.close()
            if ff.wait() != 0:
                sys.exit(f"ffmpeg failed on scene {i}")
            tmp.rename(out)
            print(f"scene {i}: {n1 - n0} frames")
    b.close()
