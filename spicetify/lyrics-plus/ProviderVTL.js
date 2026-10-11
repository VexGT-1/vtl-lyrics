// VTL provider for Spicetify's Lyrics Plus app: word-timed lyrics from api.vexqyq.com/lyrics/<trackId>.
const ProviderVTL = (() => {
	const API = "https://api.vexqyq.com/lyrics/";

	function parseTime(t) {
		if (!t) return 0;
		const parts = t.split(":");
		let sec = 0;
		for (const p of parts) sec = sec * 60 + Number.parseFloat(p);
		return sec;
	}

	async function findLyrics(info) {
		const id = info.uri.split(":")[2];
		const res = await fetch(API + id);
		if (res.status !== 200) return { error: "No VTL lyrics", uri: info.uri };
		const doc = new DOMParser().parseFromString(await res.text(), "text/xml");
		const lines = Array.from(doc.getElementsByTagName("p")).map((p) => ({
			start: parseTime(p.getAttribute("begin")) * 1000,
			words: Array.from(p.getElementsByTagName("span")).map((s) => ({
				text: s.textContent,
				start: parseTime(s.getAttribute("begin")) * 1000,
				end: parseTime(s.getAttribute("end")) * 1000,
			})),
			text: p.textContent.trim(),
		}));
		return lines.length ? { lines } : { error: "No VTL lyrics", uri: info.uri };
	}

	function getKaraoke(body) {
		const out = body.lines
			.filter((l) => l.words.length)
			.map((l) => ({
				startTime: l.start,
				text: l.words.map((w) => ({ word: `${w.text.trim()} `, time: Math.max(1, Math.round(w.end - w.start)) })),
			}));
		return out.length ? out : null;
	}

	function getSynced(body) {
		const out = body.lines.filter((l) => l.text).map((l) => ({ startTime: l.start, text: l.text }));
		return out.length ? out : null;
	}

	return { findLyrics, getKaraoke, getSynced };
})();
