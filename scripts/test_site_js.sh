#!/bin/bash

set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)" || exit 1
readonly ROOT_DIR

die() {
	echo "oops: $*"
	exit 1
}

main() {
	cd -- "$ROOT_DIR/kitsunekko_tools/example_catalog" || die "can't CD to example catalog"
	pnpm test
	echo "Done."
}

main "$@"
