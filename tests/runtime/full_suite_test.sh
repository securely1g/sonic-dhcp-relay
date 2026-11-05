#!/usr/bin/env bash
# Linux AMD64 local integration test; Docker daemon required, no privileged mode.
set -euo pipefail
export RUNFILES_DIR="${RUNFILES_DIR:-$0.runfiles}"
cd "${TEST_SRCDIR}/${TEST_WORKSPACE}"
work="${TEST_TMPDIR}/v6"
mkdir -p "$work/root" "$work/tests"
# All tar inputs are Bazel-declared data; never copy host libraries.
while IFS= read -r archive; do
  tar -xf "$archive" -C "$work/root" --no-same-owner
 done < "$1"
cp "$2" "$work/tests/relay_test"
cp "$3" "$work/tests/run_tests.py"
cp "$4" "$work/tests/database_config.json"
cat > "$work/tests/redis-server" <<'SH'
#!/bin/sh
exec /rootfs/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 --library-path /rootfs/usr/lib/x86_64-linux-gnu /rootfs/usr/bin/redis-server "$@"
SH
chmod 755 "$work/tests/redis-server"
chmod -R a+rX "$work"
set +e
docker run --rm --network none --read-only --user 65534:65534 --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:rw,nosuid,nodev,size=128m -e PYTHONHOME=/rootfs/usr -v "$work/root:/rootfs:ro" -v "$work/tests:/tests:ro" debian:trixie-20260918@sha256:9cc080028c43b27d2074d63a5f9caf7166d731494965616c1a6d2827a004585c /bin/sh -c '
/rootfs/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 --library-path /rootfs/usr/lib/x86_64-linux-gnu /rootfs/usr/bin/python3 /tests/run_tests.py --redis-server /tests/redis-server -- /rootfs/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 --library-path /rootfs/usr/lib/x86_64-linux-gnu /tests/relay_test --gtest_output=xml:/tmp/v6.xml
rc=$?
if test -f /tmp/v6.xml; then echo JUNIT_BEGIN; cat /tmp/v6.xml; echo JUNIT_END; fi
exit "$rc"
' > "$work/output.log" 2>&1
rc=$?
set -e
cat "$work/output.log"
sed -n '/^JUNIT_BEGIN$/,/^JUNIT_END$/{ /^JUNIT_BEGIN$/d; /^JUNIT_END$/d; p; }' "$work/output.log" > "${XML_OUTPUT_FILE}"
test -s "${XML_OUTPUT_FILE}"
exit "$rc"
