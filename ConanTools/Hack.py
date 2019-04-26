import argparse
import inspect
import os


def reach(var_name, function_name=None):
    """Helper to search for local variable by traversing the call stack.
    """
    for f in reversed(inspect.stack()):
        if function_name and f.function != function_name:
            continue
        if var_name in f[0].f_locals:
            return f[0].f_locals[var_name]
    return None


def get_cl_profiles():
    """ HACK Determines the profiles which are specified when invoking conan.

    This function determines the initial working directory by inspecting the
    call stack and reparses the arguments to extract paths to the profile
    files.
    """
    initial_cwd = reach("current_dir", function_name="main")
    if initial_cwd is None:
        return []

    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("-pr", "--profile", action='append', dest='profiles', default=[])
    args, _ = parser.parse_known_args()
    profiles = []
    for x in args.profiles:
        if not os.path.isabs(x):
            fullpath = os.path.normpath(os.path.join(initial_cwd, x))
            if os.path.exists(fullpath):
                profiles.append(fullpath)
                continue
        profiles.append(x)
    return profiles


def get_cl_build_flags():
    """ HACK Determine the build flags which are specified when invoking conan.

    This function reparses the arguments to extract the build flags.
    """
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("-b", "--build", action='append', dest='build', nargs="?", default=[])
    args, _ = parser.parse_known_args()
    return args.build
