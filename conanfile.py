from conans import ConanFile
import os

# Import packages to make them usable via conan's `python_requires`.
from ConanTools import Conan, Git, Repack, Version
from ConanTools import *


class ConanToolsRecipe(ConanFile):
    name = "ConanTools"
    version = Version.semantic()
    description = "Helpers and tools that make working with conan (e.g., scripting) more convenient."
    url = "https://github.com/niosHD/ConanTools"
    license = "MIT"
    exports = 'ConanTools/*.py'
    build_policy = "missing"

    def package(self):
        self.copy('*.py')

    def package_info(self):
        self.env_info.PYTHONPATH = [os.path.join(self.package_folder)]
