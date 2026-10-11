"""Add VTL as the first source in Spicetify's Lyrics Plus app.

    python install.py [path-to-lyrics-plus]    (default: spicetify's CustomApps/lyrics-plus)
    spicetify apply

Safe to run again. Spicetify upgrades overwrite Lyrics Plus, so run it again after one.
"""
import json, os, re, shutil, subprocess, sys

here = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    app = sys.argv[1]
else:
    cfg = subprocess.run(["spicetify", "-c"], capture_output=True, text=True).stdout.strip()
    cands = [os.path.join(os.path.dirname(cfg), "CustomApps", "lyrics-plus"),
             os.path.join(os.environ.get("LOCALAPPDATA", ""), "spicetify", "CustomApps", "lyrics-plus"),
             os.path.expanduser("~/.config/spicetify/CustomApps/lyrics-plus")]
    app = next((c for c in cands if os.path.isdir(c)), None)
    if not app:
        sys.exit("Lyrics Plus folder not found. Pass its path as an argument.")
print("Lyrics Plus:", app)

def rw(name, fn):
    p = os.path.join(app, name)
    s = open(p, encoding="utf-8").read()
    n = fn(s)
    if n != s:
        open(p, "w", encoding="utf-8").write(n)
    return n != s

shutil.copy(os.path.join(here, "ProviderVTL.js"), os.path.join(app, "ProviderVTL.js"))

def manifest(s):
    m = json.loads(s)
    if "ProviderVTL.js" not in m["subfiles"]:
        m["subfiles"].insert(0, "ProviderVTL.js")
    return json.dumps(m, indent="\t", ensure_ascii=False)

PROV = '''	vtl: async (info) => {
		const result = { uri: info.uri, karaoke: null, synced: null, unsynced: null, provider: "VTL", copyright: null };
		let body;
		try {
			body = await ProviderVTL.findLyrics(info);
		} catch {
			return { error: "No lyrics", uri: info.uri };
		}
		if (body.error) return body;
		result.karaoke = ProviderVTL.getKaraoke(body);
		result.synced = ProviderVTL.getSynced(body);
		result.unsynced = result.synced;
		return result;
	},
'''
def providers(s):
    return s if "vtl: async" in s else s.replace("const Providers = {\n", "const Providers = {\n" + PROV, 1)

CONF = '''		vtl: {
			on: getConfig("lyrics-plus:provider:vtl:on", true),
			desc: "Word-timed lyrics hosted by VTL (api.vexqyq.com). Only tracks VTL has uploaded; every other track falls through to the next source.",
			modes: [KARAOKE, SYNCED, UNSYNCED],
		},
'''
def index(s):
    s = s if "vtl: {" in s else s.replace("\tproviders: {\n", "\tproviders: {\n" + CONF, 1)
    # force a fresh provider order once so VTL lands first
    if "vtl-order-v1" not in s:
        s = s.replace("try {\n\tCONFIG.providersOrder = JSON.parse(CONFIG.providersOrder);",
                      "try {\n\tif (!localStorage.getItem('vtl-order-v1')) { localStorage.removeItem('lyrics-plus:services-order'); localStorage.setItem('vtl-order-v1', '1'); CONFIG.providersOrder = null; }\n\tCONFIG.providersOrder = JSON.parse(CONFIG.providersOrder);", 1)
    return s

print("manifest", rw("manifest.json", manifest))
print("Providers.js", rw("Providers.js", providers))
print("index.js", rw("index.js", index))
print("done. Run: spicetify apply")
