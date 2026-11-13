#!/usr/bin/env bash
# Run a focused owner test with the same declared runtime as the full suites.
set -euo pipefail
cd "${TEST_SRCDIR}/${TEST_WORKSPACE}"
work="${TEST_TMPDIR}/focused"
mkdir -p "$work/root" "$work/tests"
while IFS= read -r archive; do
  tar -xf "$archive" -C "$work/root" --no-same-owner
done < "$1"
cp "$2" "$work/tests/relay_test"
chmod -R a+rX "$work"
image=debian:trixie-20260918@sha256:9cc080028c43b27d2074d63a5f9caf7166d731494965616c1a6d2827a004585c
source tests/runtime/check_loader_closure.sh
check_loader_closure "$work/root" "$work/tests/relay_test" "$image"
set +e
docker run --rm --network none --read-only --user 65534:65534 \
  --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp:rw,nosuid,nodev,size=128m \
  -v "$work/root:/rootfs:ro" -v "$work/tests:/tests:ro" "$image" /bin/sh -c '
/rootfs/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 --library-path /rootfs/usr/lib/x86_64-linux-gnu /tests/relay_test --gtest_output=xml:/tmp/focused.xml
rc=$?
if test -f /tmp/focused.xml; then echo JUNIT_BEGIN; cat /tmp/focused.xml; echo JUNIT_END; fi
exit "$rc"
' > "$work/output.log" 2>&1
rc=$?
set -e
cat "$work/output.log"
sed -n '/^JUNIT_BEGIN$/,/^JUNIT_END$/{ /^JUNIT_BEGIN$/d; /^JUNIT_END$/d; p; }' "$work/output.log" > "${XML_OUTPUT_FILE}"
test -s "${XML_OUTPUT_FILE}"
exit "$rc"
