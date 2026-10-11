# VTL Lyrics for desktop Spotify (Spicetify) - tutorial

Puts VTL's word-synced lyrics into Spotify's own Lyrics tab on Windows/Mac/Linux desktop. If VTL has no lyrics for a track, Spotify's normal lyrics stay.

## 1. Install Spicetify (once)

Windows, in PowerShell:

```
iwr -useb https://raw.githubusercontent.com/spicetify/cli/main/install.ps1 | iex
```

Mac/Linux:

```
curl -fsSL https://raw.githubusercontent.com/spicetify/cli/main/install.sh | sh
```

Open Spotify once and log in, then close it. (Use the normal Spotify desktop app, not the Microsoft Store one.)

## 2. Add the extension

1. Put `vtl-lyrics.js` in Spicetify's Extensions folder:
   - Windows: `%appdata%\spicetify\Extensions`
   - Mac/Linux: `~/.config/spicetify/Extensions`
2. Turn it on and apply:

```
spicetify config extensions vtl-lyrics.js
spicetify backup apply
```

(`backup apply` the first time, plain `spicetify apply` after that.)

## 3. Use it

1. Open Spotify and play a track VTL has lyrics for.
2. Open the Lyrics tab. You get VTL's lyrics, word by word, with a small "VTL LYRICS" label at the top.
3. A track VTL has nothing for just shows Spotify's normal lyrics.

Which tracks have lyrics: https://lyrics.vexqyq.com

## If it does not show up

- Spotify updated and the extension stopped working: run `spicetify backup apply` again.
- The Lyrics tab never changes: the extension finds the tab by Spotify's internal names (the `SELECTORS` list at the top of `vtl-lyrics.js`), and Spotify changes those between versions. Fix: right-click in Spotify, Spicetify, Show Devtools, inspect the Lyrics tab, find the element that holds the lyric lines, and add its `data-testid` or class to `SELECTORS`. Then `spicetify apply`.
- Nothing at all: `spicetify config extensions` should list `vtl-lyrics.js`, then `spicetify apply`.
- To remove it: `spicetify config extensions vtl-lyrics.js-` then `spicetify apply`.

Not tested against a live Spotify desktop client yet, so the first run is also the first real test.
