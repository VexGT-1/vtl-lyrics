"""Add VTL as the first lyrics source in Liquid Lyrics (NMWplays/Liquid-Lyrics).

    python install.py [path-to-liquid-lyrics.js]
    spicetify apply

With no argument it downloads the current liquid-lyrics.js from GitHub, adds VTL, writes it to
Spicetify's Extensions folder and enables it. Safe to run again. A Liquid Lyrics update (or the
Marketplace) overwrites the file, so run this again after one.
"""
import os, subprocess, sys, urllib.request

here = os.path.dirname(os.path.abspath(__file__))
RAW = "https://raw.githubusercontent.com/NMWplays/Liquid-Lyrics/main/liquid-lyrics.js"
cfg = subprocess.run(["spicetify", "-c"], capture_output=True, text=True).stdout.strip()
ext_dir = os.path.join(os.path.dirname(cfg), "Extensions")
os.makedirs(ext_dir, exist_ok=True)
dest = os.path.join(ext_dir, "liquid-lyrics.js")

if len(sys.argv) > 1:
    src = open(sys.argv[1], encoding="utf-8").read()
elif os.path.exists(dest) and "VTLfetch" not in open(dest, encoding="utf-8").read():
    src = open(dest, encoding="utf-8").read()          # already installed (Marketplace), patch in place
elif os.path.exists(dest):
    print("already patched, re-patching from a fresh download")
    src = urllib.request.urlopen(urllib.request.Request(RAW, headers={"User-Agent": "vtl-installer"})).read().decode("utf-8")
else:
    req = urllib.request.Request(RAW, headers={"User-Agent": "vtl-installer"})
    src = urllib.request.urlopen(req).read().decode("utf-8")

if "VTLfetch" in src and len(sys.argv) > 1:
    print("already patched")
else:
    prov = open(os.path.join(here, "vtl-provider.js"), encoding="utf-8").read().strip() + "\n"
    edits = [
        ('Za=["spicy","spotify"]', 'Za=["vtl","spicy","spotify"]'),
        ('var su={spotify:{id:"spotify",fetch:Jr},spicy:{id:"spicy",fetch:oo}}',
         prov + 'var su={vtl:{id:"vtl",fetch:VTLfetch},spotify:{id:"spotify",fetch:Jr},spicy:{id:"spicy",fetch:oo}}'),
        ('return e==="spotify"?"via Spotify"', 'return e==="vtl"?"via VTL":e==="spotify"?"via Spotify"'),
    ]
    for old, new in edits:
        if old not in src:
            sys.exit("Liquid Lyrics changed, cannot patch (missing: %s...). Tell Vex." % old[:40])
        src = src.replace(old, new, 1)
    open(dest, "w", encoding="utf-8").write(src)
    print("patched", dest)

subprocess.run(["spicetify", "config", "extensions", "liquid-lyrics.js"])
print("done. Run: spicetify apply")
