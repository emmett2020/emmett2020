#!/usr/bin/env python3
"""Software Watch.

Fetch the latest version of each tracked tool, diff it against the saved
state, then render two artifacts:

  * changes.md   - only written when a tracked tool released a new version
  * dashboard.md - always written; the living "current state" board

Uses only the Python standard library (urllib) so it runs on the GitHub
Actions runner with no pip install. Individual source failures are isolated:
a tool that can't be fetched keeps its last known version and is flagged,
the run still completes.
"""

import json
import os
import re
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(HERE, "state.json")

# changes.md / dashboard.md are transient build artifacts. By default write
# them next to this script, but the workflow points OUTPUT_DIR at a temp dir
# so they never land in the repo.
OUT_DIR = os.environ.get("OUTPUT_DIR", HERE)
CHANGES_PATH = os.path.join(OUT_DIR, "changes.md")
DASHBOARD_PATH = os.path.join(OUT_DIR, "dashboard.md")

GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")
UA = "emmett2020-software-watch"


# --------------------------------------------------------------------------
# HTTP helpers
# --------------------------------------------------------------------------
def _get_text(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def get_json(url, headers=None):
    return json.loads(_get_text(url, headers))


def gh_json(path):
    headers = {"Accept": "application/vnd.github+json"}
    if GH_TOKEN:
        headers["Authorization"] = f"Bearer {GH_TOKEN}"
    return get_json(f"https://api.github.com{path}", headers)


def gh_latest_release(repo):
    """Latest non-prerelease release tag of a GitHub repo, 'v' stripped."""
    return gh_json(f"/repos/{repo}/releases/latest")["tag_name"].lstrip("v")


def version_key(v):
    return tuple(int(x) for x in re.findall(r"\d+", v))


# --------------------------------------------------------------------------
# Per-tool fetchers
# --------------------------------------------------------------------------
def src_llvm():
    tag = gh_json("/repos/llvm/llvm-project/releases/latest")["tag_name"]
    return tag.replace("llvmorg-", "")


def src_gcc():
    tags = gh_json("/repos/gcc-mirror/gcc/tags?per_page=100")
    versions = [
        m.group(1)
        for t in tags
        if (m := re.match(r"releases/gcc-(\d+\.\d+\.\d+)$", t["name"]))
    ]
    return max(versions, key=version_key)


def src_cmake():
    return gh_latest_release("Kitware/CMake")


def src_ninja():
    return gh_latest_release("ninja-build/ninja")


def src_vcpkg():
    return gh_latest_release("microsoft/vcpkg")


def src_conan():
    return gh_latest_release("conan-io/conan")


def src_ubuntu():
    cycle = get_json("https://endoflife.date/api/ubuntu.json")[0]
    return cycle.get("latest") or cycle.get("cycle")


def src_linux():
    return get_json("https://www.kernel.org/releases.json")["latest_stable"]["version"]


def src_python():
    cycle = get_json("https://endoflife.date/api/python.json")[0]
    return cycle.get("latest") or cycle.get("cycle")


def src_pytorch():
    return gh_latest_release("pytorch/pytorch")


def src_vllm():
    return gh_latest_release("vllm-project/vllm")


# key, display name, fetcher
SOURCES = [
    ("llvm", "LLVM / Clangd", src_llvm),
    ("gcc", "GCC", src_gcc),
    ("cmake", "CMake", src_cmake),
    ("ninja", "Ninja", src_ninja),
    ("vcpkg", "vcpkg", src_vcpkg),
    ("conan", "Conan", src_conan),
    ("ubuntu", "Ubuntu", src_ubuntu),
    ("linux", "Linux Kernel", src_linux),
    ("python", "Python", src_python),
    ("pytorch", "PyTorch", src_pytorch),
    ("vllm", "vLLM", src_vllm),
]


def main():
    state = {}
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            state = json.load(f)
    first_run = not state

    results = {}      # key -> {name, version, error}
    changes = []      # (name, old, new)

    for key, name, fetch in SOURCES:
        old = state.get(key)
        try:
            new = fetch()
        except Exception as exc:  # isolate per-source failures
            results[key] = {"name": name, "version": old, "error": str(exc)}
            continue
        results[key] = {"name": name, "version": new, "error": None}
        if old and new and old != new:
            changes.append((name, old, new))
        if new:
            state[key] = new

    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Dashboard (mode B) - always refreshed.
    lines = [
        "# 📊 Software Watch Dashboard",
        "",
        f"_Last checked: {now}_",
        "",
        "| Tool | Latest version |",
        "| --- | --- |",
    ]
    for key, name, _ in SOURCES:
        r = results[key]
        version = r["version"] or "—"
        if r["error"]:
            version = f"{version} ⚠️"
        lines.append(f"| {name} | `{version}` |")
    lines += ["", "<!-- software-watch-dashboard -->"]
    with open(DASHBOARD_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")

    # Change report (mode A) - only on real changes, never on the seeding run.
    has_changes = bool(changes) and not first_run
    if has_changes:
        cl = ["The following tracked software released new versions:", ""]
        for name, old, new in changes:
            cl.append(f"- **{name}**: `{old}` → `{new}`")
        cl += ["", f"_Detected: {now}_"]
        with open(CHANGES_PATH, "w") as f:
            f.write("\n".join(cl) + "\n")

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write(f"has_changes={'true' if has_changes else 'false'}\n")

    print(f"first_run={first_run} has_changes={has_changes} changes={changes}")


if __name__ == "__main__":
    main()
