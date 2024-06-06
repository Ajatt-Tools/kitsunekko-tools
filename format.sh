#!/bin/bash

echo "Formatting $PWD"

readarray -t FILES <<<"$(git ls-files | grep -P '\.py$')"
readonly -a FILES

pyupgrade --py311-plus "${FILES[@]}"
isort "${FILES[@]}"
black "${FILES[@]}"
