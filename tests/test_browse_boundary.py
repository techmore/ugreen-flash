import tempfile
import unittest
from pathlib import Path

from app import app


class BrowseBoundaryTests(unittest.TestCase):
    def test_paths_cannot_escape_either_configured_root(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            local = base / 'local'
            nas = base / 'nas'
            outside = base / 'outside'
            for path in (local, nas, outside):
                path.mkdir()
            (local / 'safe.txt').write_text('safe')
            (local / 'nested').mkdir()
            (local / 'nested' / 'inside.txt').write_text('inside')
            (local / 'inside-link').symlink_to(local / 'nested', target_is_directory=True)
            (outside / 'private.txt').write_text('private')
            (local / 'escape').symlink_to(outside, target_is_directory=True)
            old = {key: app.config[key] for key in ('LOCAL_ROOT', 'NAS_ROOT')}
            app.config.update(LOCAL_ROOT=str(local), NAS_ROOT=str(nas), TESTING=True)
            try:
                with app.test_client() as client:
                    ok = client.get('/api/browse', query_string={'location': 'local'})
                    self.assertEqual(ok.status_code, 200)
                    self.assertIn('safe.txt', [x['name'] for x in ok.get_json()['items']])
                    inside = client.get('/api/browse', query_string={'location': 'local', 'path': 'inside-link'})
                    self.assertEqual(inside.status_code, 200)
                    self.assertIn('inside.txt', [x['name'] for x in inside.get_json()['items']])
                    for location, path in [('local', '../outside'), ('nas', '../outside'),
                                           ('local', str(outside)), ('local', 'escape')]:
                        with self.subTest(location=location, path=path):
                            result = client.get('/api/browse', query_string={'location': location, 'path': path})
                            self.assertEqual(result.status_code, 403)
            finally:
                app.config.update(old)


if __name__ == '__main__':
    unittest.main()
