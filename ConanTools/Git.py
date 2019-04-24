from subprocess import run, PIPE, DEVNULL
import string


def get_branch(cwd=None):
    return run(["git", "rev-parse", "--abbrev-ref", "HEAD"], stdin=DEVNULL,
               stdout=PIPE, stderr=DEVNULL, universal_newlines=True, cwd=cwd,
               check=True).stdout.strip()


def describe(cwd=None):
    return run(["git", "describe", "--tags", "--abbrev=40", "--always"], stdin=DEVNULL,
               stdout=PIPE, stderr=DEVNULL, universal_newlines=True, cwd=cwd,
               check=True).stdout.strip()


def is_repo(cwd=None):
    return run(["git", "status"], stdin=DEVNULL, stdout=DEVNULL,
               stderr=DEVNULL, cwd=cwd).returncode == 0


def get_tag(cwd=None):
    return run(["git", "describe", "--exact-match", "--tags"],
               stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL, cwd=cwd).stdout.strip()


def slug(input):
    whitelist = set(string.ascii_letters + string.digits)

    def sanitize_char(ch):
        if ch in whitelist:
            return ch
        return '_'

    return ''.join([sanitize_char(ch) for ch in input])
