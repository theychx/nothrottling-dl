# nothrottling-dl
As a means of avoiding getting banned from content providers employing aggresive throttling schemes
(such as Pluralsight), `nothrottling-dl` inserts a waiting period equal to the entire duration of
the downloaded media, before engaging in the next download.

# Installation
```
pip3 install nothrottling-dl
```

Nothrottling-dl requires python 3.6+

# Usage
```
nothrottling-dl [-h] URL
```

Only playlist urls are accepted.
You can specify user credentials in a `.netrc` file (only works if user login is supported in the
specific youtube-dl extractor) as explained [here](https://github.com/ytdl-org/youtube-dl#authentication-with-netrc-file).
