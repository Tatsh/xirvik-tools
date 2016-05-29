import unittest

from bencodepy import encode as bencode



def create_torrent(path, save_to=None, piece_length=256):
    pass


def create_random_data_file(path, size=2306867):
    """size is intentionally a non-power of 2"""


class TestTorrentVerfication(unittest.TestCase):
    def setUp(self):
        self.torrent_data = bencode({
            b'info': {
                b'name': 'Test torrent',
                b'piece length': 20,
                b'pieces': '',
                b'files': [
                    {
                        b'path': '',
                    },
                ],
            }
        })

    #def test_verify_torrent_contents(self):
        #verify_torrent_contents()


if __name__ == '__main__':
    unittest.main()
