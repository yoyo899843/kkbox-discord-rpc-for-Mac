from setuptools import setup

APP = ['src/app.py']
DATA_FILES = [('media', ['media/icon_128.png'])]
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'media/icon.icns',
    'plist': {
        'CFBundleName': 'KKBOX Discord RPC',
        'CFBundleDisplayName': 'KKBOX Discord RPC',
        'CFBundleIdentifier': 'com.poyu39.kkbox-discord-rpc',
        'CFBundleShortVersionString': '1.0.0',
        'LSUIElement': True,
    },
    'packages': ['rumps'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
)
