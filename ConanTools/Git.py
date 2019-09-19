from subprocess import run, PIPE, DEVNULL
from typing import List, Optional


def revision(cwd: Optional[str] = None) -> Optional[str]:
    res = run(["git", "rev-parse", "HEAD"],
              stdin=DEVNULL, stdout=PIPE, stderr=DEVNULL, universal_newlines=True, cwd=cwd)
    if res.returncode == 0:
        return res.stdout.strip()
    return None


def branches(rev: Optional[str] = None, cwd: Optional[str] = None) -> List[str]:
    current_sha = rev or revision(cwd=cwd)
    # Get a list of all heads and their SHAs.
    refs = run(["git", "for-each-ref", "--format=%(objectname) %(refname:short)", "refs/heads"],
               stdin=DEVNULL, stdout=PIPE, stderr=DEVNULL, universal_newlines=True, cwd=cwd,
               check=True).stdout.strip()
    # Fallback to remote refs if no heads exist.
    if refs == "":
        refs = run(["git", "for-each-ref", "--format=%(objectname) %(refname:lstrip=3)",
                    "refs/remotes"],
                   stdin=DEVNULL, stdout=PIPE, stderr=DEVNULL, universal_newlines=True, cwd=cwd,
                   check=True).stdout.strip()
    if refs == "":
        return None
    refs = [line.split(' ', 1) for line in refs.replace('\r', '').split('\n')]
    return [name for sha, name in refs if sha == current_sha]


def branch(cwd: Optional[str] = None) -> Optional[str]:
    res = branches(cwd=cwd)
    if res:
        return res[0]
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
