"""Check independently resolved relay SDK roots and their full package closure."""
import json


def resolved_graph(module_lock):
    extensions = module_lock["moduleExtensions"]
    audit = next(value for name, value in extensions.items()
                 if name.endswith("//bazel_metadata:audit_apt.bzl%apt"))
    return json.loads(audit["general"]["generatedRepoSpecs"]["trixie"]["attributes"]["lock_content"])


def compare(expected, actual):
    for field in ("sources", "dependency_sets", "packages"):
        if expected[field] != actual[field]:
            raise ValueError("APT selection drift in " + field)
