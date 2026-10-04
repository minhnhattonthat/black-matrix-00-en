; Memory-card save title in English (SYSTEM.DAT sub-file 10, the save/load overlay at 0x800D4000).
; The original routine builds the 32-character title one kana/kanji at a time from a 36-glyph table;
; this replaces its body with a template plus fullwidth English words (titles stay 2-byte Shift-JIS).
;   "ＢＭ００　Ｃｈ２　００１：３１　＜　５＞　Ｆｒｅｅ　Ｔｉｍｅ　１"
; Entry state kept from the original prologue: s1 = title buffer (64 bytes, zeroed), s0-s4 and ra saved.
; Assembled by build.patch_system(); paths are relative to the repo root.

.psx
.open "work/sub10.bin", "work/sub10.out", 0x800D4000

GET   equ 0x80023E60           ; a0 = save variable number -> v0
EXIT  equ 0x800DD02C           ; the original epilogue

.org 0x800DCA88
.area 0x800DD02C-0x800DCA88
    la    a1, st_template
    jal   st_copy
    move  a0, s1

    ; ---- chapter: 0 = cleared, 10 = final, else "Ch" + digit (characters 5-7)
    jal   GET
    li    a0, 0x56
    sll   v0, v0, 16
    sra   s4, v0, 16
    la    a1, st_clear
    beqz  s4, @@chapter
    li    v0, 10
    la    a1, st_final
    beq   s4, v0, @@chapter
    nop
    la    a1, st_chapter
@@chapter:
    jal   st_copy
    addiu a0, s1, 10
    blez  s4, @@time
    slti  v0, s4, 10
    beqz  v0, @@time
    addiu v0, s4, 0x4F         ; fullwidth digit: 0x82, 0x4F + n
    sb    v0, 15(s1)

    ; ---- play time hhh:mm (characters 9-11, 13-14)
@@time:
    jal   GET
    li    a0, 0x58
    sll   v0, v0, 16
    sra   s0, v0, 16           ; hours
    jal   GET
    li    a0, 0x59
    sll   v0, v0, 16
    sra   s2, v0, 16           ; minutes
    li    t0, 100
    divu  s0, t0
    mflo  v0
    mfhi  s0
    sltiu v1, v0, 10
    bnez  v1, @@hundreds
    nop
    li    v0, 9
@@hundreds:
    addiu v0, v0, 0x4F
    sb    v0, 19(s1)
    li    t0, 10
    divu  s0, t0
    mflo  v0
    mfhi  v1
    addiu v0, v0, 0x4F
    sb    v0, 21(s1)
    addiu v1, v1, 0x4F
    sb    v1, 23(s1)
    divu  s2, t0
    mflo  v0
    mfhi  v1
    addiu v0, v0, 0x4F
    sb    v0, 27(s1)
    addiu v1, v1, 0x4F
    sb    v1, 29(s1)

    ; ---- save slot 1-15, right-aligned (characters 17-18)
    lui   v1, 0x800E
    lbu   v0, 0x0CF5(v1)
    li    t0, 10
    addiu v0, v0, 1
    divu  v0, t0
    mflo  v0
    mfhi  v1
    addiu v1, v1, 0x4F
    beqz  v0, @@mode
    sb    v1, 37(s1)
    li    v1, 0x82
    sb    v1, 34(s1)
    addiu v0, v0, 0x4F
    sb    v0, 35(s1)

    ; ---- what the save is: scenario / battle n / free time n (characters 21-31)
@@mode:
    jal   GET
    li    a0, 0x5D
    sll   v0, v0, 16
    sra   s0, v0, 16           ; 0 scenario, 1 battle, 2 free time
    jal   GET
    li    a0, 0x5E
    sll   v0, v0, 16
    sra   s3, v0, 16           ; its number
    bnez  s0, @@not_scenario
    li    s2, -1               ; s2 = digit to append, none
    la    a1, st_scenario
    bnez  s4, @@put
    nop
    la    a1, st_ending
    b     @@put
    nop
@@not_scenario:
    li    v0, 2
    beq   s0, v0, @@free
    li    v0, 1
    bne   s0, v0, @@done
    li    v0, 10
    la    a1, st_battle
    bne   s4, v0, @@put
    move  s2, s3
    ; final chapter: 1-2 = battle 1, 3 = battle 2, 4 = the last battle
    blez  s3, @@done
    slti  v0, s3, 3
    bnez  v0, @@put
    li    s2, 1
    li    v0, 3
    beq   s3, v0, @@put
    li    s2, 2
    li    v0, 4
    bne   s3, v0, @@done
    li    s2, -1
    la    a1, st_last
    b     @@put
    nop
@@free:
    la    a1, st_free
    move  s2, s3
@@put:
    jal   st_copy
    addiu a0, s1, 42
    bltz  s2, @@done
    li    v0, 0x82
    sb    v0, 0(a0)
    addiu v0, s2, 0x4F
    sb    v0, 1(a0)
@@done:
    j     EXIT
    nop

; copy the zero-terminated bytes at a1 to a0; a0 ends just past the copy
st_copy:
    lbu   t0, 0(a1)
    addiu a1, a1, 1
    beqz  t0, @@end
    nop
    sb    t0, 0(a0)
    b     st_copy
    addiu a0, a0, 1
@@end:
    jr    ra
    nop

st_template:  ; "BM00 ??? 000:00 < 0>            "
    .db 0x82,0x61,0x82,0x6C,0x82,0x4F,0x82,0x4F,0x81,0x40,0x81,0x48,0x81,0x48,0x81,0x48
    .db 0x81,0x40,0x82,0x4F,0x82,0x4F,0x82,0x4F,0x81,0x46,0x82,0x4F,0x82,0x4F,0x81,0x40
    .db 0x81,0x83,0x81,0x40,0x82,0x4F,0x81,0x84,0x81,0x40,0x81,0x40,0x81,0x40,0x81,0x40
    .db 0x81,0x40,0x81,0x40,0x81,0x40,0x81,0x40,0x81,0x40,0x81,0x40,0x81,0x40,0x81,0x40
    .db 0
st_clear:  ; "Clr"
    .db 0x82,0x62,0x82,0x8C,0x82,0x92
    .db 0
st_final:  ; "Fin"
    .db 0x82,0x65,0x82,0x89,0x82,0x8E
    .db 0
st_chapter:  ; "Ch0"
    .db 0x82,0x62,0x82,0x88,0x82,0x4F
    .db 0
st_scenario:  ; "Scenario"
    .db 0x82,0x72,0x82,0x83,0x82,0x85,0x82,0x8E,0x82,0x81,0x82,0x92,0x82,0x89,0x82,0x8F
    .db 0
st_ending:  ; "Ending"
    .db 0x82,0x64,0x82,0x8E,0x82,0x84,0x82,0x89,0x82,0x8E,0x82,0x87
    .db 0
st_battle:  ; "Battle "
    .db 0x82,0x61,0x82,0x81,0x82,0x94,0x82,0x94,0x82,0x8C,0x82,0x85,0x81,0x40
    .db 0
st_last:  ; "Last Battle"
    .db 0x82,0x6B,0x82,0x81,0x82,0x93,0x82,0x94,0x81,0x40,0x82,0x61,0x82,0x81,0x82,0x94
    .db 0x82,0x94,0x82,0x8C,0x82,0x85
    .db 0
st_free:  ; "Free Time "
    .db 0x82,0x65,0x82,0x92,0x82,0x85,0x82,0x85,0x81,0x40,0x82,0x73,0x82,0x89,0x82,0x8D
    .db 0x82,0x85,0x81,0x40
    .db 0
    .align 4
.endarea

.close
