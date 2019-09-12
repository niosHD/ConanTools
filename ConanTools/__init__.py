import os
import string
from typing import Dict, List, Optional

import ConanTools.Conan
import ConanTools.Repack


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
                            profiles=profiles, options=options, build=build, layout=layout,
                            add_script=True)
    else:
        recipe.create(user=user, channel=channel, name=name, version=version, remote=remote,
                      profiles=profiles, options=options, build=build, cwd=cwd)


def pkg_import(recipe: 'Conan.Recipe', user: str, channel: str, name: Optional[str] = None,
               version: Optional[str] = None, remote: Optional[str] = None,
               profiles: Optional[List[str]] = None, options: Dict[str, str] = {},
               build: Optional[List[str]] = None, pkg_folder: Optional[str] = None):
    """Imports the package content, after building it if necessary, into the pkg_folder.

    By default, subpackages are built using the local flow and directly use the specified
    pkg_folder. This mode is similar to, for example, a superbuild using cmake. Alternatively,
    if the ``CT_ENABLE_SUBPACKAGES`` environment variable is defined, each subpackage is
    created individually and gets subsequently imported into the pkg_folder.
    """
    reference = recipe.reference(user=user, channel=channel, name=name, version=version)

    # qualify the options with the package name
    full_opt = {}
    for k, v in options.items():
        if ":" in k:
            full_opt[k] = v
        else:
            full_opt["{}:{}".format(reference.name, k)] = v

    if not env_flag("CT_ENABLE_SUBPACKAGES"):
        # Build package with the local flow but skip real package creation. Install
        # directly into the pkg_folder instead.
        recipe.install(profiles=profiles, options=full_opt, build=build, remote=remote,
                       add_script=True)
        if recipe.external_source:
            recipe.source(add_script=True)
        recipe.build(pkg_folder=pkg_folder, add_script=True)
        recipe.package(pkg_folder=pkg_folder, add_script=True)
        return

    # Try to import an already existing package but without building it.
    importFile = ConanTools.Repack.ConanImportTxtFile()
    importFile.add_package(reference)
    try:
        importFile.install(remote=remote, profiles=profiles, options=full_opt, build=[],
                           cwd=pkg_folder)
        return
    except ValueError:
        pass

    # Build the package using the local or cache-based workflow and then import the content.
    create(recipe=recipe, user=user, channel=channel, name=name, version=version, remote=remote,
           profiles=profiles, options=full_opt, build=build)
    importFile.install(remote=remote, profiles=profiles, options=full_opt, build=[], cwd=pkg_folder)


def write_helper_scripts(filedir: str, recipe_path: str, src_folder: str = None,
                         build_folder: str = None, pkg_folder: str = None):
    """Generate helper shell scripts for executing the build and package stage.
    """
    ConanTools.Conan.write_conan_sh_file(filedir, "build",
                                         ["build", recipe_path, "--source-folder=" + src_folder,
                                          "--package-folder=" + pkg_folder], build_folder)
    ConanTools.Conan.write_conan_sh_file(filedir, "package",
                                         ["package", recipe_path, "--package-folder=" + pkg_folder],
                                         build_folder)
