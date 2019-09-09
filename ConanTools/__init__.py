import os
import shlex
import string
import subprocess as sp
import sys
from typing import Dict, List, Optional

import ConanTools.Repack


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


def slug(input: Optional[str]) -> Optional[str]:
    """Creates a lowercase alphanumeric version of the input with '-' for all other characters.

    Additionally, all '-' characters are stripped from the start and end of the result.
    The approach is similar to the one Gitlab CI uses for _SLUG variables (see
    `CI_COMMIT_REF_SLUG <https://docs.gitlab.com/ee/ci/variables/predefined_variables.html>`_).

    :param input: Optional input string.
    :returns: Slug version of the input string or None if input is None.
    """
    if input is None:
        return None
    whitelist = set(string.ascii_letters + string.digits)

    def sanitize_char(ch):
        if ch in whitelist:
            return ch.lower()
        return '-'

    return ''.join([sanitize_char(ch) for ch in input]).strip('-')


def env_flag(name: str, default: bool = False) -> bool:
    """Queries an environment variable and converts the value to a bool.

    :param name: Name of the environment variable.
    :param default: Default value that is returned when the variable is not defined.
    :returns: Boolean interpretation of the value.
    """
    res = os.environ.get(name, default)
    if isinstance(res, bool):
        return res
    res = res.lower()
    if res == "0" or res == "false" or res == "off":
        return False
    return True


def create(recipe: 'Conan.Recipe', user: str, channel: str, name: Optional[str] = None,
           version: Optional[str] = None, remote: Optional[str] = None,
           profiles: Optional[List[str]] = None, options: Dict[str, str] = {},
           build: Optional[List[str]] = None, cwd: Optional[str] = None,
           layout: Optional['Conan.PkgLayout'] = None):
    """Creates a package from the recipe using either the local or cache-based workflow.

    The ``CT_CREATE_LOCAL`` environment variable is used to enable the local instead of the
    cache-based flow. By default, the local flow builds into fixed directories next to the recipe
    which is more comfortable during development and also better suited for build caching.
    """
    if env_flag("CT_CREATE_LOCAL"):
        recipe.create_local(user=user, channel=channel, name=name, version=version, remote=remote,
                            profiles=profiles, options=options, build=build, layout=layout)
    else:
        recipe.create(user=user, channel=channel, name=name, version=version, remote=remote,
                      profiles=profiles, options=options, build=build, cwd=cwd)


def pkg_import(recipe: 'Conan.Recipe', user: str, channel: str, name: Optional[str] = None,
               version: Optional[str] = None, remote: Optional[str] = None,
               profiles: Optional[List[str]] = None, options: Dict[str, str] = {},
               build: Optional[List[str]] = None, pkg_folder: Optional[str] = None):
    """Imports the package content, after building it if necessary, into the pkg_folder.
    """
    # Try to import an already existing package but without building it.
    importFile = ConanTools.Repack.ConanImportTxtFile()
    importFile.add_package(recipe.reference(user=user, channel=channel, name=name, version=version))
    try:
        importFile.install(remote=remote, profiles=profiles, options=options, build=[],
                           cwd=pkg_folder)
        return
    except ValueError:
        pass

    # Build the package using the local or cache-based workflow and then import the content.
    create(recipe=recipe, user=user, channel=channel, name=name, version=version, remote=remote,
           profiles=profiles, options=options, build=build)
    importFile.install(remote=remote, profiles=profiles, options=options, build=[], cwd=pkg_folder)
