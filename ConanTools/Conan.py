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


# FIXME empty lists in python are evaluated as False -> it is not possible
#       to specify no build flag at the moment or to suppress the use of the Hack functions
#       without specifying profile/build flags
def run_build(cmd, args, remote, profiles, build, cwd):
    profile_args = _format_arg_list(profiles or Hack.get_cl_profiles(), "--profile")
    build_args = _format_arg_list(build or Hack.get_cl_build_flags() or "outdated", "--build")
    remote_args = _format_arg_list(remote or [], "--remote")
    run([cmd] + args + profile_args + build_args + remote_args, cwd=cwd)


def get_recipe_field(recipe_path, field_name, cwd=None):
    # make the recipe path absolute
    cwd = cwd or os.getcwd()
    if not os.path.isabs(recipe_path):
        recipe_path = os.path.normpath(os.path.join(cwd, recipe_path))

    if not os.path.exists(recipe_path):
        return None

    get_recipe_field._recipe_cache = getattr(get_recipe_field, "_recipe_cache", {})
    recipe = get_recipe_field._recipe_cache.setdefault(recipe_path, Recipe(recipe_path))
    return recipe.get_field(field_name)


class Reference():
    def __init__(self, name, version, user, channel):
        self._name = name
        self._version = version
        self._user = user
        self._channel = channel

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    @property
    def user(self):
        return self._user

    @property
    def channel(self):
        return self._channel

    def clone(self, name=None, version=None, user=None, channel=None):
        return Reference(name=name or self.name,
                         version=version or self.version,
                         user=user or self.user,
                         channel=channel or self.channel)

    def __str__(self):
        return "{}/{}@{}/{}".format(self.name, self.version, self.user, self.channel)

    def in_local_cache(self):
        # check if the recipe is known locally
        result = run(["search", str(self)], ignore_returncode=True)
        if result.returncode == 0:
            return True
        return False

    def in_remote(self, remote):
        # check if the recipe is known on the remote
        result = run(["search", str(self), "--remote", remote], ignore_returncode=True)
        if result.returncode == 0:
            return True
        return False

    def download_recipe(self, remote=None):
        remote_args = _format_arg_list(remote or [], "--remote")
        run(["download", str(self), "--recipe"] + remote_args)

    def install(self, remote=None, profiles=None, build=None, cwd=None):
        run_build("install", [str(self)], remote=remote, profiles=profiles, build=build, cwd=cwd)

    def set_remote(self, remote):
        run(["remote", "add_ref", str(self), remote])

    def create_alias(self, name=None, version=None, user=None, channel=None):
        alias_ref = self.clone(name=name, version=version, user=user, channel=channel)
        run(["alias", str(alias_ref), str(self)])
        return alias_ref

    def upload_all(self, remote):
        run(["upload", str(self), "--remote", remote, "--all", "-c"])


class Recipe():
    def __init__(self, path, cwd=None):
        if path and cwd and not os.path.isabs(path):
            path = os.path.normpath(os.path.join(cwd, path))
        self._path = path

    def get_field(self, field_name):
        self._recipe_field_cache = getattr(self, "_recipe_field_cache", None)
        if self._recipe_field_cache is None:
            tmpfile = None
            try:
                tmpfile = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
                tmpfile.close()
                sp.check_call([CONAN_PROGRAM, "inspect", self._path, "--json", tmpfile.name],
                              stdin=sp.DEVNULL, stdout=sp.DEVNULL, stderr=sp.DEVNULL)
                with open(tmpfile.name) as f:
                    self._recipe_field_cache = json.load(f)
            finally:
                if tmpfile and os.path.exists(tmpfile.name):
                    os.unlink(tmpfile.name)
        return self._recipe_field_cache[field_name]

    def reference(self, user, channel, name=None, version=None):
        name = name or self.get_field("name")
        version = version or self.get_field("version")
        return Reference(name=name, version=version, user=user, channel=channel)

    def export(self, user, channel, name=None, version=None):
        ref = self.reference(name=name, version=version, user=user, channel=channel)
        run(["export", self._path, str(ref)])
        return ref

    def create(self, user, channel, name=None, version=None, remote=None,
               profiles=None, build=None, cwd=None):
        ref = self.reference(name=name, version=version, user=user, channel=channel)
        run_build("create", [self._path, str(ref)],
                  remote=remote, profiles=profiles, build=build, cwd=cwd)
        return ref

    def _default_src_folder(self):
        recipe_dir = os.path.dirname(os.path.abspath(self._path))
        return recipe_dir

    def _default_build_folder(self):
        recipe_dir = os.path.dirname(os.path.abspath(self._path))
        return os.path.join(recipe_dir, "_build", self.get_field("name"))

    def _default_pkg_folder(self):
        recipe_dir = os.path.dirname(os.path.abspath(self._path))
        return os.path.join(recipe_dir, "_install", self.get_field("name"))

    def install(self, build_folder=None, profiles=None, build=None, remote=None):
        build_folder = build_folder or self._default_build_folder()
        run_build("install", [self._path], remote=remote, profiles=profiles, build=build,
                  cwd=build_folder)

    def build(self, src_folder=None, build_folder=None, pkg_folder=None):
        build_folder = build_folder or self._default_build_folder()
        src_folder = src_folder or self._default_src_folder()
        pkg_folder = pkg_folder or self._default_pkg_folder()
        run(["build", self._path, "--source-folder="+src_folder, "--package-folder="+pkg_folder],
            cwd=build_folder)

    def package(self, src_folder=None, build_folder=None, pkg_folder=None):
        build_folder = build_folder or self._default_build_folder()
        src_folder = src_folder or self._default_src_folder()
        pkg_folder = pkg_folder or self._default_pkg_folder()
        run(["package", self._path, "--source-folder="+src_folder, "--package-folder="+pkg_folder],
            cwd=build_folder)
