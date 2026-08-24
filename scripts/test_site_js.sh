#!/bin/bash

set -euo pipefail

readonly ROOT_DIR=$(git rev-parse --show-toplevel)

die() {
	echo "oops: $*"
	exit 1
}

main() {
	cd -- "$ROOT_DIR/kitsunekko_tools/example_catalog" || die "can't CD to example catalog"
	pnpm run test:site-js
        pnpm run coverage:site-js
	echo "Done."
}

main "$@"
