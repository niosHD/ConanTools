#!/usr/bin/env python3
import os
import ConanTools
import ConanTools.Git
import ConanTools.Conan as Conan

# Setup the default configuration.
BINTRAY_API_KEY = os.environ["BINTRAY_API_KEY"]  # has to be defined in environment
BINTRAY_USER = "nioshd"
CONAN_CHANNEL = "testing"
if ConanTools.Git.tag():
    CONAN_CHANNEL = "stable"

# Permit to override the derived configuration variables via the command line.
BINTRAY_USER = os.environ.get("BINTRAY_USER", BINTRAY_USER)
CONAN_USER = os.environ.get("CONAN_USER", BINTRAY_USER)
CONAN_CHANNEL = os.environ.get("CONAN_CHANNEL", CONAN_CHANNEL)
CONAN_REMOTE_NAME = os.environ.get("CONAN_REMOTE_NAME", "bintray_{}".format(BINTRAY_USER))

# Build the package.
package = Conan.Reference(recipe="conanfile.py", user=CONAN_USER, channel=CONAN_CHANNEL)
package.create()

# Add the bintray remote and authenticate against it.
CONAN_REMOTE_URL = "https://api.bintray.com/conan/{}/conan".format(BINTRAY_USER)
Conan.run(["remote", "add", CONAN_REMOTE_NAME, CONAN_REMOTE_URL, "--insert", "0"])
Conan.run(["user", BINTRAY_USER, "-p", BINTRAY_API_KEY, "-r", CONAN_REMOTE_NAME])

# Upload the built package and recipe.
Conan.run(["upload", package.package_id(), "-r", CONAN_REMOTE_NAME, "--all", "-c"])

# Create an additional alias with the branch name slug and upload it too.
BRANCH_SLUG = ConanTools.slug(ConanTools.Git.branch())
if BRANCH_SLUG:
    Conan.run(["alias", package.package_id(version=BRANCH_SLUG), package.package_id()])
    Conan.run(["upload", package.package_id(version=BRANCH_SLUG),
              "-r", CONAN_REMOTE_NAME, "--all", "-c"])
