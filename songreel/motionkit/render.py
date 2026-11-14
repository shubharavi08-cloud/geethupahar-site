"""Render a motion scene to MP4:  python3 render.py scene.html out.mp4 SECONDS [FPS] [audio.m4a]"""
import sys, asyncio, subprocess, os, tempfile, shutil
from playwright.async_api import async_playwright
async def frames(scene, d, n, fps, workers=3):
    async def work(w):
        async with async_playwright() as p:
            b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 540, "height": 960}, device_scale_factor=2)
            await pg.goto("file://" + os.path.abspath(scene)); await pg.wait_for_timeout(500)
            for i in range(w, n, workers):
                await pg.evaluate(f"render({i/fps})"); await pg.screenshot(path=f"{d}/{i:05d}.jpg", type="jpeg", quality=93)
            await b.close()
    await asyncio.gather(*[work(w) for w in range(workers)])
def main():
    scene, out, secs = sys.argv[1], sys.argv[2], float(sys.argv[3]); fps = int(sys.argv[4]) if len(sys.argv) > 4 else 24
    audio = sys.argv[5] if len(sys.argv) > 5 else None; n = int(secs * fps); d = tempfile.mkdtemp()
    asyncio.run(frames(scene, d, n, fps))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", f"{d}/%05d.jpg"] + (["-i", audio] if audio else []) + \
          ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"] + (["-c:a", "aac", "-shortest"] if audio else []) + ["-movflags", "+faststart", out]
    subprocess.run(cmd, check=True); shutil.rmtree(d); print("wrote", out)
if __name__ == "__main__": main()
