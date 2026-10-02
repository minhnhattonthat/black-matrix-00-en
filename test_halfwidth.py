import halfwidth

FONT = halfwidth.FONT.read_bytes()


def rows(cell):
    return ["".join("#" if cell[2 * y + x // 8] & (0x80 >> (x % 8)) else "." for x in range(12))
            for y in range(12)]


def test_font_has_95_glyphs_in_top_six_bits():
    assert len(FONT) == 95 * 12
    assert all(b & 3 == 0 for b in FONT)
    assert not any(FONT[:12])                       # space is blank
    assert any(FONT[(ord("A") - 0x20) * 12:][:12])  # A is not


def test_compose_puts_left_in_columns_0_5_and_right_in_6_11():
    a = rows(halfwidth.compose(FONT, ord("A"), ord(" ")))
    b = rows(halfwidth.compose(FONT, ord(" "), ord("A")))
    assert any("#" in r for r in a)
    assert all(r[6:] == "......" for r in a)
    assert all(r[:6] == "......" for r in b)
    assert [r[:6] for r in a] == [r[6:] for r in b]


def test_compose_out_of_range_is_space():
    blank = halfwidth.compose(FONT, 0x20, 0x20)
    assert halfwidth.compose(FONT, 0x09, 0x7F) == blank == bytes(24)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
