# Geeth Upahar Motion Kit
Vector write-on animation for personalised song videos.
- shape.py: text -> glyph outlines via HarfBuzz + fontTools (correct Kannada/Tamil/Telugu/Malayalam/Hindi shaping)
- engine.js: deterministic render(t): pen-tip stroke draw-on, gold fill, shimmer, heart/flourish paths, sparkles
- build.py: scene spec (demo) -> scene.html; render.py: scene.html -> mp4 (Playwright frames + ffmpeg)
Use: python3 build.py scene.html && python3 render.py scene.html out.mp4 11 24 [audio.m4a]
