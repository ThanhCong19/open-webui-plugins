# Banner kit

Parametric generator + headless-render pipeline for the plugin README banners
(4:1 wide, dark, one accent + one motif per plugin). Add a new plugin banner by
adding one config entry and one motif function, then running two commands.

## Files

| File | What |
|------|------|
| `banners.py` | Generator. Holds the shared HTML/CSS template, the per-plugin configs, and the motif SVGs. Writes one `banner_<key>.html` per plugin. |
| `render.mjs` | Renders every `banner_*.html` here to `banner-<key>.png` at 2x (3200x800) via headless Chrome over CDP. |
| `promo.example.html` | Bonus: the taller 16:10 "hero" layout (a mock Valves panel on a designed background). Render at 1600x1000. |

## Run

```bash
python banners.py     # writes banner_<key>.html for every plugin in the config
node   render.mjs     # writes banner-<key>.png (2x) for each banner_*.html
```

Local machine paths (not on PATH):
- python: `C:\Users\Jakob\Documents\GitHub\openwebui-venv\Scripts\python.exe`
- node:   `C:\Users\Jakob\Documents\GitHub\node-v22.16.0-win-x64\node.exe`
- chrome: `C:\Program Files\Google\Chrome\Application\chrome.exe` (override with `CHROME=... node render.mjs`)

## Add a new plugin banner

In `banners.py`:

1. Write a motif function `m_<name>(a1, a2)` returning an inline `<svg width="384" height="300" viewBox="0 0 384 300">…</svg>`. Draw with the two accent colors passed in. Keep it iconic (5–10 elements). **Keep every element inside its bounds** — e.g. content sitting on a card must clear that card's border by ~8px (the To/CC/BCC chip overlap bug came from a rect running past the envelope's bottom edge).
2. Add a `banners["<key>"] = dict(a1=..., a2=..., emoji=..., title=..., title_size=..., badges=[...], tag="...", motif=m_<name>(a1, a2))`.
3. `python banners.py && node render.mjs`.

### Rules learned
- **No version numbers** in badges (they go stale). Badges carry *features* (`Event function`, `Auto-seed`, `Throttled`, `ui:// + CSP`, …), 2–3 words each, first one gets the accent fill, the rest a leading accent dot.
- Longer explanation lives in `tag`, not the badges.
- Motif goes in a framed "stage" (glass panel + concentric-ring backdrop + floating accent dots). That framing is in the shared template, so a motif only needs to draw its own icon.

## Design system (so a new banner matches)

- **Canvas** 1600x400 (4:1). Rendered at 2x for retina README use.
- **Background** flat dark (`#08090d`→`#0c0d14`), two accent radial glows (top-left `a1`, bottom-right `a2`), a masked dot-grid, and a left accent edge-line gradient.
- **Accent** per plugin: `a1` primary + `a2` secondary (a gradient pair). Current picks:
  interface-defaults indigo/violet · visualizer teal/purple · email blue/sky ·
  mcp-app-bridge emerald · vision amber/coral · prune teal/green.
- **Title** 78–88px, weight 800, gradient `#fff → a2`, paired with the plugin emoji glyph.
- **Layout** text left (badges → emoji+title → tagline), motif in the framed stage on the right (~470px column).
- **Flat only** — no drop shadows on content except the stage panel, no gradients on text fills beyond the title, min font ~15px.

## Use in a plugin README

```markdown
<p align="center"><img src="../.misc/banner-<key>.png" alt="<Plugin>" width="100%"></p>
```

(rendered `banner-*.png` are gitignored, regenerate with `node render.mjs`, or copy the PNG into the plugin folder and reference it locally.)
