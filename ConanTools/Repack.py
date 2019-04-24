import argparse
import configparser
import inspect
import json
import os
import subprocess
import sys
import tempfile

global_pid_cache = {}


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


def format_arg_list(values, argument):
    args = []
    if not isinstance(values, list):
        values = [values]
    for x in values:
        args.append(argument)
        if x is not None:
            args.append(x)
    return args


def run(args, cwd=None, stdout=None, stderr=None, ignore_returncode=False):
    cwd = os.path.abspath(cwd if cwd is not None else os.getcwd())
    os.makedirs(cwd, exist_ok=True)
    print("[%s] $ %s" % (cwd, " ".join(args)))
    sys.stdout.flush()
    result = subprocess.run(args, stdout=stdout, stderr=stderr, cwd=cwd)
    if stdout == subprocess.PIPE:
        result.stdout = result.stdout.decode().strip()
    if stderr == subprocess.PIPE:
        result.stderr = result.stderr.decode().strip()
    if ignore_returncode is False and result.returncode != 0:
        if stdout == subprocess.PIPE:
            print(result.stdout, file=sys.stdout)
        if stderr == subprocess.PIPE:
            print(result.stderr, file=sys.stderr)
        raise ValueError(
            "Executing command \"%s\" failed! (returncode=%d)" %
            (" ".join(args), result.returncode))
    return result


def run_conan_build_command(cmd, args, remote, profiles, build, cwd):
    profile_args = format_arg_list(profiles or get_cl_profiles(), "--profile")
    build_args = format_arg_list(build or get_cl_build_flags() or "outdated", "--build")
    remote_args = format_arg_list(remote or [], "--remote")
    run(["conan", cmd] + args + profile_args + build_args + remote_args, cwd=cwd)


class PID():
    def __init__(self, name=None, version=None, user=None, channel=None, recipe=None, cwd=None):
        if recipe and cwd and not os.path.isabs(recipe):
            recipe = os.path.normpath(os.path.join(cwd, recipe))

        self._name = name
        self._version = version
        self.user = user
        self.channel = channel
        self._recipe = recipe

    def get_recipe_field(self, field_name):
        assert self.recipe is not None, "Recipe has not been defined!"
        self._recipe_field_cache = getattr(self, "_recipe_field_cache", None)
        if self._recipe_field_cache is None:
            tmpfile = None
            try:
                tmpfile = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
                tmpfile.close()
                run(["conan", "inspect", self.recipe, "--json", tmpfile.name],
                    stdout=subprocess.PIPE)
                with open(tmpfile.name) as f:
                    self._recipe_field_cache = json.load(f)
            finally:
                if tmpfile and os.path.exists(tmpfile.name):
                    os.unlink(tmpfile.name)
        return self._recipe_field_cache[field_name]

    @property
    def recipe(self):
        return self._recipe

    @property
    def name(self):
        if self._name is None:
            self._name = self.get_recipe_field("name")
        return self._name

    @property
    def version(self):
        if self._version is None:
            self._version = self.get_recipe_field("version")
        return self._version

    def package_id(self, name=None, version=None, user=None, channel=None):
        name = name or self.name
        version = version or self.version
        user = user or self.user
        channel = channel or self.channel

        # at the very least a user and a channel has to be defined
        assert name is not None, "Package name is not defined!"
        assert version is not None, "Package version is not defined!"
        assert user is not None, "Package user is not defined!"
        assert channel is not None, "Package channel is not defined!"
        return "{}/{}@{}/{}".format(name, version, user, channel)

    def set_remote(self, remote=None, user=None, channel=None):
        package_id = self.package_id(user=user, channel=channel)
        run(["conan", "remote", "add_ref", package_id, remote])  # , ignore_returncode=True

    def in_cache(self, user=None, channel=None):
        package_id = self.package_id(user=user, channel=channel)

        # check if the recipe is known locally
        result = run(["conan", "search", package_id], ignore_returncode=True)
        if result.returncode == 0:
            return True
        return False

    def in_remote(self, remote=None, user=None, channel=None):
        package_id = self.package_id(user=user, channel=channel)

        # check if the recipe is known on the remote
        result = run(["conan", "search", package_id, "--remote", remote], ignore_returncode=True)
        if result.returncode == 0:
            return True
        return False

    def download_recipe(self, remote=None, user=None, channel=None):
        package_id = self.package_id(user=user, channel=channel)
        run(["conan", "download", package_id, "--remote", remote, "--recipe"])

    def export(self, user=None, channel=None, remote=None):
        assert self.recipe is not None, "Recipe has not been defined!"
        package_id = self.package_id(user=user, channel=channel)
        run(["conan", "export", self.recipe, package_id])
        if remote is not None:
            self.set_remote(remote=remote, user=user, channel=channel)

    def install(self, user=None, channel=None, remote=None,
                profiles=None, build=None, cwd=None):
        package_id = self.package_id(user=user, channel=channel)
        run_conan_build_command("install", [package_id], remote=remote,
                                profiles=profiles, build=build, cwd=cwd)

    def create(self, user=None, channel=None, remote=None,
               profiles=None, build=None, cwd=None):
        package_id = self.package_id(user=user, channel=channel)
        run_conan_build_command("create", [self.recipe, package_id], remote=remote,
                                profiles=profiles, build=build, cwd=cwd)


def get_recipe_field(recipe, field_name, cwd=None):
    # make the recipe path absolute
    cwd = cwd or os.getcwd()
    if not os.path.isabs(recipe):
        recipe = os.path.normpath(os.path.join(cwd, recipe))

    if not os.path.exists(recipe):
        return None

    pid = global_pid_cache.setdefault(recipe, PID(recipe=recipe))
    return pid.get_recipe_field(field_name)


class ConanImportTxtFile:
    def __init__(self, file_name=None, cwd=None):
        self._package_ids = {}
        self._file_name = file_name
        self._delete = False

        # create a temporary file name if needed
        if self._file_name is None:
            tmpfile = tempfile.NamedTemporaryFile(suffix=".txt", dir=cwd, delete=False)
            tmpfile.close()
            self._file_name = tmpfile.name
            self._delete = True

    def __del__(self):
        if self._delete and os.path.exists(self._file_name):
            os.unlink(self._file_name)

    def add_package(self, name, refstring):
        self._package_ids[name] = refstring

    def add_pid(self, pid, user=None, channel=None):
        self._package_ids[pid.name] = pid.package_id(user=user, channel=channel)

    def install(self, remote=None, profiles=None, build=None, cwd=None):
        # write a conanfile in txt format with the package ids the imports
        config = configparser.ConfigParser(allow_no_value=True)
        config["requires"] = {x: None for x in self._package_ids.values()}
        config["imports"] = {
            "., * -> . @ root_package={}".format(x): None for x in self._package_ids.keys()
        }
        with open(self._file_name, 'w') as configfile:
            config.write(configfile)

        run_conan_build_command("install", [self._file_name], remote=remote,
                                profiles=profiles, build=build, cwd=cwd)


def extend_profile(inpath, outpath, build_requires):
    config = configparser.ConfigParser(allow_no_value=True)
    config.read([inpath])
    for x in build_requires:
        config["build_requires"][x] = None
    with open(outpath, 'w') as configfile:
        config.write(configfile)
