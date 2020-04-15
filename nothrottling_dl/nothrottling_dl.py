import argparse
import time
from pathlib import Path

import youtube_dl
from youtube_dl.utils import DownloadError, ExtractorError

YDL_OPTS = {"usenetrc": True}
OUTPUT_TEMPLATE = "{}/{} %(title)s.%(ext)s"
INFO_MSG = "<nothrottling-dl> {}"


class ResourceNotFoundError(Exception):
    pass


class NotAPlaylistError(Exception):
    pass


class DownloadOperationError(Exception):
    pass


class Playlist:
    def __init__(self, url):
        self._ydl = youtube_dl.YoutubeDL(YDL_OPTS)
        playlist = self._fetch_plist_data(url)
        self._title = playlist["title"]
        self._enumerated_items = list(enumerate(playlist["entries"], start=1))
        self._length = len(self._enumerated_items)
        self._swidth = len(str(self._length))
        self._fetched = Fetched(self._title)
        self.last_item = False

    def items(self):
        for pos, item in self._enumerated_items:
            if pos == self._length:
                self.last_item = True
            plis = str(pos).zfill(self._swidth)

            if self._fetched.is_fetched_item(item.get("title"), plis):
                yield None
            else:
                self._ydl.params.update({"outtmpl": OUTPUT_TEMPLATE.format(self._title, plis)})
                pre = time.time()
                info = self._fetch_media(item["url"])
                yield (info["duration"], round(time.time() - pre))

    def _fetch_plist_data(self, url):
        try:
            plist_data = self._ydl.extract_info(url, process=False)
        except DownloadError:
            raise ResourceNotFoundError
        else:
            if "entries" not in plist_data:
                raise NotAPlaylistError
        return plist_data

    def _fetch_media(self, url):
        try:
            return self._ydl.extract_info(url)
        except (DownloadError, ExtractorError):
            raise DownloadOperationError


class Fetched:
    def __init__(self, playlist_title):
        playlist_path = Path(playlist_title)
        self._fetched = list(playlist_path.glob("*")) if playlist_path.is_dir() else []

    def is_fetched_item(self, title, plis):
        if not self._fetched:
            return False
        if title:
            filematch = [f for f in self._fetched if title in str(f)]
        else:
            # Ugly hack for Pluralsight (and maybe others),
            # where "title" field is missing from entry data.
            filematch = [f for f in self._fetched if str(f.name).startswith("{} ".format(plis))]
        return True if filematch and not any(f.match("*.part") for f in filematch) else False


def human_time(seconds):
    template = "%Ss"
    if seconds >= 60:
        template = "%Mm:" + template
    if seconds >= 3600:
        template = "%Hh:" + template
    return time.strftime(template, time.gmtime(seconds))


def print_info(msg):
    print(INFO_MSG.format(msg))


def download_playlist(url):
    playlist = Playlist(url)

    print()
    for dl_info in playlist.items():
        if not dl_info:
            print_info("Skipping already downloaded item.")
            print()
            continue
        if playlist.last_item:
            return

        media_dur, dl_dur = dl_info
        delay = max(media_dur - dl_dur, 0)

        print()
        print_info("Duration of media is {}.".format(human_time(media_dur)))
        print_info("Duration of download operation was {}.".format(human_time(dl_dur)))
        if delay:
            print_info("Waiting for {} until next download.".format(human_time(delay)))
            time.sleep(delay)
        else:
            print_info("No waiting necessary.")
        print()


def cli():
    parser = argparse.ArgumentParser(
        description="Download media playlist contents, employing draconian anti-throttling measures."
    )
    parser.add_argument("url", metavar="URL", type=str, help="playlist url")
    args = parser.parse_args()
    err_msg = None

    try:
        download_playlist(args.url)
    except KeyboardInterrupt:
        err_msg = "Aborted by user."
    except ResourceNotFoundError:
        err_msg = "Resource not found (or not supported by youtube-dl)."
    except NotAPlaylistError:
        err_msg = "Resource is not a playlist."
    except DownloadOperationError:
        err_msg = "A problem occured during content download."
    finally:
        if err_msg:
            parser.exit(status=1, message="\nError: {}\n".format(err_msg))


if __name__ == "__main__":
    cli()
