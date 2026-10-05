; VWF for the message renderer. Design + RE: docs/re/text-engine.md "Dynamic tiles and VWF hooks".
;
; Each text line gets a "line slot" of 32 cells; cell (slot L, column c) is dynamic tile
;   $180 + base + L*32 + c      (base = 2*$0A1A: tiles below are window labels, never touched)
; Glyphs are ORed into those 2bpp tiles (plane 0 = top 8 rows, plane 1 = bottom 8 rows) and the
; whole slot buffer is uploaded by the NMI ($57 = $FE, then wait one frame). Tiles are stored EOR $6F
; (the game's font is inverted: $6F = $FFFF in every window seen).
; Fixed font (original renderer) is used when: menu mode ($0A1C), kanji in the message ($0A18),
; too few line slots for the window, a cursor-set code appeared in the message, or char not $20-$7E.
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
!slots  = $7FB000         ; 128 x 16-byte tiles -> VRAM $6C00 (BG tiles $180-$1FF)

org $00BE43               ; renderer message start; was: STZ $0A10 / STZ $0A06
    JML vwf_start
    NOP : NOP

org $00BE70               ; renderer char path; was: CMP #$00CE / BEQ $BE4F
    JML vwf_dispatch
    NOP

org $00BF01               ; newline; was: LDA $09FE / (CMP #$003E)
    JML vwf_newline

org $00BF91               ; cursor set {pXX:YY}; was: STA $09FC / LDA [$14]
    JML vwf_setcol
    NOP

org $01ECE5               ; window clear; was: REP #$20 / LDA #$2000
    JML vwf_clear
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
    LDA.l !nlines : CMP #$0000 : BEQ .fixed
    LDA $09F6 : LSR : CMP.l !nlines : BCC .ok : BEQ .ok   ; visible lines <= slots?
.fixed:
    LDA #$0001 : STA.l !novwf
    BRA .done
.ok:
    JSR vwf_advance_line
.done:
    PLY : PLX : PLP
    JML $00BE49

vwf_layout:               ; !base = 2*$0A1A, !nlines = (128 - base) / 32 (0 if base >= 128)
    LDA $0A1A : ASL : STA.l !base
    CMP #$0080 : BCC +
    LDA #$0000 : STA.l !nlines : RTS
+   EOR #$FFFF : INC : CLC : ADC #$0080          ; 128 - base
    LSR : LSR : LSR : LSR : LSR : STA.l !nlines
    RTS

vwf_advance_line:         ; px = 0, line = (line + 1) mod nlines, clear that slot (16-bit A/X/Y)
    LDA #$0000 : STA.l !px : STA.l !partial
    LDA.l !nlines : BEQ .out
    LDA.l !line : INC : CMP.l !nlines : BCC + : LDA #$0000
+   STA.l !line
    JSR vwf_clearslot
.out:
    RTS

vwf_clearslot:            ; zero the 32 tiles (512 bytes) of slot !line
    LDA.l !line : ASL : ASL : ASL : ASL : ASL : CLC : ADC.l !base   ; tile index of cell 0
    ASL : ASL : ASL : ASL : TAX                                       ; * 16 bytes
    LDY #$0100
    LDA $6F                                      ; blank tile = paper (inversion mask)
-   STA.l !slots,x : INX : INX : DEY : BNE -
    RTS

; ---------------------------------------------------------------- char path
vwf_dispatch:             ; renderer: A = char (16-bit), X = tilemap offset (16-bit)
    CMP #$00CE : BNE + : JML $00BE4F            ; replayed: no-op char
+   PHA
    LDA $0A1C : ORA $0A18 : BNE .fixed
    LDA.l !novwf : BNE .fixed
    LDA 1,s : CMP #$0020 : BCC .fixed : CMP #$007F : BCS .fixed
    PLA
    JSR vwf_draw
    DEX : DEX : DEC $09FC                       ; native $BE88 adds one cell back
    JML $00BE78
.fixed:
    PLA
    JML $00BE75                                 ; original: JSR $C156 (tile = char code)

vwf_draw:                 ; A = char; draws glyph at (!line, $09FC, !px); advances X/$09FC/!px
    PHA
    LDA.l !partial : BEQ +                       ; step back into the partly filled cell
    DEX : DEX : DEC $09FC
    LDA #$0000 : STA.l !partial
+   PLA
    SEC : SBC #$0020 : STA.l !gptr               ; glyph index
    PHX
    TAX
    SEP #$20 : LDA.l vwf_widths,x : REP #$20 : AND #$00FF : STA.l !wid
    LDA.l !gptr : ASL : ASL : ASL : ASL : CLC : ADC #vwf_glyphs&$FFFF : STA.l !gptr
    LDA.l !line : ASL : ASL : ASL : ASL : ASL : CLC : ADC.l !base : STA.l !toff
    LDA $09FC : AND #$001F : CLC : ADC.l !toff : STA.l !toff    ; tile index of this cell
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
    LDA.l !slots+16,x : EOR $6F : ORA.l !v : EOR $6F : STA.l !slots+16,x   ; spill into the next cell
    REP #$20
    LDA.l !row : INC : STA.l !row : CMP #$0010 : BCC .row
    PLX
    LDA.l !tile : CLC : ADC $0A02 : STA.l $7E9000,x : CLC : ADC #$0400 : STA.l $7E9040,x
    LDA.l !px : CLC : ADC.l !wid : STA.l !px
.adv:
    LDA.l !px : CMP #$0008 : BCC .upload
    SEC : SBC #$0008 : STA.l !px
    INX : INX : INC $09FC
    LDA.l !tile : INC : STA.l !tile
    CLC : ADC $0A02 : STA.l $7E9000,x : CLC : ADC #$0400 : STA.l $7E9040,x
    BRA .adv
.upload:
    LDA.l !px : BEQ +                            ; partly filled cell: park the cursor on the next one so
    INX : INX : INC $09FC                        ; fixed-font output (prompt arrow, numbers) gets a fresh cell
    LDA #$0001 : STA.l !partial
+   LDA #$6C00 : STA $78                         ; NMI: !slots -> VRAM $6C00
    SEP #$20 : LDA #$FE : STA $57 : REP #$20
    JSL $00E3BE                                  ; wait for it ($57 is one command per frame)
    RTS

; ---------------------------------------------------------------- newline / cursor / clear
vwf_newline:
    PHP : REP #$30 : PHX : PHY
    JSR vwf_advance_line
    PLY : PLX : PLP
    LDA $09FE                                    ; replayed
    JML $00BF04

vwf_setcol:
    STA $09FC                                    ; replayed
    PHA
    LDA #$0001 : STA.l !novwf                    ; positioned layout: fixed font from here on
    PLA
    LDA [$14]                                    ; replayed
    JML $00BF96

vwf_clear:
    PHP : REP #$30 : PHX
    JSR vwf_layout
    LDA #$0000 : STA.l !px : STA.l !line : STA.l !partial
    LDA $0A18 : BNE +                            ; kanji tiles of this message live in !slots
    LDA.l !base : ASL : ASL : ASL : ASL : TAX    ; clear from the first VWF tile to the end
    LDA $6F                                      ; blank tile = paper (inversion mask)
-   CPX #$0800 : BCS +
    STA.l !slots,x : INX : INX : BRA -
+   PLX : PLP
    REP #$20                                     ; replayed
    LDA #$2000
    JML $01ECEA
