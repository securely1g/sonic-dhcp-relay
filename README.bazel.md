# Experimental Bazel DHCP relay source build

This opt-in build owns DHCP4 and DHCP6 daemons, runtime/debug TARs, and focused
and original-suite tests. Existing production sources, Make/package entry points,
and gitlink revisions are retained. It does not produce DEBs or assemble an image.

## Portable dependency contract

Use Bazel 8.5.1 and the canonical registry/BCR endpoints in `.bazelrc`.
`MODULE.bazel` requires published Common `.9-334389...` (including its published
YANG runtime overlay), infra `.39-8147619...`, distroless `.21`, and libyang `.6`.
There are no sibling-checkout overrides and no unused DHCP monitor dependency.
The old experimental Common/infra linker-metadata adapter is deliberately not
included: current distroless rewrites imported GNU linker scripts. This does not
establish that every current shared-link/runtime boundary has passed validation.

The published native `pcapplusplus@24.9.0.sonic.1` target builds the existing
PcapPlusPlus v24.09 sources with SONiC's random-source-port patch. The relay and
packet tests depend on its public `@pcapplusplus//:Pcap++` target. This removes
the nested CMake producer and root-only parser-generator overrides.
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
No APT versions/checksums are hand-edited: the published shared lock and its
request/source freshness checks remain required during configured analysis.
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

### Shared APT lock checks

The build and metadata targets consume the published `dhcpmon_debian`,
`dhcp_relay_test_debian` and `trixie` collections from
`@sonic_build_infra//apt:apt.lock.json`. The same import binds the owner's
`apt/requests.json` and `apt/sources.json`; missing or stale requests fail during
configured analysis before any source action runs. No component-private lock or
fresh network resolution is needed during normal builds.

Source CI starts with a new Bazel output root, generates `MODULE.bazel.lock` as
ignored evidence, analyzes all six runtime/debug/metadata outputs and all four
runtime tests, and rejects DEB-producing actions before execution. The original
full suites and their loader-closure checks remain required. `git diff
--exit-code` verifies that validation did not change tracked inputs.

## Validation scope

The source gate covers native AMD64/Trixie runtime/debug TARs, metadata and the
complete declared test suites. ARM, live forwarding and installed-image checks
require separate evidence; the source gate does not build a complete image.

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
target platforms, checks the imported APT requests/sources against the shared lock,
audits the configured transitive graph for DEB producers before execution,
builds both runtime/debug TARs and both metadata targets, then executes all four
runtime test targets with `--nocache_test_results`. Focused adapters execute the
unchanged owner sender/classifier binaries with the same declared loader and
capability-free, network-disabled, read-only Docker runtime as the original
suites. XML must show at least 3/2/62/47 completed cases respectively, no skips
or disabled cases; additions are allowed, silent coverage loss is not.

CPU/action concurrency is bounded to two jobs and an 8 GiB scheduling budget. The artifact includes selected output files and
checksums, source commit/tree, tool/config hashes, fresh resolution lock, module
graph, configured actions, BEP and JUnit/test logs, including available failure
receipts. No caches or environment/credential dumps are uploaded. An actual
hosted pass (or an explicit maintainer fork-run approval) remains necessary;
local command-equivalent validation alone is not a hosted-green claim. This
workflow makes no ARM, default-host, native global-install bootstrap, image,
or live-forwarding claim.
