import os
import shlex
import string
import subprocess as sp
import sys
from typing import Optional


# TODO make this helper more similar to subprocess.run
def run(args, cwd=None, stdout=None, stderr=None, ignore_returncode=False):
    cwd = os.path.abspath(cwd if cwd is not None else os.getcwd())
    os.makedirs(cwd, exist_ok=True)
    print("[%s] $ %s" % (cwd, " ".join([shlex.quote(x) for x in args])))
    sys.stdout.flush()
    result = sp.run(args, stdout=stdout, stderr=stderr, cwd=cwd)
    if stdout == sp.PIPE:
        result.stdout = result.stdout.decode().strip()
    if stderr == sp.PIPE:
        result.stderr = result.stderr.decode().strip()
    if ignore_returncode is False and result.returncode != 0:
        if stdout == sp.PIPE:
            print(result.stdout, file=sys.stdout)
        if stderr == sp.PIPE:
            print(result.stderr, file=sys.stderr)
        raise ValueError(
            "Executing command \"%s\" failed! (returncode=%d)" %
            (" ".join(args), result.returncode))
    return result


# https://docs.gitlab.com/ee/ci/variables/predefined_variables.html
def slug(input: Optional[str]) -> Optional[str]:
    if input is None:
        return None
    whitelist = set(string.ascii_letters + string.digits)

    def sanitize_char(ch):
        if ch in whitelist:
            return ch.lower()
        return '-'

    return ''.join([sanitize_char(ch) for ch in input]).strip('-')
