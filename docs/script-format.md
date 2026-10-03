# SCENARIO script format

Read off the interpreter in `SLPS_035.73` (loaded at `0x80010000`, file offset = address − `0x80010000` + `0x800`) and two overlays in `SYSTEM.DAT`.

## Interpreter

- Dispatcher at `0x800246c0`: fetch a u16 op; `op >> 12` picks a handler table, `op & 0xfff` indexes it.
- Tables are registered with `0x80023c80(class, table)`:

| Class | Table | Where |
|---|---|---|
| 0 (control flow) | `0x8005f12c` | EXE |
| 1 (text, menus, system) | `0x8005f1ac` | EXE |
| 2 | `0x80199148` | `SYSTEM.DAT` sub-file 5, loaded at `0x80190000` |
| 3 | `0x801800a8` | `SYSTEM.DAT` sub-file 4, loaded at `0x80140000` |

- The program counter is a u16 **word** index, so a script cannot exceed `0x20000` bytes.
- Fetch helpers that handlers call:

| Address | Sig | Reads |
|---|---|---|
| `0x8002423c` | `w` | one u16 |
| `0x800242c0` | `www` | three u16 |
| `0x80024270` | `L` / imm32 | skips one word if the address is not 4-byte aligned, then a u32 |
| `0x80024300` + `w` loop | `S` | string: words until a zero u16 |
| `0x8002431c` | `E` | expression |

## Operands

- **`L`**: every u32 operand of an opcode is an absolute byte offset into the script. Handlers shift it right by one and store it as the program counter (or pass it on as a script address). It is preceded by a `00 00` pad word when it would otherwise sit on an odd word. The pad therefore appears or disappears when earlier data changes length by 2 mod 4.
- **`S`**: Shift-JIS bytes ending at the first zero **u16**. The test is word-wise, so an odd-length string needs one `00` to complete its last word and then the `00 00` terminator.
- **`E`**: reverse-Polish expression, a list of u16 items:

| Item | Extra | Meaning |
|---|---|---|
| `0` | — | end, pop result |
| `1` | u16 | push immediate |
| `2` | u16 | push 32-bit variable |
| `3` | u16 | push 16-bit variable |
| `4` | aligned u32 | push immediate (a plain number, not a jump) |
| `0x80`, `0x81` | — | unary operators |
| `0x82`–`0x91` | — | binary operators |
| anything else | — | ignored |

## Opcodes

The full signature table is `OPS` in `script.py`. Signatures were collected by listing, for each handler, its calls to the fetch helpers in address order. No code outside the handlers and the dispatcher calls those helpers.

Opcodes that matter for translation:

| Op | Sig | Role |
|---|---|---|
| `0001` | `wwE` | assign variable |
| `0002` | `LE` | jump if expression is zero |
| `0003` | `L` | goto |
| `000a` | `L` | call |
| `000c` | `wwwL` | start a parallel script at `L` |
| `1050` | `S` | dialogue line |
| `105b` | `SL` | string plus jump target |
| `1061`, `1062` | `L` | register a script address |
| `1073` | `ES` | string with a leading argument |
| `1081` | `SL` | menu choice: label and target |
| `1082` | `L` | menu default/cancel target |
| `108a` | `SLLE` | string with two targets |
| `108f` | `S` | string |

## Checks

`test_script.py` holds on all 382 non-empty `SCENARIO.DAT` sub-files: the token stream reproduces the used bytes exactly, every jump lands on a token start, and no kana run lies outside a string token.

A signature could still be wrong for a handler that reads operands on only some branches. The linear listing would overcount; such an error would normally derail tokenization, and none did.

## TOWN.DAT

43 sub-files. Each is a tree of containers:

    u16 count, u16 1, u32 2, then count x (u32 offset, u32 size) in 4-byte words

Offsets are relative to the container, entries are contiguous and start right
after the table; anything that does not parse as a container is a leaf
(`town.parse` / `town.rebuild`). Town-state files 4..30 and sub 40 carry two
text leaves, identical in every copy:

| leaf | role | entries | bytes per line |
|------|------|---------|----------------|
| A, 68 entries | Notebook articles | 846 lines | 32 (16 cells) |
| B, 48 entries | prompts, Save/Load/Config, coach tips, shop names | 147 lines | 28 (14 cells) |

Text leaf: u16 offset table (count = first offset / 2), then per entry

    (0001 [u16 param] <Shift-JIS, even length> 0000)* [0000]

The closing `0000` is absent on the 16-name shop list and present on some
empty articles, so it is kept as a flag. Params (0x07/0x0b/0x0c) occur only on
the three yes/no prompts. Leaves are padded to a word; a leaf must stay under
64 KB. English grows each town file by about 2.5 KB; parents are relaid out.

JSON: `script/TOWN/notebook.json` (one entry per article, `en` with `\n` hard
breaks, auto-wrapped at 32 bytes, an empty paragraph becomes a `　` line) and
`script/TOWN/town.json` (one entry per line, no wrapping, 28-byte cap).

## EXE strings (SLPS_035.73)

21 fixed slots, patched in place by `exe.py` after the armips step
(`script/EXE/strings.json`, width = slot - 2). Reward messages are three text
objects: item name, a template, and a one-cell string from the pointer table at
0x8005F0FC (digits ０-９, マ, 覚) drawn over the template's cell 1 (13 px per
cell). English templates therefore keep cell 1 blank: ` x` `９` ` obtained`,
` m` `as` `tered`, ` l` `ea` `rned`. The seven 8-byte names at 0x8006B30C are
only read by the 18-byte default-name copy for the hero; `ヨハネ` is left as is
(no room for "Johannes").
