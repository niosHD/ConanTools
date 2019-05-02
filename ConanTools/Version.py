# Single source of truth regarding the package version.
import os
from ConanTools import Git


# The following version string denotes the version that is either currently
# developed or the actual version in case of a release.
__version_string__ = '0.2.0'
__version_file_dir__ = os.path.dirname(os.path.abspath(__file__))


def is_release(cwd: str = None) -> bool:
    """Returns True if the folder is a git repository and on a tag or not a git repository at all.
    """
    if not Git.is_repository(cwd):
        return True
    if Git.tag(cwd) is not None:
        return True
    return False


def _format_git_version(default: str, cwd: str, digits: int,
                        mod_sep: str, metadata_sep: str) -> str:
    if is_release(cwd):
        return default
    desc_str = Git.describe(cwd)
    parts = desc_str.split("-")
    if len(parts) == 1:
        # only relevant when no tag was found and only the SHA has been returned
        parts = [default, "dev0", "g" + desc_str]
    else:
        parts[1] = "post" + parts[1]
    res = parts[0] + mod_sep + parts[1]
    if digits == 0:
        return res
    return res + metadata_sep + parts[2][0:digits + 1]


# https://www.python.org/dev/peps/pep-0440
def pep440(default: str = __version_string__,
           cwd: str = __version_file_dir__, digits: int = 10) -> str:
    """Returns the default version string when building a tag or when
    no git repository has been found. Otherwise the git describe output,
    formatted according to PEP440, is returned as version string.
    """
    return _format_git_version(default, cwd, digits, ".", "+")


# https://semver.org/spec/v2.0.0.html
def semantic(default: str = __version_string__,
             cwd: str = __version_file_dir__, digits: int = 10) -> str:
    """Returns the default version string when building a tag or when
    no git repository has been found. Otherwise the git describe output,
    formatted according to semantic versioning, is returned as version string.
    """
    return _format_git_version(default, cwd, digits, "-", "+")
