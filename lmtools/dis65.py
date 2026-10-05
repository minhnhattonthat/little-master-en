"""Minimal linear 65816 disassembler for RE (tracks M/X width through REP/SEP only)."""

FMT = {"imp": "", "acc": "A", "imm8": "#${:02X}", "dp": "${:02X}", "dpx": "${:02X},x", "dpy": "${:02X},y",
       "idp": "(${:02X})", "idpx": "(${:02X},x)", "idpy": "(${:02X}),y", "ildp": "[${:02X}]", "ildpy": "[${:02X}],y",
       "sr": "${:02X},s", "sry": "(${:02X},s),y", "abs": "${:04X}", "absx": "${:04X},x", "absy": "${:04X},y",
       "iabs": "(${:04X})", "iabsx": "(${:04X},x)", "ilabs": "[${:04X}]", "long": "${:06X}", "longx": "${:06X},x"}
SIZE = {"imp": 1, "acc": 1, "abs": 3, "absx": 3, "absy": 3, "iabs": 3, "iabsx": 3, "ilabs": 3, "rell": 3, "bm": 3,
        "long": 4, "longx": 4}

OPS = {}
for i, mn in enumerate(["ORA", "AND", "EOR", "ADC", "STA", "LDA", "CMP", "SBC"]):
    for off, mode in [(1, "idpx"), (3, "sr"), (5, "dp"), (7, "ildp"), (9, "immM"), (0xD, "abs"), (0xF, "long"),
                      (0x11, "idpy"), (0x12, "idp"), (0x13, "sry"), (0x15, "dpx"), (0x17, "ildpy"), (0x19, "absy"),
                      (0x1D, "absx"), (0x1F, "longx")]:
        OPS[i * 0x20 + off] = (mn, mode)
OPS[0x89] = ("BIT", "immM")
for spec in """00 BRK imm8|02 COP imm8|04 TSB dp|06 ASL dp|08 PHP imp|0A ASL acc|0B PHD imp|0C TSB abs|0E ASL abs
10 BPL rel|14 TRB dp|16 ASL dpx|18 CLC imp|1A INC acc|1B TCS imp|1C TRB abs|1E ASL absx
20 JSR abs|22 JSL long|24 BIT dp|26 ROL dp|28 PLP imp|2A ROL acc|2B PLD imp|2C BIT abs|2E ROL abs
30 BMI rel|34 BIT dpx|36 ROL dpx|38 SEC imp|3A DEC acc|3B TSC imp|3C BIT absx|3E ROL absx
40 RTI imp|42 WDM imm8|44 MVP bm|46 LSR dp|48 PHA imp|4A LSR acc|4B PHK imp|4C JMP abs|4E LSR abs
50 BVC rel|54 MVN bm|56 LSR dpx|58 CLI imp|5A PHY imp|5B TCD imp|5C JML long|5E LSR absx
60 RTS imp|62 PER rell|64 STZ dp|66 ROR dp|68 PLA imp|6A ROR acc|6B RTL imp|6C JMP iabs|6E ROR abs
70 BVS rel|74 STZ dpx|76 ROR dpx|78 SEI imp|7A PLY imp|7B TDC imp|7C JMP iabsx|7E ROR absx
80 BRA rel|82 BRL rell|84 STY dp|86 STX dp|88 DEY imp|8A TXA imp|8B PHB imp|8C STY abs|8E STX abs
90 BCC rel|94 STY dpx|96 STX dpy|98 TYA imp|9A TXS imp|9B TXY imp|9C STZ abs|9E STZ absx
A0 LDY immX|A2 LDX immX|A4 LDY dp|A6 LDX dp|A8 TAY imp|AA TAX imp|AB PLB imp|AC LDY abs|AE LDX abs
B0 BCS rel|B4 LDY dpx|B6 LDX dpy|B8 CLV imp|BA TSX imp|BB TYX imp|BC LDY absx|BE LDX absy
C0 CPY immX|C2 REP imm8|C4 CPY dp|C6 DEC dp|C8 INY imp|CA DEX imp|CB WAI imp|CC CPY abs|CE DEC abs
D0 BNE rel|D4 PEI idp|D6 DEC dpx|D8 CLD imp|DA PHX imp|DB STP imp|DC JML ilabs|DE DEC absx
E0 CPX immX|E2 SEP imm8|E4 CPX dp|E6 INC dp|E8 INX imp|EA NOP imp|EB XBA imp|EC CPX abs|EE INC abs
F0 BEQ rel|F4 PEA abs|F6 INC dpx|F8 SED imp|FA PLX imp|FB XCE imp|FC JSR iabsx|FE INC absx""".replace("\n", "|").split("|"):
    op, mn, mode = spec.split()
    OPS[int(op, 16)] = (mn, mode)
assert len(OPS) == 256


def disasm(rom, pc, addr, n, m16=False, x16=False) -> list[str]:
    """Disassemble up to n instructions from rom[pc], which the CPU sees at SNES address `addr`."""
    out = []
    for _ in range(n):
        if pc >= len(rom):
            break
        mn, mode = OPS[rom[pc]]
        if mode in ("immM", "immX"):
            wide = m16 if mode == "immM" else x16
            size, text = (3, "#${:04X}") if wide else (2, "#${:02X}")
        else:
            size, text = SIZE.get(mode, 2), FMT.get(mode, "")
        raw = bytes(rom[pc:pc + size])
        val = int.from_bytes(raw[1:], "little")
        if mode == "rel":
            text = f"${(addr + 2 + (val - 256 if val > 127 else val)) & 0xFFFF:04X}"
        elif mode == "rell":
            text = f"${(addr + 3 + (val - 65536 if val > 32767 else val)) & 0xFFFF:04X}"
        elif mode == "bm":
            text = f"${raw[2]:02X},${raw[1]:02X}"
        else:
            text = text.format(val)
        if mn in ("REP", "SEP"):
            m16 = (mn == "REP") if val & 0x20 else m16
            x16 = (mn == "REP") if val & 0x10 else x16
        out.append(f"${addr >> 16:02X}:{addr & 0xFFFF:04X}  {raw.hex(' ')}  {mn} {text}".rstrip())
        pc, addr = pc + size, (addr & 0xFF0000) | ((addr + size) & 0xFFFF)
    return out
