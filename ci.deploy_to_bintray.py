#!/usr/bin/env python3
import os
import ConanTools
import ConanTools.Git
import ConanTools.Conan as Conan

# Setup the default configuration but permit to override the configuration
# variables via the command line.
BINTRAY_API_KEY = os.environ["BINTRAY_API_KEY"]  # has to be defined in environment
BINTRAY_USER = os.environ.get("BINTRAY_USER", "nioshd")
CONAN_USER = os.environ.get("CONAN_USER", BINTRAY_USER)
CONAN_CHANNEL = os.environ.get("CONAN_CHANNEL",
                               "stable" if ConanTools.Git.tag() else "testing")
CONAN_REMOTE_NAME = os.environ.get("CONAN_REMOTE_NAME", "bintray_{}".format(BINTRAY_USER))

# Add the bintray remote and authenticate against it.
CONAN_REMOTE_URL = "https://api.bintray.com/conan/{}/conan".format(BINTRAY_USER)
Conan.run(["remote", "add", CONAN_REMOTE_NAME, CONAN_REMOTE_URL, "--insert", "0"])
Conan.run(["user", BINTRAY_USER, "-p", BINTRAY_API_KEY, "-r", CONAN_REMOTE_NAME])

# Build the package.
ref = Conan.Recipe("conanfile.py").create(user=CONAN_USER, channel=CONAN_CHANNEL)

# Upload the built package and recipe.
ref.upload_all(CONAN_REMOTE_NAME)

# Create an additional alias with the branch name slug and upload it too.
BRANCH_SLUG = ConanTools.slug(ConanTools.Git.branch())
if BRANCH_SLUG:
    alias_ref = ref.create_alias(version=BRANCH_SLUG)
    alias_ref.upload_all(CONAN_REMOTE_NAME)
