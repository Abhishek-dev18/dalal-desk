# The README film

`docs/demo.gif` and `docs/demo.mp4` are rendered from `index.html`: a 41-second walkthrough in the
"Mascot Screencast" style. The Claude Code window is redrawn in HTML, and an original pixel bull acts
out what the tool is doing. Every number on screen is real `dd.py` output on the synthetic sample
data in `tests/fixtures.py`; the prompts and replies are scripted.

This folder is build tooling only. Nothing in `dalal/` depends on it.

## Rebuild

Needs Chrome, ffmpeg and `pip install playwright`. Put two open-licensed fonts in `tools/film/fonts/`:
`Inter.ttf` (Inter variable) and `JetBrainsMono.ttf` (JetBrains Mono variable).

```
cd tools/film
python3 shoot.py stills 5.3 20.8      # check a few frames first
python3 shoot.py film                 # one mp4 per chapter in scenes/
for i in 0 1 2 3 4; do echo "file 'scenes/s$i.mp4'"; done > list.txt
ffmpeg -f concat -safe 0 -i list.txt -c copy ../../docs/demo.mp4
ffmpeg -i ../../docs/demo.mp4 -vf "fps=12,scale=760:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle" ../../docs/demo.gif
```

If the tool's output changes, update the numbers in the `CH` table at the top of the script in `index.html`.
