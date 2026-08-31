#!/usr/bin/env bash
# Export the prebuilt LEMMING artefacts out of an existing rdfbench-lemming
# image into generators/lemming/vendor/, so the image can be rebuilt anywhere
# without reaching maven.aksw.org (which has been offline since 2026 -- see
# BUILD_ISSUE.txt).
#
# Run this on a machine that already has a working image, then copy the vendor
# directory to the machine that does not:
#
#     ./generators/lemming/export-vendor.sh
#     tar czf lemming-vendor.tar.gz -C generators/lemming vendor
#     scp lemming-vendor.tar.gz vm:/path/to/repo/
#     # on the VM:
#     tar xzf lemming-vendor.tar.gz -C generators/lemming
#     docker compose build lemming
#
set -euo pipefail

IMAGE="${1:-rdfbench-lemming:latest}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR="$HERE/vendor"

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "error: image '$IMAGE' not found locally." >&2
    echo "This script copies artefacts OUT of a working image; it cannot create one." >&2
    echo "Pass a different image as \$1, or obtain vendor/ from a machine that has it." >&2
    exit 1
fi

mkdir -p "$VENDOR"
cid="$(docker create "$IMAGE")"
trap 'docker rm -f "$cid" >/dev/null 2>&1 || true' EXIT

echo "extracting from $IMAGE ..."
docker cp "$cid:/app/target/lemming.jar" "$VENDOR/lemming.jar"
rm -rf "$VENDOR/testdata"
docker cp "$cid:/app/testdata" "$VENDOR/testdata"

( cd "$VENDOR" && sha256sum lemming.jar > lemming.jar.sha256 )

echo
echo "wrote:"
ls -lh "$VENDOR/lemming.jar"
du -sh "$VENDOR/testdata"
echo
echo "verify on the far side with:  (cd generators/lemming/vendor && sha256sum -c lemming.jar.sha256)"
