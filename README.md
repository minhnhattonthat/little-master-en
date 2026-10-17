# Little Master: Nijiiro no Maseki — English translation (SNES)

Fan translation of *Little Master: Nijiiro no Maseki* (Little Master: Jewels of Rainbow), Tokuma Shoten Intermedia / Zener Works, 1995.

**Play it:** download `LittleMaster_EN_v1.0.zip` from [Releases](../../releases), and apply the `.bps` to your own Japanese ROM (CRC32 `B916334C`, 2 MB, no header). Patched ROM CRC32 `85B10100`.

This repo holds the source only: no ROM data. Everything is built from the original ROM you supply.

- Full script translation (19 blocks, 3723 entries), variable-width font, relocated text, translated title subtitle.
- Build: put the ROM in `rom/`, then `python -X utf8 lm.py build`. Tools: Python 3, asar, Mesen2 (tests only). `python lm.py -h` lists commands.
- Notes: `docs/` (reverse engineering, style, playtest log), `glossary.md` (names).

Credits: minhnhattonthat, with Claude (Anthropic). Original game (c) 1995 Tokuma Shoten Intermedia / Zener Works.

## Support

If you enjoy this translation, you can support my work on Ko-fi:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/minhnhattonthat)
