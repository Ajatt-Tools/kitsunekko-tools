#!/bin/bash

if [[ -f ktools.toml ]]; then
	rm -rf -- _site
	hatch run ktools build -c ktools.toml
fi
