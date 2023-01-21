# kitsunekko-tools

A set of scripts for creating a local [kitsunekko](http://kitsunekko.net/dirlist.php?dir=subtitles/japanese/&sort=date&order=desc) mirror.

## Usage

1) Install dependencies.

    ``` bash
    pip install -r requirements.txt
    ```
2) Change [settings](settings.json).
    
    ``` bash
    vim settings.json
    ```
    
    * `destination` - the local folder the files should be downloaded to.
    * `proxy` - Your proxy settings.
       Set to `null` if you don't use proxies.
       By default, it is set to the Tor address.
    
    Everything else usually doesn't need to be changed.
3) Run.

    ``` bash
    bash run
    ```
