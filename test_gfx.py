import dat, build, gfx, labels


def test_sheet_round_trips_through_an_image_and_paste_touches_one_pixel():
    for blob in labels.sheets().values():
        assert gfx.from_image(blob, gfx.to_image(blob)) == blob
        out = gfx.paste(blob, 5, 7, [[9]])
        assert len(out) == len(blob) and gfx.get(out, 5, 7) == 9
        assert gfx.paste(out, 5, 7, [[gfx.get(blob, 5, 7)]]) == blob


def test_redraw_stays_inside_its_rectangle():
    blob = labels.sheets()["system_ui"]
    rect = (48, 112, 96, 128)
    out = labels.redraw(blob, rect, "SHOP", labels.TITLE, "centre")
    w = gfx.header(blob)[1]
    changed = [(x, y) for y in range(160) for x in range(w) if gfx.get(blob, x, y) != gfx.get(out, x, y)]
    assert changed and all(rect[0] <= x < rect[2] and rect[1] <= y < rect[3] for x, y in changed)


def test_nameplates_keep_sizes_and_stay_in_the_name_rows():
    import struct, town
    ch = town.parse(dat.unpack((build.ORIG / "TOWN.DAT").read_bytes())[4])[0]
    sheet, table = labels.nameplates(ch[7], ch[6])
    assert (len(sheet), len(table)) == (len(ch[7]), len(ch[6])) and sheet != ch[7] and table != ch[6]
    w = gfx.header(sheet)[1]
    assert all(gfx.get(sheet, x, y) == gfx.get(ch[7], x, y) for y in range(96, gfx.height(sheet)) for x in range(w))
    o3 = struct.unpack_from("<I", table, 12)[0]
    assert table[o3:o3 + 4] == ch[6][o3:o3 + 4]
    for i in range(struct.unpack_from("<I", table, o3)[0]):
        u, v, rw, h = table[o3 + 4 + 4 * i:o3 + 8 + 4 * i]
        assert u + rw <= 256


def test_disc_screen_keeps_size_and_leaves_other_frames_alone():
    sub = dat.unpack((build.ORIG / "SYSTEM.DAT").read_bytes())[100]
    out = labels.disc_screen(sub)
    assert len(out) == len(sub) and out != sub
    assert out[labels.DISC_TABLE + 0x504:labels.DISC_SHEET] == sub[labels.DISC_TABLE + 0x504:labels.DISC_SHEET]   # background


def test_instruction_page_keeps_sizes_and_only_moves_its_own_frame():
    import town
    sub = dat.unpack((build.ORIG / "TOWN.DAT").read_bytes())[36]
    ch = town.parse(sub)[0]
    spec = labels.PANELS[36]
    sheet, table = labels.panel(ch[spec["sheet"]], ch[spec["table"]], spec)
    assert (len(sheet), len(table)) == (len(ch[spec["sheet"]]), len(ch[spec["table"]]))
    changed = [i for i in range(len(table)) if table[i] != ch[spec["table"]][i]]
    assert changed
    assert sheet[:gfx.header(sheet)[2]] == ch[spec["sheet"]][:gfx.header(sheet)[2]]      # palette untouched


def test_circus_pictures_keep_every_file_the_same_size():
    import town
    subs = dat.unpack((build.ORIG / "TOWN.DAT").read_bytes())
    for i in labels.CIRCUS_FILES:
        tree = town.parse(subs[i])
        labels.circus(i, tree)
        out = town.rebuild(tree)
        assert len(out) == len(subs[i]) and out != subs[i], i


if __name__ == "__main__":
    test_sheet_round_trips_through_an_image_and_paste_touches_one_pixel()
    test_redraw_stays_inside_its_rectangle()
    test_nameplates_keep_sizes_and_stay_in_the_name_rows()
    test_disc_screen_keeps_size_and_leaves_other_frames_alone()
    test_instruction_page_keeps_sizes_and_only_moves_its_own_frame()
    test_circus_pictures_keep_every_file_the_same_size()
    print("ok")
