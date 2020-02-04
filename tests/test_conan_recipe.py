from ConanTools import Conan
from contextlib import redirect_stdout
import io
import json
import pytest


inspectJSON = """
{"name": "ConanTools",
 "version": "0.1.1-post7+ga21edb7f08",
 "url": "https://github.com/niosHD/ConanTools",
 "homepage": null,
 "license": "MIT",
 "author": null,
 "description": "Helpers and tools that make working with conan (e.g., scripting) more convenient.",
 "topics": null,
 "generators": ["txt"],
 "exports": "ConanTools/*.py",
 "exports_sources": null,
 "short_paths": false,
 "apply_env": true,
 "build_policy": "missing",
 "revision_mode": "hash",
 "settings": null,
 "options": null,
 "no_copy_source": true,
 "default_options": null}
"""


@pytest.fixture
def mock_inspect(mocker):
    # Mock the methods that are used internally to inspect a conanfile.
    mocker.patch('tempfile.NamedTemporaryFile')
    mocker.patch('subprocess.check_call')
    mocker.patch('builtins.open')
    mocker.patch('os.unlink')
    mocker.patch('json.load', return_value=json.loads(inspectJSON))


@pytest.fixture
def mock_run(mocker):
    # Mock the run method that is used internally to execute conan commands.
    run_ret = mocker.Mock()
    mocker.patch('os.makedirs')
    mocker.patch('subprocess.run', return_value=run_ret)
    mocker.patch('distutils.dir_util.copy_tree')
    mocker.patch('shutil.rmtree')
    return run_ret


def test_recipe_get_field(mock_inspect):
    recipe = Conan.Recipe("foobar.py")
    assert recipe.get_field("name") == "ConanTools"
    assert recipe.get_field("version") == "0.1.1-post7+ga21edb7f08"
    assert recipe.get_field("url") == "https://github.com/niosHD/ConanTools"
    assert recipe.get_field("license") == "MIT"

    recipe = Conan.Recipe("foobar.py", cwd="/tmp")
    assert recipe.get_field("generators") == ["txt"]


def test_get_recipe_field(mocker, mock_inspect):
    assert Conan.get_recipe_field("does_not_exist.py", "name") is None

    mocker.patch('os.path.exists', return_value=True)
    assert Conan.get_recipe_field("a.py", "name") == "ConanTools"
    assert Conan.get_recipe_field("a.py", "version") == "0.1.1-post7+ga21edb7f08"


def test_recipe_reference(mock_inspect):
    recipe = Conan.Recipe("foobar.py")
    ref = recipe.reference("foo", "testing")
    assert ref.name == "ConanTools"
    assert ref.version == "0.1.1-post7+ga21edb7f08"
    assert ref.user == "foo"
    assert ref.channel == "testing"

    ref = recipe.reference("foo", "testing", name="pkg", version="1.2.3")
    assert ref.name == "pkg"
    assert ref.version == "1.2.3"


def test_recipe_export(mock_run, mock_inspect):
    # Test call when export fails.
    recipe = Conan.Recipe("/foobar.py")
    mock_run.returncode = 1
    output = io.StringIO()
    with redirect_stdout(output):
        with pytest.raises(ValueError):
            recipe.export("foo", "testing", version="1.1.1")
    assert "$ conan export /foobar.py ConanTools/1.1.1@foo/testing" in output.getvalue()

    # Test call when export succeeds.
    recipe = Conan.Recipe("foobar.py", cwd="/tmp")
    mock_run.returncode = 0
    output = io.StringIO()
    with redirect_stdout(output):
        recipe.export("bar", "testing", version="1.1.1")
    assert "$ conan export /tmp/foobar.py ConanTools/1.1.1@bar/testing" in output.getvalue()


def test_recipe_create(mock_run, mock_inspect):
    # Test call when create fails.
    recipe = Conan.Recipe("/foobar.py")
    mock_run.returncode = 1
    output = io.StringIO()
    with redirect_stdout(output):
        with pytest.raises(ValueError):
            recipe.create("bar", "testing", remote="baz", profiles=['a.p'], cwd="/foo/fizz")
    assert ("[/foo/fizz] $ conan create /foobar.py ConanTools/0.1.1-post7+ga21edb7f08@bar/testing "
            "--profile a.p --build outdated --remote baz") == output.getvalue().strip()

    # Test call when create succeeds.
    recipe = Conan.Recipe("foobar.py", cwd="/tmp")
    mock_run.returncode = 0
    output = io.StringIO()
    with redirect_stdout(output):
        recipe.create("bar", "testing", version="5.6.8", build="foo", options={"key": True})
    assert "$ conan create /tmp/foobar.py ConanTools/5.6.8@bar/testing --build foo -o key=True" \
        in output.getvalue()


def test_recipe_install(mock_run):
    # Test call when install fails.
    recipe = Conan.Recipe("/foobar.py")
    mock_run.returncode = 1
    output = io.StringIO()
    with redirect_stdout(output):
        with pytest.raises(ValueError):
            recipe.install(build_folder="/build", profiles=['a.p'], options={"key": True},
                           remote="baz")
    assert ("[/build] $ conan install /foobar.py "
            "--profile a.p --build outdated --remote baz -o key=True") == output.getvalue().strip()

    # Test call when install succeeds.
    recipe = Conan.Recipe("foobar.py", cwd="/tmp")
    mock_run.returncode = 0
    output = io.StringIO()
    with redirect_stdout(output):
        recipe.install()
    assert ("[/tmp/_build] $ conan install /tmp/foobar.py "
            "--build outdated") == output.getvalue().strip()


def test_recipe_source(mock_run):
    # Test call when install fails.
    recipe = Conan.Recipe("/foobar.py")
    mock_run.returncode = 1
    output = io.StringIO()
    with redirect_stdout(output):
        with pytest.raises(ValueError):
            recipe.source(src_folder="/src", build_folder="/build")
    assert ("[/build] $ conan source /foobar.py "
            "--source-folder=/src") == output.getvalue().strip()

    # Test call when source succeeds.
    recipe = Conan.Recipe("foobar.py", cwd="/tmp")
    mock_run.returncode = 0
    output = io.StringIO()
    with redirect_stdout(output):
        recipe.source(src_folder="src")
    assert ("[/tmp/_build] $ conan source /tmp/foobar.py "
            "--source-folder=src") == output.getvalue().strip()


def test_recipe_build(mock_run, mock_inspect):
    # Test call when build fails.
    recipe = Conan.Recipe("/foobar.py")
    mock_run.returncode = 1
    output = io.StringIO()
    with redirect_stdout(output):
        with pytest.raises(ValueError):
            recipe.build(src_folder="/src", build_folder="/build", pkg_folder="/pkg")
    assert ("[/build] $ conan build /foobar.py --source-folder=/src "
            "--package-folder=/pkg") == output.getvalue().strip()

    # Test call when build succeeds.
    recipe = Conan.Recipe("foobar.py", cwd="/tmp")
    mock_run.returncode = 0
    output = io.StringIO()
    with redirect_stdout(output):
        recipe.build()
    assert ("[/tmp/_build] $ conan build /tmp/foobar.py --source-folder=/tmp "
            "--package-folder=/tmp/_install") == output.getvalue().strip()


def test_recipe_package(mock_run):
    # Test call when package fails.
    recipe = Conan.Recipe("/foobar.py")
    mock_run.returncode = 1
    output = io.StringIO()
    with redirect_stdout(output):
        with pytest.raises(ValueError):
            recipe.package(src_folder="/src", build_folder="/build", pkg_folder="/pkg")
    assert ("[/build] $ conan package /foobar.py --source-folder=/src "
            "--package-folder=/pkg") == output.getvalue().strip()

    # Test call when package succeeds.
    recipe = Conan.Recipe("foobar.py", cwd="/tmp")
    mock_run.returncode = 0
    output = io.StringIO()
    with redirect_stdout(output):
        recipe.package()
    assert ("[/tmp/_build] $ conan package /tmp/foobar.py --source-folder=/tmp "
            "--package-folder=/tmp/_install") == output.getvalue().strip()


def test_recipe_export_pkg(mock_run, mock_inspect):
    # Test call when export_pkg fails.
    recipe = Conan.Recipe("/foobar.py")
    mock_run.returncode = 1
    output = io.StringIO()
    with redirect_stdout(output):
        with pytest.raises(ValueError):
            recipe.export_pkg("bar", "testing", profiles=['a.p'], pkg_folder="/tmp/pkg", cwd="/ab")
    assert ("[/ab] $ conan export-pkg /foobar.py ConanTools/0.1.1-post7+ga21edb7f08@bar/testing "
            "--package-folder=/tmp/pkg --profile a.p") == output.getvalue().strip()

    # Test call when export_pkg succeeds.
    recipe = Conan.Recipe("foobar.py", cwd="/tmp")
    mock_run.returncode = 0
    output = io.StringIO()
    with redirect_stdout(output):
        recipe.export_pkg("bar", "testing", version="5.6.8", options={"key": True},
                          pkg_folder="/tmp/pkg", cwd="/tmp/_build")
    assert ("[/tmp/_build] $ conan export-pkg /tmp/foobar.py ConanTools/5.6.8@bar/testing "
            "--package-folder=/tmp/pkg -o key=True") in output.getvalue()


def test_recipe_create_local(mock_run, mock_inspect):
    # Test call when export_pkg fails.
    recipe = Conan.Recipe("/foobar.py", external_source=True)
    mock_run.returncode = 0
    output = io.StringIO()
    with redirect_stdout(output):
        recipe.create_local("user", "channel")
    commands = output.getvalue().strip().splitlines()
    assert "[/_build] $ conan install /foobar.py --build outdated" == commands[0]
    assert "[/_build] $ conan source /foobar.py --source-folder=/_source" == commands[1]
    assert ("[/_build] $ conan build /foobar.py --source-folder=/_source "
            "--package-folder=/_install") == commands[2]
    assert ("[/_build] $ conan package /foobar.py --source-folder=/_source "
            "--package-folder=/_install") == commands[3]
    assert ("$ conan export-pkg /foobar.py ConanTools/0.1.1-post7+ga21edb7f08@user/channel "
            "--package-folder=/_install") in commands[4]
