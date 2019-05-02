import ConanTools.Version


def test_out_of_repository(mocker):
    mocker.patch('ConanTools.Git.is_repository', return_value=False)
    assert ConanTools.Version.pep440("1.2.3") == "1.2.3"
    assert ConanTools.Version.semantic("2.3.4") == "2.3.4"


def test_in_repo_on_tag(mocker):
    mocker.patch('ConanTools.Git.is_repository', return_value=True)
    mocker.patch('ConanTools.Git.tag', return_value="5.0.0")
    assert ConanTools.Version.pep440("1.2.3") == "1.2.3"
    assert ConanTools.Version.semantic("2.3.4") == "2.3.4"


def test_in_repo_on_regular_commit(mocker):
    mocker.patch('ConanTools.Git.is_repository', return_value=True)
    mocker.patch('ConanTools.Git.tag', return_value=None)

    # Test when no tag has been found by describe and only the sha is returned.
    describe = mocker.patch('ConanTools.Git.describe',
                            return_value="1234567890123456789012345678901234567890")
    assert ConanTools.Version.pep440("1.2.3") == "1.2.3.dev0+g1234567890"
    assert ConanTools.Version.semantic("2.3.4") == "2.3.4-dev0+g1234567890"

    # Test disabling of the metadata by setting digits=0.
    assert ConanTools.Version.pep440("1.2.3", digits=0) == "1.2.3.dev0"
    assert ConanTools.Version.semantic("2.3.4", digits=0) == "2.3.4-dev0"

    # Test when a tag is found by describe.
    describe.return_value = "5.0.0-15-g1234567890123456789012345678901234567890"
    assert ConanTools.Version.pep440(
        "1.2.3", digits=40) == "5.0.0.post15+g1234567890123456789012345678901234567890"
    assert ConanTools.Version.semantic(
        "2.3.4", digits=40) == "5.0.0-post15+g1234567890123456789012345678901234567890"
