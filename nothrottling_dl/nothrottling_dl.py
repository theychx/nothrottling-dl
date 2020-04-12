import argparse
import time
from pathlib import Path

import youtube_dl
from youtube_dl.utils import DownloadError, ExtractorError

YTDL_OPTS = {"usenetrc": True}
OUTPUT_TEMPLATE = "{}/{} {}.%(ext)s"
INFO_MSG = "<nothrottling-dl> {}"


class ResourceNotFoundError(Exception):
    pass


class NotAPlaylistError(Exception):
    pass


class DownloadOperationError(Exception):
    pass


class YtdlSession:
    ytdl = youtube_dl.YoutubeDL(YTDL_OPTS)


class Playlist:
    def __init__(self, url):
        playlist = self._fetch_plist_data(url)
        self.title = playlist["title"]
        self._enumerated_items = list(enumerate(playlist["entries"], start=1))
        self.length = len(self._enumerated_items)

    @property
    def items(self):
        return (MediaItem(e) for e in self._enumerated_items)

    def _fetch_plist_data(self, url):
        try:
            plist_data = YtdlSession.ytdl.extract_info(url, process=False)
        except DownloadError:
            raise ResourceNotFoundError
        else:
            if "entries" not in plist_data:
                raise NotAPlaylistError
        return plist_data


class MediaItem:
    def __init__(self, enumerated_item):
        self.pos, self._item = enumerated_item
        self.title = self._item["title"]

    def download(self, outtmpl=None):
        if outtmpl:
            YtdlSession.ytdl.params.update({"outtmpl": outtmpl})
        pre = time.time()

        try:
            info = YtdlSession.ytdl.extract_info(self._item["url"])
        except (DownloadError, ExtractorError):
            raise DownloadOperationError
        return (info["duration"], round(time.time() - pre))


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
    itemn_zerofill = len(str(playlist.length))
    already_fetched = None
    playlist_path = Path(playlist.title)

    if playlist_path.is_dir():
        already_fetched = list(playlist_path.glob("*"))

    print()
    for item in playlist.items:
        if already_fetched:
            filematch = [f for f in already_fetched if item.title in str(f)]
            if filematch and not any(f.match("*.part") for f in filematch):
                print_info('Skipping "{}".'.format(item.title))
                print()
                continue

        plis = str(item.pos).zfill(itemn_zerofill)
        outtmpl = OUTPUT_TEMPLATE.format(playlist.title, plis, item.title)
        media_dur, dl_dur = item.download(outtmpl=outtmpl)
        delay = max(media_dur - dl_dur, 0)

        if item.pos == playlist.length:
            return

        print()
        if delay:
            print_info("Duration of media is {}.".format(human_time(media_dur)))
            print_info("Duration of download operation was {}.".format(human_time(dl_dur)))
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
