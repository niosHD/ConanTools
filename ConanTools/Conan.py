import json
import os
import shutil
import subprocess as sp
import tempfile
from typing import Optional

import ConanTools
import ConanTools.Hack as Hack

CONAN_PROGRAM = os.environ.get("CONAN_PROGRAM", "conan")


def run(args, cwd=None, stdout=None, stderr=None, ignore_returncode=False,
        conan_program=CONAN_PROGRAM):
    args = [conan_program] + args
    return ConanTools.run(args, cwd=cwd, stdout=stdout, stderr=stderr,
                          ignore_returncode=ignore_returncode)


def _format_arg_list(values, argument):
    args = []
    if not isinstance(values, list):
        values = [values]
    for x in values:
        args.append(argument)
        if x is not None:
            args.append(x)
    return args


def run_build(cmd, args, remote, profiles, build, options, cwd):
    if profiles is None:
        profiles = Hack.get_cl_profiles()
    if build is None:
        build = Hack.get_cl_build_flags() or "outdated"
    profile_args = _format_arg_list(profiles, "--profile")
    build_args = _format_arg_list(build, "--build")
    remote_args = _format_arg_list(remote or [], "--remote")
    option_args = _format_arg_list(["{}={}".format(k, v) for k, v in options.items()] or [], "-o")
    run([cmd] + args + profile_args + build_args + remote_args + option_args, cwd=cwd)


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

    def install(self, remote=None, profiles=None, build=None, options={}, cwd=None):
        run_build("install", [str(self)], remote=remote, profiles=profiles, options=options,
                  build=build, cwd=cwd)

    def set_remote(self, remote):
        run(["remote", "add_ref", str(self), remote])

    def create_alias(self, name=None, version=None, user=None, channel=None):
        alias_ref = self.clone(name=name, version=version, user=user, channel=channel)
        run(["alias", str(alias_ref), str(self)])
        return alias_ref

    def upload_all(self, remote):
        run(["upload", str(self), "--remote", remote, "--all", "-c"])


class PkgLayout():
    def src_folder(self, recipe: 'Recipe'):
        raise NotImplementedError

    def build_folder(self, recipe: 'Recipe'):
        raise NotImplementedError

    def pkg_folder(self, recipe: 'Recipe'):
        raise NotImplementedError


class RelativePkgLayout(PkgLayout):
    """Layout class that permits various relative package layouts.

    The default mode (i.e., no ``root`` specified) is to use the directory of the recipe as layout
    root. Subsequently, subdirectories relative to the recipe are used for all operations. The
    actual name of the subdirectories can be customized and an additional ``offset`` parameter can
    be used to further move the root relative to the recipe.

    Alternatively, when an explicit ``root`` has been specified, directories relative to this root
    are used. By default, the package name is used as ``offset`` to permit reusing the same layout
    instance accross multiple recipes.
    """
    def __init__(self, root: str = None, offset: str = None, src_dir: str = "_source",
                 build_dir: str = "_build", pkg_dir: str = "_install"):
        self._root = root
        self._offset = offset
        self._src_dir = src_dir
        self._build_dir = build_dir
        self._pkg_dir = pkg_dir

    def root(self, recipe: 'Recipe'):
        if self._root is None:
            # No root has been defined, use the recipe path directory as root and apply the offset
            # if available.
            root = os.path.dirname(recipe.path)
            offset = self._offset or "."
        else:
            # Use the specified root and offset if available. Otherwise, fallback to the package
            # name as offset.
            root = self._root
            offset = self._offset or recipe.get_field("name")

        return os.path.normpath(os.path.join(root, offset))

    def src_folder(self, recipe: 'Recipe'):
        if recipe.external_source:
            return os.path.join(self.root(recipe), self._src_dir)
        else:
            return os.path.dirname(recipe.path)

    def build_folder(self, recipe: 'Recipe'):
        return os.path.join(self.root(recipe), self._build_dir)

    def pkg_folder(self, recipe: 'Recipe'):
        return os.path.join(self.root(recipe), self._pkg_dir)


class TempPkgLayout(PkgLayout):
    def __init__(self, src_dir="_source", build_dir="_build",
                 pkg_dir="_install"):
        self._directories = {}
        self._src_dir = src_dir
        self._build_dir = build_dir
        self._pkg_dir = pkg_dir

    def __del__(self):
        for directory in self._directories.values():
            shutil.rmtree(directory)

    def _root(self, recipe: 'Recipe'):
        result = self._directories.get(recipe, False)
        if result:
            return result
        result = tempfile.mkdtemp(recipe.get_field("name"))
        self._directories[recipe] = result
        return result

    def src_folder(self, recipe: 'Recipe'):
        if recipe.external_source:
            return os.path.join(self._root(recipe), self._src_dir)
        else:
            return os.path.dirname(recipe.path)

    def build_folder(self, recipe: 'Recipe'):
        return os.path.join(self._root(recipe), self._build_dir)

    def pkg_folder(self, recipe: 'Recipe'):
        return os.path.join(self._root(recipe), self._pkg_dir)


class Recipe():
    def __init__(self, path: str, external_source: bool = False,
                 layout: Optional[PkgLayout] = None, cwd: Optional[str] = None):
        # Make the recipe path absolute.
        cwd = cwd or os.getcwd()
        if not os.path.isabs(path):
            path = os.path.normpath(os.path.join(cwd, path))
        self._path = path

        # Ideally this property should be queryable from the recipe.
        # However at the moment I do not know how to do it.
        self._external_source = external_source

        self._layout = layout or RelativePkgLayout()

    @property
    def path(self):
        return self._path

    @property
    def external_source(self):
        return self._external_source

    def get_field(self, field_name: str):
        self._recipe_field_cache = getattr(self, "_recipe_field_cache", None)
        if self._recipe_field_cache is None:
            tmpfile = None
            try:
                tmpfile = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
                tmpfile.close()
                sp.check_call([CONAN_PROGRAM, "inspect", self.path, "--json", tmpfile.name],
                              stdin=sp.DEVNULL, stdout=sp.DEVNULL, stderr=sp.DEVNULL)
                with open(tmpfile.name) as f:
                    self._recipe_field_cache = json.load(f)
            finally:
                if tmpfile and os.path.exists(tmpfile.name):
                    os.unlink(tmpfile.name)
        return self._recipe_field_cache[field_name]

    def reference(self, user: str, channel: str, name=None, version=None):
        name = name or self.get_field("name")
        version = version or self.get_field("version")
        return Reference(name=name, version=version, user=user, channel=channel)

    def export(self, user, channel, name=None, version=None):
        ref = self.reference(name=name, version=version, user=user, channel=channel)
        run(["export", self.path, str(ref)])
        return ref

    def create(self, user, channel, name=None, version=None, remote=None,
               profiles=None, options={}, build=None, cwd=None):
        ref = self.reference(name=name, version=version, user=user, channel=channel)
        run_build("create", [self.path, str(ref)],
                  remote=remote, profiles=profiles, options=options, build=build, cwd=cwd)
        return ref

    def create_local(self, user, channel, name=None, version=None, remote=None,
                     profiles=None, options={}, build=None,
                     layout=None, src_folder=None, build_folder=None, pkg_folder=None):
        self.install(layout=layout, build_folder=build_folder, profiles=profiles, options=options,
                     build=build, remote=remote)
        if self.external_source:
            self.source(layout=layout, src_folder=src_folder, build_folder=build_folder)
        self.build(layout=layout, src_folder=src_folder, build_folder=build_folder,
                   pkg_folder=pkg_folder)
        self.package(layout=layout, src_folder=src_folder, build_folder=build_folder,
                     pkg_folder=pkg_folder)
        self.export_pkg(user=user, channel=channel, name=name, version=version,
                        profiles=profiles, options=options, layout=layout, pkg_folder=pkg_folder)

    def install(self, layout=None, build_folder=None, profiles=None, options={}, build=None,
                remote=None):
        layout = layout or self._layout
        build_folder = build_folder or layout.build_folder(self)
        run_build("install", [self.path], remote=remote, profiles=profiles, options=options,
                  build=build, cwd=build_folder)

    def source(self, layout=None, src_folder=None, build_folder=None):
        layout = layout or self._layout
        src_folder = src_folder or layout.src_folder(self)
        build_folder = build_folder or layout.build_folder(self)
        run(["source", self.path, "--source-folder=" + src_folder], cwd=build_folder)

    def build(self, layout=None, src_folder=None, build_folder=None, pkg_folder=None):
        layout = layout or self._layout
        src_folder = src_folder or layout.src_folder(self)
        build_folder = build_folder or layout.build_folder(self)
        pkg_folder = pkg_folder or layout.pkg_folder(self)
        assert src_folder is not None
        run(["build", self.path,
             "--source-folder=" + src_folder, "--package-folder=" + pkg_folder],
            cwd=build_folder)

    def package(self, layout=None, src_folder=None, build_folder=None, pkg_folder=None):
        layout = layout or self._layout
        src_folder = src_folder or layout.src_folder(self)
        build_folder = build_folder or layout.build_folder(self)
        pkg_folder = pkg_folder or layout.pkg_folder(self)
        run(["package", self.path,
             "--source-folder=" + src_folder, "--package-folder=" + pkg_folder],
            cwd=build_folder)

    def export_pkg(self, user, channel, name=None, version=None,
                   profiles=None, options={}, layout=None, pkg_folder=None, cwd=None):
        layout = layout or self._layout
        pkg_folder = pkg_folder or layout.pkg_folder(self)
        ref = self.reference(name=name, version=version, user=user, channel=channel)
        run_build("export-pkg", [self.path, str(ref), "--package-folder=" + pkg_folder],
                  remote=None, profiles=profiles, options=options, build=[], cwd=cwd)
