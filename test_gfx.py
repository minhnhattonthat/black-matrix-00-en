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


if __name__ == "__main__":
    test_sheet_round_trips_through_an_image_and_paste_touches_one_pixel()
    test_redraw_stays_inside_its_rectangle()
    print("ok")
