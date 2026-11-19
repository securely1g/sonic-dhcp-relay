"""Re-resolve relay dependencies independently for the standalone CI audit."""

load("@rules_distroless//apt:extensions.bzl", _apt = "apt")

apt = _apt
