import dat, build, lz, labels


def test_unpack_pack_round_trip_on_a_portrait_file():
    packed = dat.unpack((build.ORIG / "EVENT.DAT").read_bytes())[190]
    data, used = lz.unpack(packed)
    assert used <= len(packed) and len(data) % 4 == 0
    again = lz.pack(data, packed[:3])
    assert again[:3] == packed[:3] and lz.unpack(again)[0] == data
    assert len(again) <= len(packed)                      # ours must still fit comfortably


def test_plate_changes_only_the_name_picture():
    packed = dat.unpack((build.ORIG / "EVENT.DAT").read_bytes())[190]
    old, _ = lz.unpack(packed)
    new, _ = lz.unpack(labels.plate(packed, "Cain"))
    changed = [i for i in range(len(old)) if old[i] != new[i]]
    assert len(new) == len(old) and changed and min(changed) >= len(old) - 0x2F8 + 0x38   # inside the plate's pixels


if __name__ == "__main__":
    test_unpack_pack_round_trip_on_a_portrait_file()
    test_plate_changes_only_the_name_picture()
    print("ok")
