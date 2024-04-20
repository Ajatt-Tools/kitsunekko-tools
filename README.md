# kitsunekko-tools

A set of scripts for creating a
local [kitsunekko](http://kitsunekko.net/dirlist.php?dir=subtitles/japanese/&sort=date&order=desc)
mirror.

The main benefit of having all subtitles saved locally
is that you can browse them using [lf](https://wiki.archlinux.org/title/Lf)
and quickly search with [fzf](https://wiki.archlinux.org/title/Fzf).

## Usage

1) Clone the repository.
2) Change [settings](settings.json).

    ``` bash
    vim settings.json
    ```

   Or you can copy the config file to `~/.config/kitsunekko-tools/settings.json` and edit it there.

    * `destination` - the local folder the files should be downloaded to.
    * `proxy` - Your proxy settings.
      Set to `null` if you don't use proxies.
      By default, it is set to the Tor address.

   Everything else usually doesn't need to be changed.
3) Run.

    ``` bash
    ktools sync
    ```

## Upload your mirror to Mega

1) Install [megatools](https://aur.archlinux.org/packages/megatools).
2) Create `~/.megarc` and [specify](https://megatools.megous.com/man/megarc.html) your credentials.
3) Run `ktools upload`.

## Ignoring certain files

To prevent some files from being downloaded (because they are too big, broken, etc.),
Create a file named `.kitsuignore` in the root of `destination`
and fill it with Unix shell-style wildcards, one per line.
