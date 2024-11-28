# kitsunekko-tools

[![Chat](https://img.shields.io/badge/chat-join-green?style=for-the-badge&logo=Telegram&logoColor=green)](https://tatsumoto.neocities.org/blog/join-our-community)
[![Support](https://img.shields.io/badge/support-developer-orange?style=for-the-badge&logo=Patreon&logoColor=orange)](https://tatsumoto.neocities.org/blog/donating-to-tatsumoto)

A set of scripts for creating a
local [kitsunekko](http://kitsunekko.net/dirlist.php?dir=subtitles/japanese/&sort=date&order=desc)
mirror.

The main benefit of having all subtitles saved locally
is that you can browse them using [lf](https://wiki.archlinux.org/title/Lf)
and quickly search with [fzf](https://wiki.archlinux.org/title/Fzf).

## Install

Install using [pipx](https://pipx.pypa.io/stable/) from [pypi](https://pypi.org/project/kitsunekko-tools/).

```bash
pipx install kitsunekko-tools
```

## Configure

Run this command to create the config file.

```bash
ktools config create
```

Edit the config file.

 * `destination` - the local folder where the files should be downloaded.
 * `proxy` - Your proxy settings.
   Set to `""` (empty string) if you don't use proxies.
   By default, it is set to the default Tor address.

Everything else usually doesn't need to be changed.

## Usage

> [!TIP]
> Clone [kitsunekko-mirror](https://github.com/Ajatt-Tools/kitsunekko-mirror)
> before downloading from kitsunekko directly.

The first time, run full sync.
It will download everything.

``` bash
ktools sync --full
```

Run sync.
If you already have downloaded everything once,
this command will skip files that have not been modified recently.

``` bash
ktools sync
```

The `skip_older` config parameter controls what files should be skipped during regular runs.

## Upload your mirror to Mega

1) Install [megatools](https://archlinux.org/packages/extra/x86_64/megatools/).
2) Create `~/.megarc` and [specify](https://megatools.megous.com/man/megarc.html) your credentials.
3) Run `ktools upload`.

## Ignoring certain files

To prevent some files from being downloaded (because they are too big, broken, etc.),
Create a file named `.kitsuignore` in the root of `destination`
and fill it with paths relative to `destination`.

## Help

Run `ktools --help` to print a help page.

## Environment variables

* `KITSU_API_KEY` - overwrite api_key in the config.
* `KITSU_API_URL` - overwrite api_url in the config.

## Kitsunekko mirror

[kitsunekko-mirror](https://github.com/Ajatt-Tools/kitsunekko-mirror)
is a git repository with Japanese anime subtitles.
