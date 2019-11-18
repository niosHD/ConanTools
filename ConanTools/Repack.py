import configparser
import glob
import tempfile
from typing import List
import os

import ConanTools.Conan as Conan


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

    def add_package_string(self, name, refstring: str):
        self._package_ids[name] = refstring

    def add_package(self, ref: Conan.Reference):
        self._package_ids[ref.name] = str(ref)

    def add_packages(self, refs: List[Conan.Reference]):
        for ref in refs:
            self.add_package(ref)

    def install(self, remote=None, profiles=None, options={}, build=None, cwd=None):
        # write a conanfile in txt format with the package ids the imports
        config = configparser.ConfigParser(allow_no_value=True)
        config.optionxform = str
        config["requires"] = {x: None for x in self._package_ids.values()}
        config["imports"] = {
            "., * -> . @ root_package={}".format(x): None for x in self._package_ids.keys()
        }
        with open(self._file_name, 'w') as configfile:
            config.write(configfile)

        args = Conan.fmt_build_args("install", [self._file_name], remote=remote, profiles=profiles,
                                    options=options, build=build)
        Conan.run(args, cwd=cwd)

        # remove conan packaging metadata files
        cwd = os.path.abspath(cwd if cwd is not None else os.getcwd())
        files = glob.glob(os.path.join(cwd, "conan*"))
        files += glob.glob(os.path.join(cwd, "graph_info.json"))
        for f in files:
            os.remove(f)


def extend_profile(inpath, outpath, build_requires):
    config = configparser.ConfigParser(allow_no_value=True)
    config.optionxform = str
    config.read([inpath])
    for x in build_requires:
        config["build_requires"][x] = None
    with open(outpath, 'w') as configfile:
        config.write(configfile)
