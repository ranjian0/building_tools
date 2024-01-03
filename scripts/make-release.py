#!/usr/bin/python3
#
# Generate an addon release archive. For repeatability, the timestamp
# and contents for each file are taken from the last commit affecting
# that file.
#
# This script takes an arg identifying a specific commit (e.g. a tag)
# from which to generate the archive. For example, the command
#
#     ./make-dist v1.0
#
# will make an archive for the commit tagged “v1.0” (assuming it exists).
# This tag name will also be included in the created archive name.

import os
import sys
import time
import zipfile
import pathlib
import subprocess

REPO_FILES = (
    "btools/",
    "__init__.py",
    "addon_updater.py",
    "addon_updater_ops.py",
    "LICENSE",
    "README.md",
    "CHANGELOG.md"
)


def git(*args):
    # convenience routine for simplifying git command calls.
    return subprocess.check_output(("git",) + args)


def main() -> None:
    upto = git("tag", "-l", "--sort=-creatordate").split(b"\n")[0].strip().decode()
    if not upto:
        print("Git repository has no tags, please create one!")
        return
    
    if len(sys.argv) > 1:
        # if the user specifies a tag, use that
        upto = sys.argv[-1]

    if upto == "latest":
        # if the user specifies "latest", use the latest commit
        upto = git("rev-list", "--all").split(b"\n")[0].strip().decode()    

    earliest = git("rev-list", "--reverse", upto).split(b"\n")[0].strip().decode()

    basename = "building_tools"
    outfilename = "%s_%s.zip" % (basename, upto if len(upto) < 10 else 'latest')
    if pathlib.Path(outfilename).exists():
        os.remove(outfilename)    
    out = zipfile.ZipFile(outfilename, "x")
    for item in REPO_FILES:
        if item.endswith("/"):
            items = sorted(
                set(
                    line.rsplit("\t", 1)[1]
                    for line in git("log", "--raw", item).decode().split("\n")
                    if line.startswith(":")
                )
            )
        else:
            items = (item,)

        for filename in items:
            info = git("log", "--format=%ct:%H", "-n1", "%s..%s" % (earliest, upto), "--", filename).strip()

            if info != b"":
                item = zipfile.ZipInfo()
                item.filename = basename + "/" + filename
                item.external_attr = 0o100644 << 16
                item.compress_type = zipfile.ZIP_DEFLATED
                timestamp, commit_hash = info.split(b":")
                timestamp = int(timestamp)
                info = git("ls-tree", commit_hash, filename).strip()

            if info != b"":
                object_hash = info.split(b"\t")[0].split(b" ")[2].decode()
                object_contents = git("show", object_hash)
                item.date_time = time.gmtime(timestamp)[:6]
                out.writestr(item, object_contents)

    out.close()

    sys.stdout.write("created archive: %s\n" % outfilename)

if __name__ == "__main__":
    main()