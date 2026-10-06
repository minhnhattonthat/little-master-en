# Playtest guide (M6)

## How to play a release candidate

1. Run `python lm.py release --version 1.0-rcN`. This writes `dist/LittleMaster_EN_v1.0-rcN.zip`, with the `.bps` and `README.txt` inside.
2. Patch your Japanese ROM as the README says, or play `build/lm_en.sfc` directly.
3. Play in **Mesen2**.
4. Also boot it **once in a second emulator** (bsnes or Snes9x) and go to the title screen. Check that the subtitle reads "~ Jewels of Rainbow ~" and isn't garbled. This confirms the bank `$40` mirror that the title graphics rely on (M5).

## Checklist

- [ ] Title, intro and opening scenes
- [ ] Each scenario: briefing, field dialogue, battles (attack and magic messages, level-up, status popups)
- [ ] Menus: unit info, items, equip, shop, hospital, config, report, scenario info, terrain info
- [ ] Save and load
- [ ] Ending and staff roll
- [ ] Anything cut off, overlapping, unreadable, untranslated or oddly worded
- [ ] If a **small speech-bubble graphic with tiny lettering** appears (ROM `09DB16`, M5 open item), save a state there

## How to report

For each problem, add a row to the bug log:
- **where:** scenario or place;
- **problem:** what you saw, and what you expected;
- **state:** a save-state name. In Mesen2, use *File → Save State → Save to file…*, then copy the `.mss` into `test/states/`.

Status starts as `open`. When it's fixed, the row gets the test name and the commit. `wontfix` rows get a reason in the test column.

## Bug log

| # | where | problem | state | status | test | commit |
|---|---|---|---|---|---|---|
| B1 | map, System menu | cursor can't move; froze when hovering Item (description hit the wrap column, engine waited for a key) | bug_menu | fixed | test_system_menu_cursor_leaves_item | 2ddfc32 |
| C1 | menus (engine) | `$57=$FE` VWF tile upload lost when `$10 ≥ 2` (M3 review) | | open | | |
| C2 | text (engine) | `!partial` survives the D0 glyph path (M3 review) | | open | | |
| C3 | text (engine) | each message start takes a new VWF slot (M3 review) | | open | | |
| C4 | script | wording polish: msg36 #445 #482 #231 #574 #270/#548/#606 #391 #612; ev0A #193 #301 #287; ev22 #62 (M4 review) | | open | | |
| C5 | unknown screen | `09DB16` speech-bubble graphic not yet seen (M5) | | open | | |

## Notes

- The world map spells the ruins JUSVAN, in the game's own decorative letters. The script uses *Jasvan*, by user ruling. This is not a bug.
