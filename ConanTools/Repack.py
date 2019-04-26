import configparser
import tempfile
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

        Conan.run_build("install", [self._file_name],
                        remote=remote, profiles=profiles, build=build, cwd=cwd)


def extend_profile(inpath, outpath, build_requires):
    config = configparser.ConfigParser(allow_no_value=True)
    config.read([inpath])
    for x in build_requires:
        config["build_requires"][x] = None
    with open(outpath, 'w') as configfile:
        config.write(configfile)
