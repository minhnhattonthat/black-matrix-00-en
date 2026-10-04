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

; ---- unit names in English ---------------------------------------------------
; A unit's name is copied into its record when the game starts and is then kept in the save, so saves
; made before the translation carry Japanese names (and "Johannes" does not fit its 8-byte default slot).
; v0 = unit record: if its name is one of the Japanese defaults, write the English one. Keeps v0.
.align 4
name_fix_one:
    lbu   t0, 0(v0)
    la    t2, name_table
    sltiu t1, t0, 0x80
    bne   t1, zero, @@ret      ; empty or already English
    lw    t4, 0(v0)
@@next:
    lw    t3, 0(t2)
    nop
    beq   t3, zero, @@ret      ; end of table: a name we do not know
    nop
    bne   t3, t4, @@next
    addiu t2, t2, 16
    lw    t3, -12(t2)
    lw    t0, -8(t2)
    lw    t1, -4(t2)
    sw    t3, 0(v0)
    sw    t0, 4(v0)
    sw    t1, 8(v0)
@@ret:
    jr    ra
    nop

; replaces the memcpy that loads the 16 unit records from a save
name_fix_load:
    addiu sp, sp, -8
    sw    ra, 0(sp)
    jal   0x80041438
    nop
    lui   v0, 0x8007
    addiu v0, v0, -0xBA8       ; 0x8006F458, the first record
    li    t6, 16
@@unit:
    jal   name_fix_one
    addiu t6, t6, -1
    bne   t6, zero, @@unit
    addiu v0, v0, 124
    lw    ra, 0(sp)
    nop
    jr    ra
    addiu sp, sp, 8

; first two characters of the Japanese name (Shift-JIS), then the English name padded to 12 bytes
name_table:
    .db 0x83,0x4A,0x83,0x43, 0x43,0x61,0x69,0x6E,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00   ; Cain
    .db 0x83,0x88,0x83,0x6E, 0x4A,0x6F,0x68,0x61,0x6E,0x6E,0x65,0x73,0x00,0x00,0x00,0x00   ; Johannes
    .db 0x83,0x47,0x83,0x4E, 0x45,0x78,0x61,0x6C,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00   ; Exal
    .db 0x83,0x8B,0x83,0x4A, 0x4C,0x75,0x63,0x61,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00   ; Luca
    .db 0x83,0x55,0x83,0x43, 0x5A,0x69,0x6F,0x6E,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00   ; Zion
    .db 0x83,0x56,0x83,0x8A, 0x53,0x79,0x72,0x69,0x61,0x20,0x00,0x00,0x00,0x00,0x00,0x00   ; Syria
    .db 0x83,0x58,0x83,0x65, 0x53,0x74,0x61,0x79,0x65,0x6E,0x00,0x00,0x00,0x00,0x00,0x00   ; Stayen
    .db 0x83,0x8A,0x83,0x8A, 0x4C,0x69,0x6C,0x69,0x73,0x20,0x00,0x00,0x00,0x00,0x00,0x00   ; Lilis
    .db 0x83,0x4C,0x83,0x8D, 0x4B,0x69,0x6C,0x6F,0x74,0x61,0x00,0x00,0x00,0x00,0x00,0x00   ; Kilota
    .db 0x83,0x94,0x83,0x40, 0x56,0x61,0x6C,0x74,0x6F,0x73,0x73,0x20,0x00,0x00,0x00,0x00   ; Valtoss
    .db 0x83,0x78,0x83,0x43, 0x42,0x61,0x6C,0x65,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00   ; Bale
    .db 0x83,0x4E,0x83,0x8C, 0x4B,0x72,0x65,0x69,0x73,0x20,0x00,0x00,0x00,0x00,0x00,0x00   ; Kreis
    .db 0x83,0x8A,0x83,0x76, 0x52,0x68,0x69,0x70,0x73,0x61,0x6C,0x69,0x73,0x20,0x00,0x00   ; Rhipsalis
    .dw 0
.endarea

; set-name (new game): original `jr ra` / `sb a3, 0x11(v0)`
.org 0x8003CDA0
    j     name_fix_one
    sb    a3, 0x11(v0)

; load game: original `jal 0x80041438` (memcpy into the unit records)
.org 0x80039CC4
    jal   name_fix_load

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
