#!/bin/bash

echo "Formatting $PWD"

readonly ROOT_DIR=$(git rev-parse --show-toplevel)

cd -- "$ROOT_DIR" || exit 1

readarray -t FILES <<<"$(git ls-files | grep -P '\.py$')"
readonly -a FILES

echo "Running pyupgrade"
pyupgrade --py313-plus "${FILES[@]}"
echo "Running isort"
isort "${FILES[@]}"
echo "Running black"
black "${FILES[@]}"
echo "Running prettier"
prettier -w kitsunekko_tools/example_catalog/resources \
	kitsunekko_tools/example_catalog/tests \
	kitsunekko_tools/example_catalog/*.json \
	kitsunekko_tools/example_catalog/*.js
