# Experimental Bazel DHCP relay source build

This opt-in build owns DHCP4 and DHCP6 daemons, runtime/debug TARs, and focused
and original-suite tests. Existing production sources, Make/package entry points,
and gitlink revisions are retained. It does not produce DEBs or assemble an image.

## Portable dependency contract

Use Bazel 8.5.1 and the canonical registry/BCR endpoints in `.bazelrc`.
`MODULE.bazel` requires published Common `.9-334389...` (including its published
YANG runtime overlay), infra `.26-51c838...`, distroless `.16`, and libyang `.6`.
There are no sibling-checkout overrides and no unused DHCP monitor dependency.
The old experimental Common/infra linker-metadata adapter is deliberately not
included: current distroless rewrites imported GNU linker scripts. This does not
establish that every current shared-link/runtime boundary has passed validation.

PcapPlusPlus v24.09 is built from its checksummed source archive using upstream
CMake and the existing SONiC random-source-port patch. BCR libpcap `.bcr.4` and
m4/bison/flex wrapper-header patches preserve gnulib header ordering under the
selected GCC toolchain. These `single_version_override` patches are **root-only**:
a downstream root must repeat the same parser-generator selections/patches until
a reviewed registry/BCR solution replaces them. Do not silently drop them when
registering this module. The patches do not substitute prebuilt project binaries.
The header-only gmock-global test dependency uses a verified immutable source
archive at the exact existing gitlink commit `6552faa2a94250ed0192dbd62e608d37fafcc216`.
This avoids requiring submodule contents omitted by GitHub source archives;
the legacy gitlink is unchanged.

## Bounded validation

Inspect configured outputs/actions before builds, including transitive edges;
never use wildcard builds/tests without inspecting them. Example explicit targets:

```sh
bazel mod graph
bazel cquery 'set(//dhcp6relay:sender_test //dhcp4relay:pcap_patch_test //dhcp4relay:runtime //dhcp6relay:runtime)' --output=files
bazel aquery 'deps(set(//dhcp6relay:sender_test //dhcp4relay:pcap_patch_test //dhcp4relay:runtime //dhcp6relay:runtime))' --output=jsonproto
bazel test --jobs=4 --local_resources=memory=8192 --nocache_test_results \
  //dhcp6relay:sender_test //dhcp4relay:pcap_patch_test
bazel build --jobs=4 --local_resources=memory=8192 \
  //dhcp4relay:runtime //dhcp4relay:runtime.debug_symbols \
  //dhcp6relay:runtime //dhcp6relay:runtime.debug_symbols
```

The C++ tests target Debian trixie and must execute with the declared target
loader/libraries on a differing host. The full original suite runners
`//tests/runtime:v4_full_suite_test` and `:v6_full_suite_test` extract declared APT
and source TAR payloads and run in the digest-pinned Debian container without
network, capabilities, privilege, or writable source mounts. Docker is an explicit
local test prerequisite. `:v4_negative_control_test` is manual and expected to fail.
The test-only seams remove raw-socket privilege requirements without replacing
production source; kernel BPF checks remain real. These are unit-suite checks,
not live forwarding or full dual-ToR acceptance.

### Private Redis prerequisite and attribution

The fixture, environment-selected database configuration, dual-ToR scope guard,
and README/regression tests are carried from Guohan Lu's existing
[PR #1](https://github.com/securely1g/sonic-dhcp-relay/pull/1), head
`fda21ae4a5d5aee9aee0968774c0c708c46b4df1`. Its Make-status propagation and Python/
Redis test build dependencies are also retained so all four fixture regression
tests have a coherent contract. The source commit credits that original author.
The separate PR's Azure service/fixture changes are not duplicated here. If PR #1
lands first, rebase and retain only the remaining Bazel/test-seam delta.

```sh
python3 -m unittest discover -s dhcp6relay/test -p run_tests_test.py -v
```

This suite needs an existing Redis executable (`REDIS_SERVER` may select a
loader wrapper). It creates only private temporary sockets/configuration and
verifies cleanup, failure propagation, and fresh state; it produces no DEBs.

### Fresh APT acceptance gate

`apt.lock.json` is the frozen reviewed **acceptance contract**, not an input
consumed by the facts-mode resolver. It has not been refreshed for this updated
dependency graph. Before claiming current graph acceptance, run:

```sh
python3 tools/bazel/validate-apt-lock.py --evidence-dir <new-receipt-dir> -- <configured-bazel-launcher>
```

The launcher must accept `mod deps --lockfile_mode=update`. The gate preserves
any previous generated lock, forces new resolution, and fails on resolver failure
or package/source/dependency-set drift. Review the successful fresh result before
updating the canonical contract; do not copy old resolution state as new evidence.
The imported `bazel_metadata/apt.lock.json` separately pins metadata payload inputs.

## Current readiness limits

This is a Draft source candidate, not an integration/release claim. The earlier
November 1 frozen candidate's tests do not establish this graph's results. Fresh
private-Redis/Make tests and static checks are recorded in publication evidence;
C++/runtime validation can remain blocked by pinned snapshot retrieval. AMD64
current-graph source builds, matched symbols, full suites, installed image closure,
ARM, live forwarding, and a complete legacy image build require separate receipts.
No infrastructure adapter, Common PR45 duplicate, platform-common migration,
monitor source, registry publication, or automatic CI policy change belongs here.
