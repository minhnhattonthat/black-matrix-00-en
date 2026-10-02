import dat
from build import ARCHIVES, ORIG


def test_roundtrip_all_archives():
    for name in ARCHIVES:
        data = (ORIG / name).read_bytes()
        assert dat.pack(dat.unpack(data)) == data, name


def test_grown_subfile_shifts_later_offsets():
    files = dat.unpack((ORIG / "SCENARIO.DAT").read_bytes())
    files[0] += b"\x01" * 5000            # grows by 3 sectors
    again = dat.unpack(dat.pack(files))
    assert again[0].rstrip(b"\0") == files[0].rstrip(b"\0")
    assert again[1:] == files[1:]


def test_too_many_files_raises():
    try:
        dat.pack([b""] * 511)             # 8 + 4*511 > 2048
    except ValueError:
        return
    assert False, "expected ValueError"


def test_sector_overflow_raises():
    try:
        dat.pack([bytes(2048 * 40000), bytes(2048 * 40000)])
    except ValueError:
        return
    assert False, "expected ValueError"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
