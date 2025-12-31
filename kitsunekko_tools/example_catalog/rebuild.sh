#!/bin/bash

if [[ -f ktools.toml ]]; then
	rm -rf -- _site
	ktools build -c ktools.toml
fi
