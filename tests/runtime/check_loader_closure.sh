#!/usr/bin/env bash
# Sourced by both installed-suite runners after extraction. The target loader
# must resolve every DT_NEEDED from declared archives, never the container base.
check_loader_closure() {
  local root="$1" binary="$2" image="$3" output rc
  set +e
  output=$(docker run --rm --network none --read-only --user 65534:65534 \
    --cap-drop ALL --security-opt no-new-privileges \
    -v "$root:/rootfs:ro" -v "$binary:/tests/relay_test:ro" \
    "$image" /rootfs/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 \
    --inhibit-cache --library-path /rootfs/usr/lib/x86_64-linux-gnu \
    --list /tests/relay_test 2>&1)
  rc=$?
  set -e
  printf '%s\n' "$output"
  if (( rc != 0 )); then
    echo "Declared runtime loader failed" >&2
    return 1
  fi
  # --library-path alone still permits default /lib and /usr/lib fallback.
  # Audit the loader's actual transitive resolution, allowing only the kernel
  # vDSO and the explicitly invoked loader outside => records.
  if ! printf '%s\n' "$output" | awk '
    /=>/ { if ($3 !~ /^\/rootfs\//) bad = 1; count++; next }
    $1 == "linux-vdso.so.1" && $2 ~ /^\(0x[0-9a-f]+\)$/ { next }
    $1 ~ /^\/rootfs\// && $2 ~ /^\(0x[0-9a-f]+\)$/ { next }
    NF { bad = 1 }
    END { exit (bad || !count) }
  '; then
    echo "Undeclared runtime library resolved outside /rootfs" >&2
    return 1
  fi
}
