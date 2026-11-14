"""Text -> vector glyph outlines (HarfBuzz shaping + fontTools outlines). Works for Latin and Indic scripts."""
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

_cache = {}
def _load(path):
    if path not in _cache:
        blob = hb.Blob.from_file_path(path); face = hb.Face(blob); font = hb.Font(face)
        tt = TTFont(path); _cache[path] = (font, tt, tt.getGlyphSet(), face.upem)
    return _cache[path]

def text_paths(text, fontpath, size, script=None, lang=None, direction="ltr"):
    """Return dict(glyphs=[{d,x}], width, ascent, descent). Paths are in px, y-down, baseline at y=0."""
    font, tt, gs, upem = _load(fontpath)
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
    if script: buf.script = script
    if lang: buf.language = lang
    hb.shape(font, buf, {"kern": True, "liga": True})
    order = tt.getGlyphOrder(); s = size / upem; x = 0; out = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = order[info.codepoint]; pen = SVGPathPen(gs, ntos=lambda v: f"{v:.2f}")
        gs[name].draw(TransformPen(pen, (s, 0, 0, -s, x + pos.x_offset * s, -pos.y_offset * s)))
        d = pen.getCommands()
        if d: out.append({"d": d})
        x += pos.x_advance * s
    hhea = tt["hhea"]
    return {"glyphs": out, "width": x, "ascent": hhea.ascent * s, "descent": -hhea.descent * s}
