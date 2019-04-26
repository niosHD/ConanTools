from subprocess import run, PIPE, DEVNULL
from typing import Optional


def revision(cwd: Optional[str] = None) -> Optional[str]:
    res = run(["git", "rev-parse", "HEAD"],
              stdin=DEVNULL, stdout=PIPE, stderr=DEVNULL, universal_newlines=True, cwd=cwd)
    if res.returncode == 0:
        return res.stdout.strip()
    return None


def branch(cwd: Optional[str] = None) -> Optional[str]:
    current_sha = revision(cwd=cwd)
    # Get a list of all refs and their SHAs.
    refs = run(["git", "for-each-ref", "--format=%(objectname) %(refname:short)", "refs/heads"],
               stdin=DEVNULL, stdout=PIPE, stderr=DEVNULL, universal_newlines=True, cwd=cwd,
               check=True).stdout.strip()
    if refs == "":
        return None
    refs = [line.split(' ', 1) for line in refs.replace('\r', '').split('\n')]
    # Return the first ref where the revisions match.
    for sha, name in refs:
        if sha == current_sha:
            return name
    return None


def describe(cwd: Optional[str] = None) -> Optional[str]:
    res = run(["git", "describe", "--tags", "--abbrev=40", "--always"],
              stdin=DEVNULL, stdout=PIPE, stderr=DEVNULL, universal_newlines=True, cwd=cwd)
    if res.returncode == 0:
        return res.stdout.strip()
    return None


def is_repository(cwd: Optional[str] = None) -> bool:
    return run(["git", "status"],
               stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL, cwd=cwd).returncode == 0


def tag(cwd: Optional[str] = None) -> Optional[str]:
    res = run(["git", "describe", "--exact-match", "--tags"],
              stdin=DEVNULL, stdout=PIPE, stderr=DEVNULL, universal_newlines=True, cwd=cwd)
    if res.returncode == 0:
        return res.stdout.strip()
    return None
