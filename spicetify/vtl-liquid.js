// VTL Lyrics for Liquid Lyrics - Spicetify extension (installs through the Spicetify Marketplace).
// On every Spotify start it downloads the NEWEST Liquid Lyrics from NMWplays/Liquid-Lyrics, adds VTL as
// the first lyrics source (word-timed, from api.vexqyq.com/lyrics/<trackId>), and runs it. Tracks VTL has
// nothing for fall through to Spicy Lyrics and Spotify as usual. Nothing is written to disk.
// Do not also install Liquid Lyrics on its own, two copies would fight.
// If a Liquid Lyrics update ever moves the code this patches, it still runs plain Liquid Lyrics and
// shows a notice. Offline: the last downloaded copy is reused.
(async function VTLLiquid() {
  if (window.__vtlLiquid) return;
  window.__vtlLiquid = true;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  while (!(window.Spicetify && Spicetify.Player && Spicetify.showNotification)) await sleep(300);

  const RAW = "https://raw.githubusercontent.com/NMWplays/Liquid-Lyrics/main/liquid-lyrics.js";
  const CACHE = "vtl-liquid-lyrics-src";
  const PROVIDER = "async function VTLfetch({id:t}){try{let e=String(t).includes(\":\")?String(t).split(\":\")[2]:String(t),r=await fetch(\"https://api.vexqyq.com/lyrics/\"+e);if(r.status!==200)return{status:\"missing_lyrics\",data:null};let d=new DOMParser().parseFromString(await r.text(),\"text/xml\"),tm=x=>{if(!x)return 0;let s=0;for(let p of x.split(\":\"))s=s*60+parseFloat(p);return Math.round(s*1e3)},first=null,C=[];for(let p of Array.from(d.getElementsByTagName(\"p\"))){let all=Array.from(p.getElementsByTagName(\"span\")).filter(s=>s.getAttribute(\"begin\")).map(s=>{let bg=!1;for(let n=s.parentNode;n&&n!==p;n=n.parentNode)if(n.getAttribute&&n.getAttribute(\"ttm:role\")===\"x-bg\")bg=!0;return{bg,w:{Text:(s.textContent||\"\").trim(),StartTime:tm(s.getAttribute(\"begin\")),EndTime:tm(s.getAttribute(\"end\")),IsPartOfWord:!1}}}).filter(x=>x.w.Text),lead=all.filter(x=>!x.bg).map(x=>x.w),bgw=all.filter(x=>x.bg).map(x=>x.w);if(!lead.length){lead=bgw;bgw=[]}if(!lead.length)continue;let ag=p.getAttribute(\"ttm:agent\")||\"v1\";first===null&&(first=ag);let it={Type:\"Vocal\",OppositeAligned:ag!==first,Lead:{StartTime:lead[0].StartTime,EndTime:lead[lead.length-1].EndTime,Syllables:lead}};bgw.length&&(it.Background=[{StartTime:bgw[0].StartTime,EndTime:bgw[bgw.length-1].EndTime,Syllables:bgw}]);C.push(it)}if(!C.length)return{status:\"missing_lyrics\",data:null};return{status:\"success\",data:{Id:e,Type:\"Syllable\",SongWriters:[],Content:C,StartTime:C[0].Lead.StartTime,EndTime:C[C.length-1].Lead.EndTime,Provider:\"vtl\"}}}catch(e){return{status:\"error\",data:null,error:{code:\"PROVIDER_FAILED\",message:String(e&&e.message||e)}}}}\n";

  let src = null;
  try {
    const res = await fetch(RAW, { cache: "no-cache" });
    if (res.ok) {
      src = await res.text();
      try { localStorage.setItem(CACHE, src); } catch (e) {}
    }
  } catch (e) {}
  if (!src) { try { src = localStorage.getItem(CACHE); } catch (e) {} }
  if (!src) { Spicetify.showNotification("VTL Lyrics: could not download Liquid Lyrics", true); return; }

  const edits = [
    ['Za=["spicy","spotify"]', 'Za=["vtl","spicy","spotify"]'],
    ['var su={spotify:{id:"spotify",fetch:Jr},spicy:{id:"spicy",fetch:oo}}',
     PROVIDER + 'var su={vtl:{id:"vtl",fetch:VTLfetch},spotify:{id:"spotify",fetch:Jr},spicy:{id:"spicy",fetch:oo}}'],
    ['return e==="spotify"?"via Spotify"', 'return e==="vtl"?"via VTL":e==="spotify"?"via Spotify"'],
  ];
  let code = src;
  let ok = true;
  for (const [from, to] of edits) {
    if (!code.includes(from)) { ok = false; break; }
    code = code.replace(from, () => to);
  }
  if (!ok) {
    code = src;
    Spicetify.showNotification("VTL Lyrics: Liquid Lyrics changed, running it without the VTL source", true);
  }

  try {
    const s = document.createElement("script");
    s.textContent = code;
    document.head.appendChild(s);
  } catch (e) {
    (0, eval)(code);
  }
})();
