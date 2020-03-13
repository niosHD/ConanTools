import argparse
from ConanTools import Conan, Version
import configparser
import json
import tempfile
from typing import Dict, List, Optional
import os
import platform
import shutil
import subprocess
import sys


def cli_parsing() -> argparse.Namespace:
    # Setup the actual argument parsing logic.
    parser = argparse.ArgumentParser(
        add_help=False, allow_abbrev=False,
        description='ConanTools CLI that provides commands missing in conan.')
    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                        help='Show this help message and exit.')
    parser.add_argument('-v', '--version', action='version', version=Version.pep440(),
                        help='Display the tool/library version and exit.')

    subparsers = parser.add_subparsers(dest='subcommand')

    # EXEC
    parser_exec = subparsers.add_parser(
        'exec', add_help=False, allow_abbrev=False,
        help='Execute a command in the environment of a package.')
    parser_exec.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                             help='Show this help message and exit.')
    parser_exec.add_argument('-p', '--profile', action='append',
                             help='Profile name or file.')
    parser_exec.add_argument('-r', '--reference', action='append',
                             help='Full package reference (Pkg/version@user/channel).')

    parser_exec.add_argument('command', nargs=1)
    parser_exec.add_argument('arguments', nargs=argparse.REMAINDER)

    args = parser.parse_args()
    return args


def cmd_exec(command: List[str],
             references: Optional[List[Conan.Reference]] = None,
             profiles: Optional[List[str]] = None,
             cwd: Optional[str] = None,
             initial_env: Optional[Dict[str, str]] = None):
    """Executes a command in the environment defined by the profile, the specified references,
    settings, and options. If any of the required packages is missing they are automatically
    installed.
    """
    # Setup proper defaults.
    cwd = cwd if cwd is not None else os.getcwd()
    references = references if references is not None else []
    initial_env = initial_env if initial_env is not None else os.environ.copy()

    # Either use the specified recipe path or build a temporary conanfile.txt, install it and
    # determine the required environment variables.
    try:
        # Write all requested references to the conanfile. Note that, as long as the extension
        # is correct, the actual name does not matter. Furthermore, we have to close the
        # file such that Windows can work with them. (see https://bugs.python.org/issue14243)
        tempdir = tempfile.mkdtemp()
        recipe_path = os.path.join(tempdir, 'conanfile.txt')
        config = configparser.ConfigParser(allow_no_value=True)
        config.optionxform = str
        config['requires'] = {str(x): None for x in references}
        config['generators'] = {'json': None}
        with open(recipe_path, 'w') as configfile:
            config.write(configfile)

        args = Conan.fmt_build_args('install', [recipe_path], remote=None, profiles=profiles,
                                    options={}, build=[])
        Conan.run(args, cwd=tempdir)

        # FIXME This generator does not provide the variables from the profile ...
        #       Dump the env using a conanfile.py to work around this limitation.
        with open(os.path.join(tempdir, 'conanbuildinfo.json')) as f:
            json_data = json.load(f)
    finally:
        # Delete the temporary directory after the processing.
        shutil.rmtree(tempdir)

    # Update the environment with the information from the virtual
    # environment generator.
    for key, value in json_data['deps_env_info'].items():
        if isinstance(value, list):
            value = os.pathsep.join(value)
            if key in initial_env:
                value = os.pathsep.join([value, initial_env[key]])
        initial_env[key] = value

    # Change to the correct directory which might has been changed during
    # installation and launch the command in the new environment.
    os.chdir(cwd)

    # Unfortunately, os.execvpe does crash on some Windows python versions
    # (see https://bugs.python.org/issue23462). Furthermore, using exec on
    # Windows apparently does not yield the desired behavior anyway
    # (see https://bugs.python.org/issue19124). Work around both problems
    # using a subprocess on Windows.
    if platform.system().lower() == 'windows':
        sys.exit(subprocess.call(command, env=initial_env))
    else:
        os.execvpe(command[0], args=command, env=initial_env)


def main():
    args = cli_parsing()
    if args.subcommand == 'exec':
        refs = [Conan.Reference.from_string(x) for x in args.reference or []]
        cmd_exec(args.command + args.arguments, references=refs, profiles=args.profile)


if __name__ == '__main__':
    main()
