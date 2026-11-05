"""Declared runtime archive manifest for the nonprivileged local v6 test."""
def _manifest_impl(ctx):
    archives = depset(transitive = [dep[DefaultInfo].files for dep in ctx.attr.archives])
    output = ctx.actions.declare_file(ctx.label.name + ".txt")
    ctx.actions.write(output, "\n".join([file.short_path for file in archives.to_list()]) + "\n")
    return [DefaultInfo(files = depset([output]), runfiles = ctx.runfiles(transitive_files = archives))]

runtime_manifest = rule(
    implementation = _manifest_impl,
    attrs = {"archives": attr.label_list(allow_files = True)},
)
