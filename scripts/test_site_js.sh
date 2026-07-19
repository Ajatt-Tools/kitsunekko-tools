#!/bin/bash

set -euo pipefail

die() {
	echo "oops: $*"
	exit 1
}

main() {
	[[ -d $PWD/.git ]] || die "started in a wrong directory: $PWD"
	cd kitsunekko_tools/example_catalog
	pnpm run check:site-js
	pnpm run test:site-js
        pnpm run coverage:site-js
	echo "Done."
}

main "$@"
