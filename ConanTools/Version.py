"""Support module that permits to derive the version of the ConanTools package from git.

The idea of this module is to generate sane package versions also for non-release configurations
based on git describe. The overall approach is similar to packages like
`setuptools_scm <https://github.com/pypa/setuptools_scm>`_ and
`dunamai <https://github.com/mtkennerly/dunamai>`_. However, given that we want to distribute
ConanTools also as conan package, having external dependencies is not really appealing.
"""
import os
from ConanTools import Git
from typing import Optional


# The following version string is only relevant when the repository gets tagged, when the package
# is deployed (e.g., pypi), or before the first tag is created in the repository.
# -> Update it to the release version before cutting the release.
__version_string__ = '0.4.2'


def is_release(cwd: Optional[str] = None) -> bool:
    """Returns True if the folder is a git repository and on a tag or not a git repository at all.
    """
    if not Git.is_repository(cwd):
        return True
    if Git.tag(cwd) is not None:
        return True
    return False


def _format_git_version(fallback: str, cwd: Optional[str], digits: int,
                        mod_sep: str, metadata_sep: str) -> str:
    if cwd == "":
        cwd = os.path.dirname(os.path.abspath(__file__))
    if is_release(cwd):
        return fallback
    desc_str = Git.describe(cwd)
    parts = desc_str.split("-")
    if len(parts) == 1:
        # only relevant when no tag was found and only the SHA has been returned
        parts = [fallback, "dev0", "g" + desc_str]
    else:
        parts[1] = "post" + parts[1]
    res = parts[0] + mod_sep + parts[1]
    if digits == 0:
        return res
    return res + metadata_sep + parts[2][0:digits + 1]


# https://www.python.org/dev/peps/pep-0440
def pep440(fallback: str = __version_string__,
           cwd: Optional[str] = "", digits: int = 10) -> str:
    """Deduces the package version via git describe and returns it in PEP440 format.

    :param fallback: The version string that is returned when no git based version can be derived.
    :param cwd: The directory where git should be invoked. (None -> current dir, "" -> package dir)
    :param digits: Number of SHA digits that should be appended as metadata. [0-40]
    :returns: The resulting version string formatted according to PEP440.
    """
    return _format_git_version(fallback, cwd, digits, ".", "+")


# https://semver.org/spec/v2.0.0.html
def semantic(fallback: str = __version_string__,
             cwd: Optional[str] = "", digits: int = 10) -> str:
    """Deduces the package version via git describe and returns it in semantic versioning format.

    :param fallback: The version string that is returned when no git based version can be derived.
    :param cwd: The directory where git should be invoked. (None -> current dir, "" -> package dir)
    :param digits: Number of SHA digits that should be appended as metadata. [0-40]
    :returns: The resulting version string formatted according to semantic versioning.
    """
    return _format_git_version(fallback, cwd, digits, "-", "+")
