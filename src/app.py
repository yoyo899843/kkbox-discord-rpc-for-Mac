import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time

import psutil
import rumps
from pypresence import Presence
from pypresence.types import ActivityType

KKBOX_BUNDLE_ID = 'com.kkbox.electron-app'
NOWPLAYING_FIELDS = ['title', 'artist', 'album', 'duration', 'elapsedTime', 'playbackRate', 'clientBundleIdentifier']


class Player:
    def __init__(self, title=None, artist=None, album=None, now_time=None, song_len=None, status=None):
        self.title = title
        self.artist = artist
        self.album = album
        self.now_time = now_time
        self.song_len = song_len
        self.status = status

    def print_info(self, logger: logging.Logger):
        logger.info(f'status: {self.status}')
        logger.info(f'title: {self.title}')
        logger.info(f'artist: {self.artist}')
        logger.info(f'album: {self.album}')
        logger.info(f'now_time: {self.now_time}')
        logger.info(f'song_len: {self.song_len}\n')

    def have_empty(self):
        has_empty_text = any((not isinstance(field, str)) or (not field.strip()) for field in (self.title, self.artist))

        invalid_time = (
            not isinstance(self.now_time, int) or self.now_time < 0 or
            not isinstance(self.song_len, int) or self.song_len <= 0
        )

        return has_empty_text or invalid_time


class DiscordRPC:
    def __init__(self, application_id):
        self.rpc = Presence(application_id)
        self.is_showing = False

    def connect(self):
        try:
            self.rpc.connect()
            return True
        except Exception:
            return False

    def update(self, player: Player):
        assets = {
            'large_image': 'https://github.com/poyu39/kkbox-discord-rpc/blob/main/media/icon_128.png?raw=true',
            'large_text': player.album if player.album else 'KKBOX',
            'small_image': 'https://github.com/poyu39/kkbox-discord-rpc/blob/main/media/icon_128.png?raw=true',
            'small_text': 'KKBOX Discord RPC',
            'small_url': 'https://github.com/poyu39/kkbox-discord-rpc'
        }

        start_time = time.time() - player.now_time
        end_time = start_time + player.song_len
        self.rpc.update(
            payload_override={
                'cmd': 'SET_ACTIVITY',
                'args': {
                    'pid': os.getpid(),
                    'activity': {
                        'type': ActivityType.LISTENING.value,
                        'state': player.artist,
                        'details': player.title,
                        'timestamps': {
                            'start': int(start_time) * 1000,
                            'end': int(end_time) * 1000
                        },
                        'assets': assets,
                        'instance': True
                    }
                },
                'nonce': '{:.20f}'.format(time.time())
            }
        )
        self.is_showing = True
        return True

    def clear(self):
        self.rpc.clear()
        self.is_showing = False

    def close(self):
        self.rpc.close()
        self.is_showing = False


NOWPLAYING_CLI_FALLBACK_PATHS = ['/opt/homebrew/bin/nowplaying-cli', '/usr/local/bin/nowplaying-cli']


class KKBOX:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.nowplaying_cli = self._find_nowplaying_cli()

        if self.nowplaying_cli is None:
            self.logger.error("'nowplaying-cli' not found. Install it with: brew install nowplaying-cli")
            sys.exit(1)

    def _find_nowplaying_cli(self):
        # apps launched from Finder/Login Items get a minimal PATH that
        # doesn't include Homebrew's bin dirs, so shutil.which() alone
        # isn't enough here.
        found = shutil.which('nowplaying-cli')
        if found:
            return found

        for path in NOWPLAYING_CLI_FALLBACK_PATHS:
            if os.path.isfile(path):
                return path

        return None

    def is_kkbox_running(self):
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] == 'KKBOX':
                return True
        return False

    def start_kkbox(self):
        if self.is_kkbox_running():
            return
        subprocess.Popen(['open', '-a', 'KKBOX'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)

    def get_player(self) -> Player:
        try:
            result = subprocess.run(
                [self.nowplaying_cli, 'get', '--json', *NOWPLAYING_FIELDS],
                capture_output=True, text=True, encoding='utf-8', timeout=5
            )
            data = json.loads(result.stdout)
        except (subprocess.SubprocessError, json.JSONDecodeError):
            return Player()

        if data.get('clientBundleIdentifier') != KKBOX_BUNDLE_ID:
            return Player()

        title = data.get('title')
        artist = data.get('artist')
        album = data.get('album')
        duration = data.get('duration')
        elapsed = data.get('elapsedTime')
        rate = data.get('playbackRate')

        song_len = int(duration) if isinstance(duration, (int, float)) else None
        now_time = int(elapsed) if isinstance(elapsed, (int, float)) else None
        status = 'playing' if rate else 'paused' if rate is not None else None

        return Player(title, artist, album, now_time, song_len, status)


class MenuBarApp(rumps.App):
    def __init__(self):
        super().__init__('KKBOX Discord RPC', icon='media/icon_128.png', quit_button='結束')
        self.status_item = rumps.MenuItem('狀態: 啟動中…')
        self.menu = [self.status_item]

        self.logger = logging.getLogger(__name__)
        self.kkbox = KKBOX()
        self.rpc = DiscordRPC('1017636675817578538')

        self.last_song = None
        self.last_status = 'paused'

        self.worker = threading.Thread(target=self._run_loop, daemon=True)
        self.worker.start()

    def _set_status(self, text: str):
        self.status_item.title = f'狀態: {text}'

    def _run_loop(self):
        self.kkbox.start_kkbox()

        if self.rpc.connect():
            self.logger.info('Discord RPC connected successfully')
            self._set_status('已連接 Discord')
        else:
            self.logger.error('Discord RPC connection failed')
            self._set_status('連接 Discord 失敗')
            return

        while True:
            try:
                player = self.kkbox.get_player()

                if player.have_empty():
                    if self.last_status != 'paused' and self.rpc.is_showing:
                        self.rpc.clear()
                        self.logger.info('cleared (nothing playing on KKBOX)')
                    self.last_song = None
                    self.last_status = 'paused'
                    self._set_status('未在播放')
                    time.sleep(1)
                    continue

                need_refresh_rpc = (self.last_song != player.title) or (self.last_status != player.status)

                if need_refresh_rpc and player.status == 'playing':
                    if self.rpc.update(player):
                        player.print_info(logger=self.logger)
                    self._set_status(f'{player.title} - {player.artist}')

                elif need_refresh_rpc and player.status == 'paused':
                    player.print_info(logger=self.logger)
                    self.rpc.clear()
                    self._set_status(f'已暫停 - {player.title}')

                self.last_song = player.title
                self.last_status = player.status

            except Exception as e:
                self.logger.error(f'Error: {e}')
                self._set_status(f'錯誤: {e}')

            time.sleep(1)


if __name__ == '__main__':
    log_dir = os.path.expanduser('~/Library/Logs/KKBOX Discord RPC')
    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(log_dir, 'app.log')),
        ]
    )

    MenuBarApp().run()
