; Halfwidth text for Black/Matrix 00 (SLPS-03573).
; A 2-byte text unit whose first byte is < 0x80 is two ASCII letters drawn
; as 6x12 glyphs into one 12x12 cell. See docs/superpowers/specs/2026-10-02-halfwidth-font-design.md
; Assembled by halfwidth.assemble(); paths are relative to the repo root.

.psx
.open "work/orig/SLPS_035.73", "work/halfwidth.exe", 0x8000F800

; ---- hook 1: glyph cache miss, before the SJIS index lookup ----------------
; original:  lbu v0,0(a1) / lhu v1,0xe(a2)
.org 0x800344FC
    j     hw_lookup
    lbu   v0, 0(a1)            ; delay slot: first displaced instruction

; ---- hook 2: bitmap pointer s1 is set, expansion about to start ------------
; original:  sltu t5,zero,s4 / addiu a2,zero,3
.org 0x80034638
    j     hw_glyph
    sltu  t5, zero, s4         ; delay slot: first displaced instruction

; ---- text objects: never spread glyphs across the field width ---------------
; Japanese menus justified 2-cell labels into 4-cell slots; with halfwidth
; English that only tears words apart ("Sa  ve"). original: andi v1, v1, 0x80
.org 0x80013598
    andi  v1, v1, 0
.org 0x80013800                ; same test in the layout branch used by menus (flags without 0xe00)
    andi  v1, v1, 0

; ---- font, glyphs 0x20-0x5F ------------------------------------------------
.org 0x800604A0
.area 0x80060848 - 0x800604A0
hw_font_lo:
    .incbin "asm/font6x12.bin", 0, 768
.endarea

; ---- font, glyphs 0x60-0x7E, and the scratch cell ---------------------------
.org 0x8006292C
.area 0x80062C4C - 0x8006292C
hw_font_hi:
    .incbin "asm/font6x12.bin", 768, 372
.align 4
hw_cell:
    .fill 24
.endarea

; ---- code ------------------------------------------------------------------
.org 0x8006087C
.area 0x80060A8C - 0x8006087C

hw_lookup:
    lhu   v1, 0xE(a2)          ; second displaced instruction; also fills the load
    sltiu t8, v0, 0x80         ;   delay of the lbu in the hook's delay slot
    bne   t8, zero, @@ascii
    nop
    j     0x80034504
    nop
@@ascii:
    mflo  a0                   ; the original does this at 0x80034508
    addu  s6, v1, a0           ;   and this at 0x80034510
    j     0x80034600           ; "index found" path
    li    a0, 0                ; index - 1; the pointer it yields is replaced in hw_glyph

; a0 = character -> v0 = address of its 12 glyph bytes. Clobbers a0, t8, t9.
hw_glyph_ptr:
    addiu a0, a0, -0x20
    sltiu t9, a0, 0x5F
    beq   t9, zero, @@space    ; outside 0x20-0x7E
    sltiu t9, a0, 0x40
    sll   t8, a0, 1
    addu  t8, t8, a0
    beq   t9, zero, @@high
    sll   t8, t8, 2            ; delay slot: t8 = index * 12
    la    v0, hw_font_lo
    jr    ra
    addu  v0, v0, t8
@@high:
    la    v0, hw_font_hi - 0x40 * 12
    jr    ra
    addu  v0, v0, t8
@@space:
    la    v0, hw_font_lo
    jr    ra
    nop

; s7 = 16-bit character code. ra was saved by the function prologue and is
; reloaded before its return, so calling from here is safe.
hw_glyph:
    andi  t8, s7, 0x8000
    bne   t8, zero, @@done     ; Shift-JIS: keep the game's glyph
    nop
    jal   hw_glyph_ptr
    srl   a0, s7, 8            ; delay slot: left character
    move  a3, v0
    jal   hw_glyph_ptr
    andi  a0, s7, 0xFF         ; delay slot: right character
    la    s1, hw_cell
    move  t0, s1
    li    t1, 12
@@row:
    lbu   t2, 0(a3)            ; left:  pixels in bits 7..2
    lbu   t3, 0(v0)            ; right: pixels in bits 7..2
    addiu a3, a3, 1
    addiu v0, v0, 1
    srl   t4, t3, 6
    or    t2, t2, t4
    sb    t2, 0(t0)            ; columns 0-7
    sll   t3, t3, 2
    sb    t3, 1(t0)            ; columns 8-11
    addiu t1, t1, -1
    bne   t1, zero, @@row
    addiu t0, t0, 2
@@done:
    j     0x80034640
    addiu a2, zero, 3          ; delay slot: second displaced instruction

.endarea
.close
