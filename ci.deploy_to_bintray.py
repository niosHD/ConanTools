#!/usr/bin/env python3
import os
import ConanTools.Git as Git
import ConanTools.Repack as Repack
import ConanTools.Version as Version

# Setup script config from environment.
BINTRAY_USER = os.environ.get("BINTRAY_USER", "nioshd")
BINTRAY_API_KEY = os.environ["BINTRAY_API_KEY"]  # has to be defined in environment
CONAN_USER = os.environ.get("CONAN_USER", BINTRAY_USER)
CONAN_CHANNEL = os.environ.get("CONAN_CHANNEL", "testing")
CONAN_REMOTE_NAME = os.environ.get("CONAN_REMOTE_NAME", "bintray_{}".format(BINTRAY_USER))
CONAN_REMOTE_URL = "https://api.bintray.com/conan/{}/conan".format(BINTRAY_USER)
BRANCH_SLUG = Git.slug(Git.get_branch())

# Build the package.
package = Repack.PID(recipe="conanfile.py", user=CONAN_USER, channel=CONAN_CHANNEL)
package.create()

# Add the bintray remote and authenticate against it.
Repack.run(["conan", "remote", "add", CONAN_REMOTE_NAME, CONAN_REMOTE_URL, "--insert", "0"])
Repack.run(["conan", "user", BINTRAY_USER, "-p", BINTRAY_API_KEY, "-r", CONAN_REMOTE_NAME])

# Upload the built package and recipe.
Repack.run(["conan", "upload", package.package_id(), "-r", CONAN_REMOTE_NAME, "--all", "-c"])

# Create an additional alias with the branch name slug and upload it too.
Repack.run(["conan", "alias",
            package.package_id(version=BRANCH_SLUG),
            package.package_id()])
Repack.run(["conan", "upload",
            package.package_id(version=BRANCH_SLUG), "-r", CONAN_REMOTE_NAME, "--all", "-c"])
