#!/usr/bin/env bash
# Regenerate generators/lemming/vendor/ from an existing rdfbench-lemming image.
#
# You do NOT need this to build the image: vendor/ is committed, so a clone
# already has the jar and `docker compose build lemming` works offline. This
# script exists for the case where the jar must be rebuilt -- an upstream
# change, or maven.aksw.org coming back (it has been offline since 2026, see
# BUILD_ISSUE.txt) -- and you want to refresh what is committed:
#
#     docker build --build-arg LEMMING_JAR_SOURCE=source \
#         -f generators/lemming/Dockerfile -t rdfbench-lemming:latest .
#     ./generators/lemming/export-vendor.sh
#     git add generators/lemming/vendor && git commit
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
