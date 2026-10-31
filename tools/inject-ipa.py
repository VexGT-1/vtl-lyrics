r"""Put vtlauto.dylib into a modded Spotify IPA.

    python tools/inject-ipa.py <input.ipa> <vtlauto.dylib> <output.ipa> [--bundle-id ID | --keep-bundle-id]

What it does: copies the dylib into Payload/Spotify.app/Frameworks and adds one LC_LOAD_DYLIB for it
to the main executable and the widget extension, so it loads AFTER spotifyglass.dylib (the order
matters: VTL adds itself to that dylib's provider list). The main app's bundle id is set to
app.silver9358.honey1315 unless --keep-bundle-id or --bundle-id says otherwise.

The load command goes into the free space after the existing ones and nothing else in the binary is
touched. (An earlier version used lief, which re-encoded __LINKEDIT on the whole binary; Chroma
1.0.0-beta.2 built that way would not install.) Every other zip entry is copied byte for byte with its
original permissions. The signature is not fixed here; sign afterwards with whatever you sideload with.
"""
import argparse
import plistlib
import struct
import zipfile

DEFAULT_BUNDLE_ID = "app.silver9358.honey1315"
DYLIB = "@rpath/vtlauto.dylib"
MH_MAGIC_64 = 0xFEEDFACF
LC_LOAD_DYLIB = 0xC
LC_RPATH = 0x8000001C


def load_commands(data):
    magic, _, _, _, ncmds, sizeofcmds, _, _ = struct.unpack_from("<IiiIIIII", data, 0)
    if magic != MH_MAGIC_64:
        raise SystemExit("not a thin 64-bit Mach-O (magic %#x)" % magic)
    off, cmds = 32, []
    for _ in range(ncmds):
        cmd, size = struct.unpack_from("<II", data, off)
        cmds.append((cmd, off, size))
        off += size
    return ncmds, sizeofcmds, cmds


def cmd_string(data, off, str_off_field):
    s = off + struct.unpack_from("<I", data, off + str_off_field)[0]
    return data[s:data.index(b"\0", s)].decode()


def first_section_offset(data, cmds):
    lowest = None
    for cmd, off, _ in cmds:
        if cmd != 0x19:  # LC_SEGMENT_64
            continue
        nsects = struct.unpack_from("<I", data, off + 64)[0]
        for i in range(nsects):
            sect_off = struct.unpack_from("<I", data, off + 72 + i * 80 + 48)[0]
            if sect_off and (lowest is None or sect_off < lowest):
                lowest = sect_off
    return lowest


def add_command(data, payload):
    ncmds, sizeofcmds, cmds = load_commands(data)
    end = 32 + sizeofcmds
    limit = first_section_offset(data, cmds)
    if end + len(payload) > limit or any(data[end:end + len(payload)]):
        raise SystemExit("no free header space for another load command")
    data[end:end + len(payload)] = payload
    struct.pack_into("<II", data, 16, ncmds + 1, sizeofcmds + len(payload))


def padded(name, header_len):
    raw = name.encode() + b"\0"
    total = (header_len + len(raw) + 7) & ~7
    return raw + b"\0" * (total - header_len - len(raw)), total


def patch_binary(blob, rpath):
    data = bytearray(blob)
    _, _, cmds = load_commands(data)
    dylibs = [cmd_string(data, off, 8) for cmd, off, _ in cmds if cmd == LC_LOAD_DYLIB]
    rpaths = [cmd_string(data, off, 8) for cmd, off, _ in cmds if cmd == LC_RPATH]
    if rpath not in rpaths:
        name, size = padded(rpath, 12)
        add_command(data, struct.pack("<III", LC_RPATH, size, 12) + name)
    if DYLIB not in dylibs:
        name, size = padded(DYLIB, 24)
        add_command(data, struct.pack("<IIIIII", LC_LOAD_DYLIB, size, 24, 2, 0x10000, 0x10000) + name)
    return bytes(data)


def set_bundle_id(raw, bundle_id):
    fmt = plistlib.FMT_BINARY if raw[:6] == b"bplist" else plistlib.FMT_XML
    info = plistlib.loads(raw)
    print("bundle id: %s -> %s" % (info.get("CFBundleIdentifier"), bundle_id))
    info["CFBundleIdentifier"] = bundle_id
    return plistlib.dumps(info, fmt=fmt)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ipa")
    ap.add_argument("dylib")
    ap.add_argument("out")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID)
    group.add_argument("--keep-bundle-id", action="store_true")
    a = ap.parse_args()

    src = zipfile.ZipFile(a.ipa)
    names = src.namelist()
    app = next(n.split("/")[1] for n in names if n.startswith("Payload/") and n.split("/")[1].endswith(".app"))
    root = "Payload/%s/" % app
    main_bin = root + app[:-4]
    widget = root + "PlugIns/WidgetExtension.appex/WidgetExtension"
    if root + "Frameworks/spotifyglass.dylib" not in names:
        print("warning: no spotifyglass.dylib in this IPA - VTL has nothing to add itself to")

    replace = {main_bin: lambda b: patch_binary(b, "@executable_path/Frameworks")}
    if widget in names:
        replace[widget] = lambda b: patch_binary(b, "@executable_path/../../Frameworks")
    if not a.keep_bundle_id:
        old_id = plistlib.loads(src.read(root + "Info.plist"))["CFBundleIdentifier"]
        replace[root + "Info.plist"] = lambda b: set_bundle_id(b, a.bundle_id)
        # iOS refuses to install an app whose extensions' ids are not prefixed by the app's own id.
        for n in names:
            parts = n[len(root):].split("/")
            if n.startswith(root + "PlugIns/") and len(parts) == 3 and parts[1].endswith(".appex") and parts[2] == "Info.plist":
                ext_id = plistlib.loads(src.read(n)).get("CFBundleIdentifier", "")
                if ext_id.startswith(old_id + "."):
                    replace[n] = (lambda new: lambda b: set_bundle_id(b, new))(a.bundle_id + ext_id[len(old_id):])

    target = root + "Frameworks/vtlauto.dylib"
    with zipfile.ZipFile(a.out, "w") as out:
        for info in src.infolist():
            if info.filename == target:
                continue
            body = src.read(info)
            if info.filename in replace:
                body = replace[info.filename](body)
            out.writestr(info, body, compress_type=info.compress_type)
        ref = src.getinfo(root + "Frameworks/spotifyglass.dylib") if root + "Frameworks/spotifyglass.dylib" in names else None
        zi = zipfile.ZipInfo(target, date_time=ref.date_time if ref else (2026, 1, 1, 0, 0, 0))
        zi.create_system = 3
        zi.external_attr = (0o100755 << 16)
        zi.compress_type = zipfile.ZIP_DEFLATED
        out.writestr(zi, open(a.dylib, "rb").read())
    print("done:", a.out)


if __name__ == "__main__":
    main()
