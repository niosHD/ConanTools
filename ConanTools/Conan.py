import json
import os
import subprocess as sp
import sys
import tempfile
import ConanTools.Hack as Hack

CONAN_PROGRAM = os.environ.get("CONAN_PROGRAM", "conan")


# TODO make this helper more similar to subprocess.run
def run(args, cwd=None, stdout=None, stderr=None, ignore_returncode=False,
        conan_program=CONAN_PROGRAM):
    cwd = os.path.abspath(cwd if cwd is not None else os.getcwd())
    os.makedirs(cwd, exist_ok=True)
    args = [conan_program] + args
    print("[%s] $ %s" % (cwd, " ".join(args)))
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


def _format_arg_list(values, argument):
    args = []
    if not isinstance(values, list):
        values = [values]
    for x in values:
        args.append(argument)
        if x is not None:
            args.append(x)
    return args


def run_build(cmd, args, remote, profiles, build, cwd):
    profile_args = _format_arg_list(profiles or Hack.get_cl_profiles(), "--profile")
    build_args = _format_arg_list(build or Hack.get_cl_build_flags() or "outdated", "--build")
    remote_args = _format_arg_list(remote or [], "--remote")
    run([cmd] + args + profile_args + build_args + remote_args, cwd=cwd)


def get_recipe_field(recipe, field_name, cwd=None):
    # make the recipe path absolute
    cwd = cwd or os.getcwd()
    if not os.path.isabs(recipe):
        recipe = os.path.normpath(os.path.join(cwd, recipe))

    if not os.path.exists(recipe):
        return None

    get_recipe_field._recipe_cache = getattr(get_recipe_field, "_recipe_cache", {})
    pid = get_recipe_field._recipe_cache.setdefault(recipe, PID(recipe=recipe))
    return pid.get_recipe_field(field_name)


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
                sp.check_call([CONAN_PROGRAM, "inspect", self.recipe, "--json", tmpfile.name],
                              stdin=sp.DEVNULL, stdout=sp.DEVNULL, stderr=sp.DEVNULL)
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
        run(["remote", "add_ref", package_id, remote])  # , ignore_returncode=True

    def in_cache(self, user=None, channel=None):
        package_id = self.package_id(user=user, channel=channel)

        # check if the recipe is known locally
        result = run(["search", package_id], ignore_returncode=True)
        if result.returncode == 0:
            return True
        return False

    def in_remote(self, remote=None, user=None, channel=None):
        package_id = self.package_id(user=user, channel=channel)

        # check if the recipe is known on the remote
        result = run(["search", package_id, "--remote", remote], ignore_returncode=True)
        if result.returncode == 0:
            return True
        return False

    def download_recipe(self, remote=None, user=None, channel=None):
        package_id = self.package_id(user=user, channel=channel)
        run(["download", package_id, "--remote", remote, "--recipe"])

    def export(self, user=None, channel=None, remote=None):
        assert self.recipe is not None, "Recipe has not been defined!"
        package_id = self.package_id(user=user, channel=channel)
        run(["export", self.recipe, package_id])
        if remote is not None:
            self.set_remote(remote=remote, user=user, channel=channel)

    def install(self, user=None, channel=None, remote=None,
                profiles=None, build=None, cwd=None):
        package_id = self.package_id(user=user, channel=channel)
        run_build("install", [package_id], remote=remote, profiles=profiles, build=build, cwd=cwd)

    def create(self, user=None, channel=None, remote=None,
               profiles=None, build=None, cwd=None):
        package_id = self.package_id(user=user, channel=channel)
        run_build("create", [self.recipe, package_id],
                  remote=remote, profiles=profiles, build=build, cwd=cwd)
