`make test` starts a private Redis process for the DHCPv6 tests, waits for its
UNIX socket to answer, and removes that process and its temporary data afterward.
It does not need a system Redis service. Install the declared `python3` and
`redis-server` build-test dependencies; `REDIS_SERVER=/absolute/path/to/redis-server`
can select an existing executable. The GoogleTests still run through `sudo`
because some tests need raw sockets.

Coverage reports are generated even when GoogleTests fail, and either test or
coverage failures make the target fail. The Debian package build therefore
cannot report success after failing tests.

The fixture supplies `DHCP6RELAY_TEST_DATABASE_CONFIG` to the test process. Running
the test binary directly without that variable retains the existing
`./test/database_config.json` behavior.

Run the fixture and Make-status regressions from the repository root:

```sh
python3 -m unittest discover -s dhcp6relay/test -p run_tests_test.py -v
```
