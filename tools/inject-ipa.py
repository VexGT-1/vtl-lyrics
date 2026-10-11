r"""Put vtlauto.dylib into a modded Spotify IPA.

    pip install lief
    python tools/inject-ipa.py <input.ipa> <vtlauto.dylib> <output.ipa> [--bundle-id ID | --keep-bundle-id]

What it does: copies the dylib into Payload/Spotify.app/Frameworks, and adds a load command for it
(and an rpath) to the main executable and the widget extension, so it loads AFTER spotifyglass.dylib
(the order matters: VTL adds itself to that dylib's provider list). The main app's bundle id is set to
app.silver9358.honey1315 unless --keep-bundle-id or --bundle-id says otherwise. The IPA's signature is
not touched here; sign it afterwards with whatever you sideload with.
"""
import argparse
import os
import plistlib
import shutil
import tempfile
import zipfile

import lief

DEFAULT_BUNDLE_ID = "app.silver9358.honey1315"


def patch_binary(path, rpath):
    fat = lief.MachO.parse(path)
    binary = fat.at(0)
    if not any("RPATH" in str(c.command) and getattr(c, "path", None) == rpath for c in binary.commands):
        binary.add(lief.MachO.RPathCommand.create(rpath))
    if not any("DYLIB" in str(c.command) and getattr(c, "name", None) == "@rpath/vtlauto.dylib"
               for c in binary.commands):
        binary.add(lief.MachO.DylibCommand.load_dylib("@rpath/vtlauto.dylib", 0x10000, 0x10000))
    fat.write(path)


def set_bundle_id(app_dir, bundle_id):
    path = os.path.join(app_dir, "Info.plist")
    raw = open(path, "rb").read()
    fmt = plistlib.FMT_BINARY if raw[:6] == b"bplist" else plistlib.FMT_XML
    info = plistlib.loads(raw)
    print("bundle id: %s -> %s" % (info.get("CFBundleIdentifier"), bundle_id))
    info["CFBundleIdentifier"] = bundle_id
    with open(path, "wb") as f:
        plistlib.dump(info, f, fmt=fmt)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ipa")
    ap.add_argument("dylib")
    ap.add_argument("out")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID)
    group.add_argument("--keep-bundle-id", action="store_true")
    a = ap.parse_args()

    work = tempfile.mkdtemp(prefix="vtl-inject-")
    try:
        with zipfile.ZipFile(a.ipa) as z:
            z.extractall(work)
        payload = os.path.join(work, "Payload")
        app_dir = next(os.path.join(payload, n) for n in os.listdir(payload) if n.endswith(".app"))
        frameworks = os.path.join(app_dir, "Frameworks")
        if not os.path.exists(os.path.join(frameworks, "spotifyglass.dylib")):
            print("warning: no spotifyglass.dylib in this IPA - VTL has nothing to add itself to")
        os.makedirs(frameworks, exist_ok=True)
        shutil.copy2(a.dylib, os.path.join(frameworks, "vtlauto.dylib"))

        if not a.keep_bundle_id:
            set_bundle_id(app_dir, a.bundle_id)

        main_bin = os.path.join(app_dir, os.path.splitext(os.path.basename(app_dir))[0])
        patch_binary(main_bin, "@executable_path/Frameworks")
        widget = os.path.join(app_dir, "PlugIns", "WidgetExtension.appex", "WidgetExtension")
        if os.path.exists(widget):
            patch_binary(widget, "@executable_path/../../Frameworks")

        if os.path.exists(a.out):
            os.remove(a.out)
        with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED) as z:
            for dirpath, _, files in os.walk(payload):
                for fn in files:
                    full = os.path.join(dirpath, fn)
                    z.write(full, os.path.relpath(full, work))
        print("done:", a.out, os.path.getsize(a.out), "bytes")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
