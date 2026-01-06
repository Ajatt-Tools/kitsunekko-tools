#!/bin/bash

echo "Formatting $PWD"

readonly ROOT_DIR=$(git rev-parse --show-toplevel)

cd -- "$ROOT_DIR" || exit 1

readarray -t FILES <<<"$(git ls-files | grep -P '\.py$')"
readonly -a FILES

pyupgrade --py312-plus "${FILES[@]}"
isort "${FILES[@]}"
black "${FILES[@]}"
prettier -w kitsunekko_tools/example_catalog/resources
