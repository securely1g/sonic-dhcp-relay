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
never use wildcard builds/tests without inspecting them. Successful configured-graph
validation requires the owner-supported execution host platform
`--host_platform=@sonic_build_infra//platforms:x86_64_trixie`, in addition to the
target platform in `.bazelrc`. The default-host libyang execution-configuration
selector failure remains unresolved; these results do not establish default-host
success. Use this flag for configured queries, builds, and tests, as below:

```sh
bazel mod graph
bazel cquery --host_platform=@sonic_build_infra//platforms:x86_64_trixie 'set(//dhcp6relay:sender_test //dhcp4relay:pcap_patch_test //dhcp4relay:runtime //dhcp6relay:runtime)' --output=files
bazel aquery --host_platform=@sonic_build_infra//platforms:x86_64_trixie 'deps(set(//dhcp6relay:sender_test //dhcp4relay:pcap_patch_test //dhcp4relay:runtime //dhcp6relay:runtime))' --output=jsonproto
bazel test --host_platform=@sonic_build_infra//platforms:x86_64_trixie --jobs=4 --local_resources=memory=8192 --nocache_test_results \
  //dhcp6relay:sender_test //dhcp4relay:pcap_patch_test
bazel build --host_platform=@sonic_build_infra//platforms:x86_64_trixie --jobs=4 --local_resources=memory=8192 \
  //dhcp4relay:runtime //dhcp4relay:runtime.debug_symbols \
  //dhcp6relay:runtime //dhcp6relay:runtime.debug_symbols
```

The C++ tests target Debian trixie and must execute with the declared target
loader/libraries on a differing host. The full original suite runners
`//tests/runtime:v4_full_suite_test` and `:v6_full_suite_test` extract declared APT
and source TAR payloads and run in the digest-pinned Debian container without
network, capabilities, privilege, or writable source mounts. Docker is an explicit
local test prerequisite. Both runners first ask the target loader for its complete
transitive dependency list for the relay ELF and reject missing libraries or
successful fallback to container libraries outside `/rootfs`. This preflight does
not audit Python/Redis ELF closure or modules loaded later with `dlopen`; those
remain additional runtime-acceptance checks. The declared closure includes Common's
source-built libnl core/route/nf TARs and libyang's owner-selected PCRE2/xxhash APT
payload aliases; it does not change Common to static linkage. Boost thread/system
payloads use the same already-declared development-package closure as compilation.
No APT versions/checksums are hand-edited: the fresh-resolution gate below remains
required, including libyang's `libyang_system` dependency set in its new receipt.
`:v4_negative_control_test` is manual and expected to fail.

The loader-output gate has bounded, Docker-free positive/missing/ambient controls:

```sh
python3 -m unittest discover -s tests/runtime -p '*_test.py' -v
```

These controls are not ELF execution. Native acceptance must additionally omit
one measured `DT_NEEDED` provider from a fresh extracted runtime and observe a
loader/preflight failure, then restore it and rerun both complete suites.
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
consumed by the facts-mode resolver. It was refreshed byte-for-byte from successful
authoritative resolution of this dependency graph (1122 packages, including
`libnl_system` and `libyang_system`). Retain a fresh comparison receipt for the
configured graph; the frozen contract alone is not fresh-resolution evidence. Run:

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

## Source PR CI (AMD64)

`.github/workflows/bazel.yml` runs for every PR, without path/Draft filters,
checking out the actual head with a read-only token and no persisted credentials.
It uses Ubuntu 24.04 AMD64, Python 3.12.3, checksummed Bazel 8.5.1 and the existing
digest-pinned trixie test runtime. No secrets, shared caches, self-hosted runner,
`pull_request_target`, new package generation, or repository-settings changes
are required. CodeQL and Semgrep remain independent and unchanged.

`tools/bazel/ci.sh` is the reproducible entry point. Set `BAZEL` to the verified
binary, `CI_SOURCE_SHA` to `git rev-parse HEAD`, and `CI_STATE`/`CI_EVIDENCE` to new
absolute directories. It explicitly selects the supported trixie host **and**
target platforms, resolves/compares the APT contract afresh (never rewrites it),
audits the configured transitive graph for DEB producers before execution,
builds both runtime/debug TARs and both metadata targets, then executes all four
runtime test targets with `--nocache_test_results`. Focused adapters execute the
unchanged owner sender/classifier binaries with the same declared loader and
capability-free, network-disabled, read-only Docker runtime as the original
suites. XML must show at least 3/2/62/47 completed cases respectively, no skips
or disabled cases; additions are allowed, silent coverage loss is not.

CPU/action concurrency is bounded to two jobs, an 8 GiB scheduling budget and
serial nested foreign builds. The artifact includes selected output files and
checksums, source commit/tree, tool/config hashes, fresh resolution lock, module
graph, configured actions, BEP and JUnit/test logs, including available failure
receipts. No caches or environment/credential dumps are uploaded. An actual
hosted pass (or an explicit maintainer fork-run approval) remains necessary;
local command-equivalent validation alone is not a hosted-green claim. This
workflow makes no ARM, default-host, native global-install bootstrap, image,
or live-forwarding claim.
