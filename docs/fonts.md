# Fonts

Every font or glyph sheet the build reads ends up inside the released patch, so its licence must allow that. One row
per file; a font with no known licence doesn't go into a release.

| File | Source (URL, version) | Licence | Redistributable in a patch | Used for | Changes made |
|---|---|---|---|---|---|
| `asm/font6x12.bin` | X11 misc-fixed 6x12 BDF (`make_font.py work/6x12.bdf`) | public domain | yes | half-width dialogue/menu font (asm/halfwidth.asm) | 95 glyphs 0x20-0x7E, 1 bit per pixel |
| `C:\Windows\Fonts\arialbd.ttf`, `arialbi.ttf`, `ARIALNB.TTF`, `ARIALNBI.TTF` | Windows | Microsoft font EULA | as rendered 1-bit glyphs only (font file not shipped) | redrawn picture text (labels.py: titles, menus, save screen, prompts) | - |
| `C:\Windows\Fonts\tahoma.ttf` | Windows | Microsoft font EULA | as rendered glyphs only | NPC/speaker name plates (labels.py) | - |
| `C:\Windows\Fonts\impact.ttf` | Windows | Microsoft font EULA | as rendered glyphs only | free-battle place names (labels.places) | - |
| `C:\Windows\Fonts\times.ttf`, `timesbd.ttf`, `timesi.ttf`, `timesbi.ttf` | Windows | Microsoft font EULA | as rendered glyphs only | disc-change screen glow, battle objective banners, stage title cards (labels.py) | - |
| Arial (ASS style in movie.py, via libass) | Windows | Microsoft font EULA | as burned-in video pixels only | movie subtitles | - |
