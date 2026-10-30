# Little Master: Nijiiro no Maseki — English translation (SNES)

Fan translation of *Little Master: Nijiiro no Maseki* (Little Master: Jewels of Rainbow), Tokuma Shoten Intermedia / Zener Works, 1995.

**Play it:** download `LittleMaster_EN_v1.0.zip` from [Releases](../../releases), and apply the `.bps` to your own Japanese ROM (CRC32 `B916334C`, 2 MB, no header). Patched ROM CRC32 `85B10100`.

**Found a bug?** [Report it](../../issues/new/choose): untranslated text, typos, overflow, crashes. Attaching a savestate helps most.

## Translation status

| Part | Status |
|---|---|
| Dialogue / story | Translated |
| Units, items, spells, monsters, battle messages | Translated |
| Title screen | Translated (subtitle "~ Jewels of Rainbow ~") |
| World-map labels, UI label graphics, intro credits | English in the original (the map art spells Jusvan; the script uses Jasvan) |
| Ending staff roll | Not checked in play (language not decided yet) |

Known issues: one speech-bubble graphic (ROM `09DB16`) may still be Japanese; not yet seen in game. Bug log: [docs/playtest.md](docs/playtest.md).

This repo holds the source only: no ROM data. Everything is built from the original ROM you supply.

- Full script translation (19 blocks, 3723 entries), variable-width font, relocated text, translated title subtitle.

## What's here

| Path | What it is |
|---|---|
| `script/` | Every text block: original Japanese and English. Translation fixes go here. |
| `glossary.md`, `docs/style.md` | Binding names, terms and style rules. |
| `lm.py`, `lmtools/` | Python build chain: dump, insert, lint, build, release (`python lm.py -h`). |
| `src/` | 65816 asm hacks (VWF, relocation), VWF font, title graphics. |
| `tbl/`, `data/` | Character tables; block, window and graphics definitions. |
| `tests/` | pytest suite (ROM-dependent tests skip when the ROM is absent; Mesen tests need Mesen2 and savestates). |
| `tools/` | Dump check (`check_rom.py`), disk cleanup (`clean.py`), Mesen2 Lua scripts (`lua/`). |
| `docs/re/` | Reverse-engineering notes. |
| `docs/decisions.md`, `docs/status.md`, `docs/playtest.md` | Rulings with their reasons; current progress; playtest guide and bug log. |
| `docs/fonts.md` | Fonts used and their licences. |
| `AGENTS.md` | Instructions for coding agents (`CLAUDE.md` points to it). |

## Build your own patched ROM

Needs Python 3.12+, [asar](https://github.com/RPGHacker/asar) in `tools/asar/`, and your own dump of the Japanese game.

```sh
git clone https://github.com/minhnhattonthat/little-master-en
cd little-master-en
# copy your dump to: rom/Little Master - Nijiiro no Maseki (Japan).sfc
#   (2,097,152 bytes, SHA-1 75b76715d4a20371e0340dbeee3a51ff6a1dbad3; the build refuses any other dump, see rom.sha1)
python -X utf8 lm.py build                             # -> build/lm_en.sfc + lm_en.bps
python -X utf8 lm.py lint && python -X utf8 -m pytest -q -m "not mesen"   # text lint + tests
```

Mesen2 (`tools/mesen2/`) is only needed for the runtime tests.

## Support

If you enjoy this translation, you can support my work on Ko-fi:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/minhnhattonthat)

## Licence

Tools and English translation: MIT. The original Japanese text in `script/` is Tokuma Shoten Intermedia / Zener Works'
and is included only so the translation can be checked against it. Little Master: Nijiiro no Maseki is (c) 1995
Tokuma Shoten Intermedia / Zener Works; this project is not affiliated with them. Do not share patched ROMs.

Credits: minhnhattonthat. The translation was made with extensive AI assistance (Claude by Anthropic). Corrections are
very welcome.
