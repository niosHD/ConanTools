from conans import ConanFile
import os

# Import packages to make them usable via conan's `python_requires`.
from ConanTools import Conan, Git, Repack, Version


class ConanToolsRecipe(ConanFile):
    name = "ConanTools"
    version = Version.semantic()
    exports = 'ConanTools/*.py'
    build_policy = "missing"

    def package(self):
        self.copy('*.py')

    def package_info(self):
        self.env_info.PYTHONPATH = [os.path.join(self.package_folder)]
