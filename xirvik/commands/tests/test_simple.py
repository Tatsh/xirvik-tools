"""Command line interface tests."""
from click.testing import CliRunner
import pytest
import requests_mock as req_mock

from ..root import xirvik

# pylint: disable=missing-function-docstring,protected-access,no-self-use,redefined-outer-name


@pytest.fixture()
def runner():
    return CliRunner()


def test_fix_rtorrent(requests_mock: req_mock.Mocker, runner: CliRunner):
    requests_mock.get('https://somehost.com:443/userpanel/index.php/services/'
                      'restart/rtorrent')
    result = runner.invoke(xirvik, ['rtorrent', 'fix', 'somehost.com'])
    assert result.exit_code == 0
