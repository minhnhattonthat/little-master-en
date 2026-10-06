; VWF for the message renderer. Design + RE: docs/re/text-engine.md "Dynamic tiles and VWF hooks".
;
; Each text line gets a "line slot" of 27 cells (216 px, the lint limit), taken from the top of the dynamic tiles
; down: slot L is tiles $180 + 128 - (L+1)*27 ..., the first line after a window clear takes slot 0, and cell c of a
; line is tile slot0 + c - col0 (col0 = cursor column of the line's first glyph). Window labels drawn as UI glyphs
; fill the tiles from the bottom up (from 2*$0A1A, sometimes drawn after the text), so they stay clear of the slots.
; Glyphs are ORed into those 2bpp tiles (plane 0 = top 8 rows, plane 1 = bottom 8 rows) and the
; whole slot buffer is uploaded by the NMI ($57 = $FE) once per screen update: drawing only marks the buffer
; dirty, and the hook on the game's tilemap upload ($00:C20E) sends the tiles first. Tiles are stored EOR $6F
; (the game's font is inverted: $6F = $FFFF in every window seen).
; Fixed font (original renderer) is used when: menu mode ($0A1C),
; too few line slots for the window, a cursor-set code appeared in the message, the cursor is above the
; window, or char not $20-$7E.
; All VWF RAM is long-addressed (.l): DB belongs to the game.

!px     = $7FFF00         ; pixel offset inside the current cell (0-7)
!line   = $7FFF02         ; current line slot
!gptr   = $7FFF04         ; glyph pointer inside bank $C0
!toff   = $7FFF06         ; byte offset of the current cell's tile inside !slots
!row    = $7FFF08         ; glyph row 0-15
!wid    = $7FFF0A         ; glyph advance width
!v      = $7FFF0C         ; glyph row << 8 >> px
!tile   = $7FFF0E         ; tile number of the current cell
!base   = $7FFF10         ; first VWF tile index (0-127) = 2*$0A1A
!nlines = $7FFF12         ; number of line slots
!novwf  = $7FFF14         ; nonzero: fixed font for the rest of this message
!partial = $7FFF16        ; nonzero: the game cursor sits one cell past a partly filled cell
!dirty  = $7FFF18         ; nonzero: !slots changed since the last upload
!needslot = $7FFF1A       ; nonzero: the next VWF glyph starts a fresh line slot (lazy: empty lines cost nothing)
!col    = $7FFF1C         ; cell index (column - !col0) of the glyph being drawn
!width  = $7FFF1E         ; cells per line slot
!col0   = $7FFF20         ; cursor column of the current line's first glyph
!slot0  = $7FFF22         ; first tile index (0-127) of the current line slot
!slots  = $7FB000         ; 128 x 16-byte tiles -> VRAM $6C00 (BG tiles $180-$1FF)

org $00BE43               ; renderer message start; was: STZ $0A10 / STZ $0A06
    JML vwf_start
    NOP : NOP

org $00BE70               ; renderer char path; was: CMP #$00CE / BEQ $BE4F
    JML vwf_dispatch
    NOP

org $00BF01               ; newline; was: LDA $09FE / (CMP #$003E)
    JML vwf_newline

org $00BF94               ; cursor set {pXX:YY}, row part (both the column and the row-only path reach it;
    JML vwf_setcol        ; $BF8C BEQ targets $BF94); was: LDA [$14] / AND #$00FF
    NOP

org $01ECE5               ; window clear; was: REP #$20 / LDA #$2000
    JML vwf_clear
    NOP

org $00C20E               ; tilemap upload request; was: PHP / SEP #$20 / INC $57
    JML vwf_c20e
    NOP

org $01ECCC               ; bank-01 copy of it (menus: hospital, shop, items; every frame); same bytes
    JML vwf_eccc
    NOP

org $C08000
vwf_glyphs:   skip $600   ; filled by lm.py build: 95 x 16 bytes, chars $20-$7E
vwf_widths:   skip $60    ; filled by lm.py build: 95 bytes
assert vwf_widths == $C08600, "vwf_widths must match lmtools/build.py VWF_WIDTHS"

; ---------------------------------------------------------------- per-message start
vwf_start:
    STZ $0A10 : STZ $0A06                       ; replayed
    PHP : REP #$30 : PHX : PHY
    JSR vwf_layout
    LDA #$0000 : STA.l !novwf
    LDA $0A1C : BNE .fixed                       ; menu mode: slot buffer is not ours
    LDA.l !nlines : CMP #$0000 : BEQ .fixed
    LDA $09F6 : LSR : CMP.l !nlines : BCC .ok : BEQ .ok   ; visible lines <= slots?
.fixed:
    LDA #$0001 : STA.l !novwf
    BRA .done
.ok:
    LDA #$0001 : STA.l !needslot
    LDA #$0000 : STA.l !px : STA.l !partial
.done:
    PLY : PLX : PLP
    JML $00BE49

vwf_layout:               ; !base = 2*($0A1A + $0A18): labels + this message's kanji/UI glyphs (the game copies them
                          ; there); !width = 27, !nlines = (128 - base) / 27 (0 if base >= 128)
    LDA $0A1A : CLC : ADC $0A18 : ASL : STA.l !base
    LDA #$001B : STA.l !width
    LDA #$0000 : STA.l !nlines
    LDA #$0080 : SEC : SBC.l !base : STA.l !v                      ; (!v: scratch)
-   LDA.l !v : SEC : SBC.l !width : BMI +
    STA.l !v
    LDA.l !nlines : INC : STA.l !nlines
    BRA -
+   RTS

vwf_advance_line:         ; px = 0, line = (line + 1) mod nlines, slot0 = 128 - (line+1)*width, clear it (16-bit A/X/Y)
    LDA #$0000 : STA.l !px : STA.l !partial
    LDA.l !nlines : BEQ .out
    LDA.l !line : INC : CMP.l !nlines : BCC + : LDA #$0000
+   STA.l !line
    INC : STA.l !row
    LDA #$0080 : STA.l !slot0
-   LDA.l !slot0 : SEC : SBC.l !width : STA.l !slot0
    LDA.l !row : DEC : STA.l !row : BNE -
    LDA $09FC : STA.l !col0
    JSR vwf_clearslot
.out:
    RTS

vwf_clearslot:            ; blank the !width tiles of the current slot
    LDA.l !slot0 : ASL : ASL : ASL : ASL : TAX                    ; * 16 bytes
    LDA.l !width : ASL : ASL : ASL : TAY                          ; words
    LDA $6F                                      ; blank tile = paper (inversion mask)
-   STA.l !slots,x : INX : INX : DEY : BNE -
    RTS

; ---------------------------------------------------------------- char path
vwf_dispatch:             ; renderer: A = char (16-bit), X = tilemap offset (16-bit)
    CMP #$00CE : BNE + : JML $00BE4F            ; replayed: no-op char
+   PHA
    LDA $0A1C : BNE .fixed
    LDA.l !novwf : BNE .fixed
    LDA $09FE : CMP $09F2 : BCC .fixed           ; cursor above the window (panel values): no slot
    LDA 1,s : CMP #$0020 : BCC .fixed : CMP #$007F : BCS .fixed
    LDA.l !needslot : BNE +                      ; (a fresh line starts at cell 0)
    LDA $09FC : SEC : SBC.l !col0 : SEC : SBC.l !partial
    CMP.l !width : BCS .fixed                    ; past the slot's last cell (line over 216 px): fixed font
+   PLA
    JSR vwf_draw
    DEX : DEX : DEC $09FC                       ; native $BE88 adds one cell back
    JML $00BE78
.fixed:
    LDA #$0000 : STA.l !partial : STA.l !px      ; a fixed char takes the (fresh) cursor cell
    LDA $0A1E : BEQ .text                       ; {cF1} palette set: UI graphics drawn with font tiles, keep the code
    PLA
    JML $00BE75                                 ; original: JSR $C156 (tile = char code)
.text:                    ; tiles $5F-$7A are icons/gauges in other palettes: draw '_' as space, a-z with the A-Z tiles
    PLA
    CMP #$005F : BNE + : LDA #$0020 : JML $00BE75
+   CMP #$0061 : BCC + : CMP #$007B : BCS + : SBC #$001F   ; carry clear here: subtracts $20
+   JML $00BE75

vwf_draw:                 ; A = char; draws glyph at (!line, $09FC, !px); advances X/$09FC/!px
    PHA
    LDA.l !needslot : BEQ +
    LDA #$0000 : STA.l !needslot
    PHX : PHY : JSR vwf_advance_line : PLY : PLX
+   LDA.l !partial : BEQ +                       ; step back into the partly filled cell
    DEX : DEX : DEC $09FC
    LDA #$0000 : STA.l !partial
+   PLA
    SEC : SBC #$0020 : STA.l !gptr               ; glyph index
    PHX
    TAX
    SEP #$20 : LDA.l vwf_widths,x : REP #$20 : AND #$00FF : STA.l !wid
    LDA.l !gptr : ASL : ASL : ASL : ASL : CLC : ADC #vwf_glyphs&$FFFF : STA.l !gptr
    LDA $09FC : SEC : SBC.l !col0 : STA.l !col                    ; cell in the slot
    CLC : ADC.l !slot0 : STA.l !toff                               ; tile index of this cell
    CLC : ADC #$0180 : STA.l !tile
    LDA.l !toff : ASL : ASL : ASL : ASL : STA.l !toff           ; byte offset
    LDA #$0000 : STA.l !row
.row:
    LDA.l !gptr : CLC : ADC.l !row : TAX
    SEP #$20 : LDA.l $C00000,x : REP #$20        ; glyph row byte (bank $C0)
    AND #$00FF : XBA : STA.l !v                  ; << 8
    LDA.l !px : TAX
-   CPX #$0000 : BEQ +
    LDA.l !v : LSR : STA.l !v : DEX : BRA -
+   LDA.l !row : CMP #$0008 : BCC +
    SEC : SBC #$0008 : ASL : INC : BRA ++        ; bottom half -> byte 2(r-8)+1
+   ASL                                          ; top half    -> byte 2r
++  CLC : ADC.l !toff : TAX
    SEP #$20                                     ; tiles are stored EOR $6F (game font is inverted)
    LDA.l !slots,x : EOR $6F : ORA.l !v+1 : EOR $6F : STA.l !slots,x       ; this cell
    LDA.l !col : INC : CMP.l !width : BEQ +                                 ; no next cell after the slot's last
    LDA.l !slots+16,x : EOR $6F : ORA.l !v : EOR $6F : STA.l !slots+16,x   ; spill into the next cell
+   REP #$20
    LDA.l !row : INC : STA.l !row : CMP #$0010 : BCS + : JMP .row
+
    PLX
    LDA.l !tile : CLC : ADC $0A02 : STA.l $7E9000,x : CLC : ADC #$0400 : STA.l $7E9040,x
    LDA.l !px : CLC : ADC.l !wid : STA.l !px
.adv:
    LDA.l !px : CMP #$0008 : BCC .upload
    SEC : SBC #$0008 : STA.l !px
    INX : INX : INC $09FC
    LDA.l !tile : INC : STA.l !tile
    LDA.l !px : BEQ .adv                         ; nothing spilled: leave the next cell (window border) alone
    LDA.l !col : INC : CMP.l !width : BEQ .adv   ; the slot's last cell has no next cell
    LDA.l !tile : CLC : ADC $0A02 : STA.l $7E9000,x : CLC : ADC #$0400 : STA.l $7E9040,x
    BRA .adv
.upload:
    LDA.l !px : BEQ +                            ; partly filled cell: park the cursor on the next one so
    INX : INX : INC $09FC                        ; fixed-font output (prompt arrow, numbers) gets a fresh cell
    LDA #$0001 : STA.l !partial
+   LDA #$0001 : STA.l !dirty                   ; uploaded by vwf_c20e before the next tilemap upload
    RTS

vwf_c20e:                 ; game asks for a tilemap upload: send dirty VWF tiles first ($57 = one command per frame)
    JSR vwf_flush
    PHP                                          ; replayed: PHP / SEP #$20 / INC $57
    SEP #$20
    INC $57
    JML $00C213

vwf_eccc:
    JSR vwf_flush
    PHP                                          ; replayed: PHP / SEP #$20 / INC $57
    SEP #$20
    INC $57
    JML $01ECD1

vwf_flush:                ; if !slots changed: NMI upload !slots -> VRAM $6C00 ($57 = $FE), wait one frame
    PHP
    REP #$20
    PHA
    LDA.l !dirty : BEQ +
    LDA #$0000 : STA.l !dirty
    LDA #$6C00 : STA $78
    SEP #$20 : LDA #$FE : STA $57 : REP #$20
    JSL $00E3BE
+   PLA
    PLP
    RTS

; ---------------------------------------------------------------- newline / cursor / clear
vwf_newline:
    PHP : REP #$30 : PHX : PHY
    LDA.l !novwf : BNE +                         ; fixed-font message: leave the slot buffer alone
    LDA #$0001 : STA.l !needslot                 ; the next glyph takes a fresh slot
    LDA #$0000 : STA.l !px : STA.l !partial
+   PLY : PLX : PLP
    LDA $09FE : CMP #$003E                       ; replayed (the JML covers $BF01-$BF04)
    JML $00BF07

vwf_setcol:
    LDA [$14] : AND #$00FF                       ; replayed
    PHA
    LDA #$0001 : STA.l !novwf                    ; positioned layout: fixed font from here on
    PLA
    JML $00BF99

vwf_clear:
    PHP : REP #$30 : PHX
    JSR vwf_layout
    LDA #$0000 : STA.l !px : STA.l !partial
    LDA #$FFFF : STA.l !line                     ; the first glyph after a clear takes slot 0 (the top one)
    LDA #$0001 : STA.l !needslot
    LDA $0A1C : BNE +                            ; menu mode: !slots is not ours
    LDA.l !base : ASL : ASL : ASL : ASL : TAX    ; clear from the first VWF tile to the end
    LDA $6F                                      ; blank tile = paper (inversion mask)
-   CPX #$0800 : BCS +
    STA.l !slots,x : INX : INX : BRA -
+   PLX : PLP
    REP #$20                                     ; replayed
    LDA #$2000
    JML $01ECEA


; ---------------------------------------------------------------- unit name print cap
; $00:B90F / $B925 print a first name / surname from the 8-byte records at $02:A050 / $02:A298 until a space. JP names
; are space-padded; an 8-letter EN name fills its record and would run into the next one, so stop after 8 bytes.
!namelen = $7FFF24

org $00B939               ; was: SEP #$20 / LDA [$00],y (copy loop head; [$00] = table, Y = index*8, X = buffer)
    JML name_copy

org $C0A000
name_copy:
    SEP #$20
    LDA #$08 : STA.l !namelen
-   LDA [$00],y : INY : CMP #$20 : BEQ +
    STA $0400,x : INX
    LDA.l !namelen : DEC : STA.l !namelen : BNE -
+   JML $00B948               ; PLY / RTS

assert pc() <= $C0E000, "bank $C0 code/data must stay below $C0E000 (graphics chunks, data/graphics.json)"
