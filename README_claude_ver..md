<div align="center">
<h1><img src="./media/icon_128.png" width="30px"> KKBOX Discord RPC (macOS)</h1>

<p>Displays KKBOX rich presence on Discord — macOS port.</p>

</div>

---

## How it works

Unlike the [Windows version](../Windows), this does **not** scrape the KKBOX
window via Chrome DevTools Protocol. On this build of the macOS KKBOX app,
`--remote-debugging-port` opens the port but the DevTools handler never
responds (confirmed not to be a firewall/sandbox issue — verified against
another local HTTP server in the same process).

Instead, this reads track info from macOS's system-wide **Now Playing**
info (the same source Control Center's media widget uses), via
[`nowplaying-cli`](https://github.com/nowplaying-cli/nowplaying-cli). KKBOX
registers `title` / `artist` / `album` / `duration` / `elapsedTime` /
`playbackRate` there under bundle id `com.kkbox.electron-app`, which this
script filters on so it only reacts when KKBOX (not Music.app, Safari, etc.)
is the active Now Playing source.

Trade-off: the Now Playing API doesn't expose cover art or a track URL, so
the Discord card's large image is a static KKBOX icon instead of the
per-track cover the Windows version shows, and the large-text field shows
the album name instead of streaming quality.

## Requirements

- macOS with [KKBOX.app](https://www.kkbox.com/) installed
- [Homebrew](https://brew.sh/)
- [uv](https://docs.astral.sh/uv/)

## Setup

```sh
brew install nowplaying-cli
cd MacOS
uv sync
```

## Run

```sh
uv run src/app.py
```

Open KKBOX (or let the script launch it), play a song, and your Discord
status should switch to "Listening to KKBOX". The app runs as a menu bar
icon (🎵) showing the current status; click it and choose "結束" to quit.
Logs are written to `~/Library/Logs/KKBOX Discord RPC/app.log`.

## Building a standalone .app

`uv`'s managed Python has zlib statically linked, which `py2app` can't
handle, so packaging needs a Python with a dynamic zlib — the
`python.org` / Homebrew framework build works. Point `uv` at it to build
a throwaway venv, then run `py2app` from there (pyproject.toml is
temporarily moved aside because setuptools would otherwise inject
`install_requires`, which `py2app` rejects):

```sh
uv venv --python /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 .venv-build
source .venv-build/bin/activate
uv pip install psutil rumps py2app "pypresence @ git+https://github.com/qwertyquerty/pypresence.git"
mv pyproject.toml pyproject.toml.bak && python setup.py py2app; mv pyproject.toml.bak pyproject.toml
```

The bundle is written to `dist/KKBOX Discord RPC.app`. Drag it into
`/Applications`, then add it to **System Settings → General → Login
Items** to launch automatically.
