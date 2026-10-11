# VTL Lyrics

Word-synced lyrics from VTL, as their own source in Spotify. Two pieces:

| Folder | What | Where it runs |
|---|---|---|
| `ios/` | `vtlauto.dylib`, adds **VTL** as its own entry in the Lyrics Sources list of the modded Spotify from [chroma.pw](https://chroma.pw). BiniLyrics and every other source stay as they are. | iPhone (sideloaded) |
| `spicetify/` | `vtl-lyrics.js`, swaps VTL lyrics into Spotify's own Lyrics tab. Install steps in `spicetify/TUTORIAL.md`. | Desktop Spotify |
| `tools/inject-ipa.py` | Puts the dylib into an IPA. | Your PC |

Not made by or affiliated with Spotify or chroma.pw.

## Where the lyrics come from

`https://api.vexqyq.com/lyrics/<spotifyTrackId>` returns a word-timed TTML file for tracks VTL has. Browse and download them at https://lyrics.vexqyq.com. A track VTL has nothing for answers nothing, so the next source in your list takes over.

## iOS

1. Get `vtlauto.dylib`: run the **Build iOS dylib** workflow (Actions tab, macOS runner) and download the `vtlauto-build` artifact.
2. Put it into your modded Spotify IPA:
   ```
   pip install lief
   python tools/inject-ipa.py spotify.ipa vtlauto.dylib spotify-vtl.ipa
   ```
   Or inject the dylib with a sideloader that supports it (it must load after `spotifyglass.dylib`).
3. Install and sign as usual. On launch a green badge says **VTL source added**.
4. Settings, Lyrics Sources: VTL is its own row. Turn it on and drag it to the top.

### How it works

Read off the real `spotifyglass.dylib`, not guessed. Its lyrics sources are `SGLyricsProvider` objects held in one static `NSArray`, built once by `+[NSArray arrayWithObjects:count:]`. Both the lyrics fetch and the Lyrics Sources page read that array. `vtlauto` appends a seventh provider to it, so VTL gets a real row and a real place in the fetch chain, and BiniLyrics' own provider is never touched. If the array was already built before `vtlauto` loads, it rewrites the static slot instead, but only for builds listed in `kKnownLists` in `ios/Sources/VTLAuto.x` (matched by the dylib's `LC_UUID`; the slot moves between builds).

VTL's source asks the real BiniLyrics source to do the TTML parsing, with a marked query; a small `NSURLProtocol` answers that one request with a pointer to `api.vexqyq.com/lyrics/<id>`. Tracks VTL doesn't have are passed on.

### Supported `spotifyglass.dylib` builds

| Build | LC_UUID | Slot |
|---|---|---|
| chroma kit v0.50.0 | `adfbf83aec1a3186948d7ff4318bb6ba` | `0x3b3f78` |
| 0.51.0-beta.1 | `d4c75c03b90b329d83b960d768cc43aa` | `0x532ed0` |

A build that is not in the table still works if `vtlauto` loads before the list is built (the usual case). To add a build: find the function that stores a 6-element `arrayWithObjects:count:` result to a static (it builds the `binilyrics` provider) and read the address in its `str x0, [x8, #off]`.

## Desktop (Spicetify)

See `spicetify/TUTORIAL.md`. Not tested against a live desktop client yet.
