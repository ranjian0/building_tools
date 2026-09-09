"""Blender-side driver for the bt session.

Runs inside Blender (GUI or -b). Registers a persistent app timer that polls a
session directory for request files and executes them:

    cmd-<id>.py   python code to exec
    req-<id>      marker file (creation order defines execution order)
    resp-<id>     written back: "EXIT:<n>\n" followed by captured output
    ack-<id>      written when the request is picked up (optional progress hint)

Also installs the session hotkeys-free utilities used by `bt`:
    - BT_SESSION_INFO dict with blender/python versions
"""

import contextlib
import glob
import io
import os
import sys
import time
import traceback

import bpy

SESSION_DIR = os.environ.get(
    "BT_SESSION_DIR", os.path.join(os.path.dirname(__file__), "..", "out", "session")
)
SESSION_DIR = os.path.abspath(SESSION_DIR)
POLL_INTERVAL = 0.05


def _process_requests():
    try:
        for req in sorted(
            glob.glob(os.path.join(SESSION_DIR, "req-*")), key=os.path.getmtime
        ):
            rid = os.path.basename(req)[len("req-") :]
            cmd_path = os.path.join(SESSION_DIR, "cmd-%s.py" % rid)
            resp_path = os.path.join(SESSION_DIR, "resp-%s" % rid)

            with open(req, "w") as f:  # touch: ack pickup
                f.write("picked-up")

            code = ""
            if os.path.exists(cmd_path):
                with open(cmd_path) as f:
                    code = f.read()

            buf = io.StringIO()
            status = 0
            started = time.time()
            glbl = {
                "__name__": "__main__",
                "__file__": cmd_path,
                "print": _tied_print(buf),
                # -- commonly used modules, ready in every exec/eval
                "bpy": bpy,
                "bmesh": __import__("bmesh"),
                "mathutils": __import__("mathutils"),
                "sys": sys,
                "os": os,
                "time": time,
            }
            try:
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                    exec(compile(code, cmd_path, "exec"), glbl)
            except Exception:
                status = 1
                buf.write(traceback.format_exc())

            duration = time.time() - started
            with open(resp_path, "w") as f:
                f.write("EXIT:%d DURATION:%.3f\n" % (status, duration))
                f.write(buf.getvalue())

            for stale in (req, cmd_path):
                try:
                    os.remove(stale)
                except OSError:
                    pass
    except Exception:
        # never let the polling loop die
        traceback.print_exc()
    return POLL_INTERVAL


def _tied_print(buf):
    def print_(*args, **kwargs):
        kwargs.pop("file", None)
        kwargs.pop("flush", None)
        buf.write(" ".join(str(a) for a in args) + "\n")

    return print_


def _install():
    os.makedirs(SESSION_DIR, exist_ok=True)

    # -- write session info for `bt status`
    info_path = os.path.join(SESSION_DIR, "info")
    with open(info_path, "w") as f:
        f.write(
            "blender:%s\npython:%d.%d.%d\ndriver:%s\npid:%d\nstarted:%s\n"
            % (
                bpy.app.version_string,
                sys.version_info.major,
                sys.version_info.minor,
                sys.version_info.micro,
                __file__,
                os.getpid(),
                time.strftime("%Y-%m-%d %H:%M:%S"),
            )
        )

    # -- marker that the driver is ready to take requests
    with open(os.path.join(SESSION_DIR, "ready"), "w") as f:
        f.write("ready")

    # -- clear stale requests from a previous session
    for stale in glob.glob(os.path.join(SESSION_DIR, "req-*")) + glob.glob(
        os.path.join(SESSION_DIR, "resp-*")
    ):
        try:
            os.remove(stale)
        except OSError:
            pass

    bpy.app.timers.register(_process_requests, first_interval=0.5, persistent=True)
    print("[bt] driver installed, session dir:", SESSION_DIR)


_install()
