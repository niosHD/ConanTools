#!/usr/bin/env python3
import os
import ConanTools
import ConanTools.Git
import ConanTools.Conan as Conan

# Setup script config from environment.
BINTRAY_USER = os.environ.get("BINTRAY_USER", "nioshd")
BINTRAY_API_KEY = os.environ["BINTRAY_API_KEY"]  # has to be defined in environment
CONAN_USER = os.environ.get("CONAN_USER", BINTRAY_USER)
CONAN_CHANNEL = os.environ.get("CONAN_CHANNEL", "testing")
CONAN_REMOTE_NAME = os.environ.get("CONAN_REMOTE_NAME", "bintray_{}".format(BINTRAY_USER))
CONAN_REMOTE_URL = "https://api.bintray.com/conan/{}/conan".format(BINTRAY_USER)

# Build the package.
package = Conan.PID(recipe="conanfile.py", user=CONAN_USER, channel=CONAN_CHANNEL)
package.create()

# Add the bintray remote and authenticate against it.
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
