from ConanTools import Conan
from contextlib import redirect_stdout
import io
import pytest


@pytest.fixture
def mock_run(mocker):
    # Mock the run method that is used internally to execute conan commands.
    run_ret = mocker.Mock()
    mocker.patch('os.makedirs')
    mocker.patch('subprocess.run', return_value=run_ret)
    return run_ret


def test_reference_string_formatting_and_clone():
    ref = Conan.Reference("foo", "1.2.3", "bar", "testing")
    assert str(ref) == "foo/1.2.3@bar/testing"

    # Test cloning and formatting for cloned references.
    cpy = ref.clone(name="bla")
    assert ref is not cpy
    assert str(cpy) == "bla/1.2.3@bar/testing"

    # Ensure that the original reference has not been modified.
    assert str(ref) == "foo/1.2.3@bar/testing"


def test_reference_in_local_cache(mock_run):
    ref = Conan.Reference("foo", "1.2.3", "bar", "testing")

    # Test call when reference is not in the local cache.
    mock_run.returncode = 1
    output = io.StringIO()
    with redirect_stdout(output):
        assert ref.in_local_cache() is False
    assert "$ conan search foo/1.2.3@bar/testing" in output.getvalue()

    # Test call when reference is in the local cache.
    mock_run.returncode = 0
    output = io.StringIO()
    with redirect_stdout(output):
        assert ref.in_local_cache() is True
    assert "$ conan search foo/1.2.3@bar/testing" in output.getvalue()


def test_reference_in_remote(mock_run):
    ref = Conan.Reference("foo", "1.2.3", "bar", "testing")

    # Test call when reference is not in the remote.
    mock_run.returncode = 1
    output = io.StringIO()
    with redirect_stdout(output):
        assert ref.in_remote("bar") is False
    assert "$ conan search foo/1.2.3@bar/testing --remote bar" in output.getvalue()

    # Test call when reference is in the remote.
    mock_run.returncode = 0
    output = io.StringIO()
    with redirect_stdout(output):
        assert ref.in_remote("bar") is True
    assert "$ conan search foo/1.2.3@bar/testing --remote bar" in output.getvalue()


def test_reference_download_recipe(mock_run):
    ref = Conan.Reference("foo", "1.2.3", "bar", "testing")

    # Test call when recipe could not be downloaded.
    mock_run.returncode = 1
    output = io.StringIO()
    with redirect_stdout(output):
        with pytest.raises(ValueError):
            ref.download_recipe()
    assert "$ conan download foo/1.2.3@bar/testing --recipe" in output.getvalue()

    # Test call when recipe could be downloaded.
    mock_run.returncode = 0
    output = io.StringIO()
    with redirect_stdout(output):
        ref.download_recipe("bar")
    assert "$ conan download foo/1.2.3@bar/testing --recipe --remote bar" in output.getvalue()


def test_reference_install(mock_run):
    ref = Conan.Reference("foo", "1.2.3", "bar", "testing")

    # Test call when the package could not be installed.
    mock_run.returncode = 1
    output = io.StringIO()
    with redirect_stdout(output):
        with pytest.raises(ValueError):
            ref.install(remote="baz", profiles=['a.p'], options={"key": True}, cwd="/foo/bar")
    assert ("[/foo/bar] $ conan install foo/1.2.3@bar/testing "
            "--profile a.p --build outdated --remote baz -o key=True") == output.getvalue().strip()

    # Test call when the package could be installed.
    mock_run.returncode = 0
    output = io.StringIO()
    with redirect_stdout(output):
        ref.install(build="foo")
    assert "$ conan install foo/1.2.3@bar/testing --build foo" in output.getvalue()


def test_reference_set_remote(mock_run):
    ref = Conan.Reference("foo", "1.2.3", "bar", "testing")

    # Test call when the remote could not be set.
    mock_run.returncode = 1
    output = io.StringIO()
    with redirect_stdout(output):
        with pytest.raises(ValueError):
            ref.set_remote(remote="baz")
    assert "$ conan remote add_ref foo/1.2.3@bar/testing baz" in output.getvalue()

    # Test call when the remote could not be set.
    mock_run.returncode = 0
    output = io.StringIO()
    with redirect_stdout(output):
        ref.set_remote(remote="baz")
    assert "$ conan remote add_ref foo/1.2.3@bar/testing baz" in output.getvalue()


def test_reference_create_alias(mock_run):
    ref = Conan.Reference("foo", "1.2.3", "bar", "testing")

    # Test call when the alias could not be created.
    mock_run.returncode = 1
    output = io.StringIO()
    with redirect_stdout(output):
        with pytest.raises(ValueError):
            ref.create_alias(version="develop", user="baz")
    assert "$ conan alias foo/develop@baz/testing foo/1.2.3@bar/testing" in output.getvalue()

    # Test call when the alias could not be created.
    mock_run.returncode = 0
    output = io.StringIO()
    with redirect_stdout(output):
        alias = ref.create_alias(version="develop", user="baz")
    assert "$ conan alias foo/develop@baz/testing foo/1.2.3@bar/testing" in output.getvalue()
    assert alias is not ref


def test_reference_upload_all(mock_run):
    ref = Conan.Reference("foo", "1.2.3", "bar", "testing")

    # Test call when the package could not be uploaded.
    mock_run.returncode = 1
    output = io.StringIO()
    with redirect_stdout(output):
        with pytest.raises(ValueError):
            ref.upload_all(remote="baz")
    assert "$ conan upload foo/1.2.3@bar/testing --remote baz --all -c" in output.getvalue()

    # Test call when the package could be uploaded.
    mock_run.returncode = 0
    output = io.StringIO()
    with redirect_stdout(output):
        ref.upload_all(remote="baz")
    assert "$ conan upload foo/1.2.3@bar/testing --remote baz --all -c" in output.getvalue()
