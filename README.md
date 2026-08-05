<div align="center">
<h1><img src="./media/icon_128.png" width="30px"> KKBOX Discord RPC (macOS)</h1>

<p>KKBOX 在 Discord 的豐富顯示 — macOS</p>

</div>

---

## 首先

這是來自 https://github.com/poyu39/kkbox-discord-rpc 的專案，但我是 MacOS 所以弄了 MacOS 版本

## 建立 .app 檔案

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
