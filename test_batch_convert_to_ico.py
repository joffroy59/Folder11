import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import batch_convert_to_ico as converter


class ChangedSvgTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'svg_custom'
        self.output = self.root / 'ico_custom'
        self.source.mkdir()
        self.output.mkdir()

    def convert(self, filename, changes=('', '', ''), input_folder=None, repo_root=None):
        with patch.object(converter.subprocess, 'check_output', side_effect=[
            str(repo_root or self.root), *changes
        ]) as git_query, patch.object(converter.subprocess, 'run') as magick, patch.object(
            converter, '__file__', str(self.root / 'converter.py')
        ):
            converter.convert_svg_to_ico(
                str(input_folder or self.source), str(self.output), (16,), only_changed=True
            )
        for call in git_query.call_args_list[1:]:
            self.assertIn('-z', call.args[0])
            self.assertEqual(call.kwargs['encoding'], 'utf-8')
        outputs = [call.args[0][-1] for call in magick.call_args_list]
        return str(self.output / (Path(filename).stem + '.ico')) in outputs

    def test_missing_ico_is_generated_even_without_git_changes(self):
        (self.source / 'new.svg').touch()
        self.assertTrue(self.convert('new.svg'))

    def test_unchanged_svg_with_existing_ico_is_skipped(self):
        (self.source / 'existing.svg').touch()
        (self.output / 'existing.ico').touch()
        self.assertFalse(self.convert('existing.svg'))

    def test_unstaged_staged_and_untracked_svg_names(self):
        filename = 'folder caf\u00e9 logo.svg'
        (self.source / filename).touch()
        (self.output / (Path(filename).stem + '.ico')).touch()
        for index in range(3):
            with self.subTest(index=index):
                changes = ['', '', '']
                changes[index] = 'svg_custom/' + filename + '\0'
                self.assertTrue(self.convert(filename, changes))

    def test_relative_input_folder(self):
        (self.source / 'relative.svg').touch()
        (self.output / 'relative.ico').touch()
        self.assertTrue(self.convert(
            'relative.svg', ('svg_custom/relative.svg\0', '', ''),
            input_folder=os.path.relpath(self.source)
        ))

    @unittest.skipUnless(os.name == 'nt', 'Windows path casing')
    def test_windows_path_casing(self):
        (self.source / 'case.svg').touch()
        (self.output / 'case.ico').touch()
        self.assertTrue(self.convert(
            'case.svg', ('svg_custom/case.svg\0', '', ''),
            repo_root=str(self.root).upper()
        ))

    @unittest.skipUnless(os.name == 'nt', 'Windows directory junction')
    def test_windows_junction_input_folder(self):
        import _winapi

        alias = self.root / 'alias'
        _winapi.CreateJunction(str(self.source), str(alias))
        self.addCleanup(os.rmdir, alias)
        (self.source / 'junction.svg').touch()
        (self.output / 'junction.ico').touch()
        self.assertTrue(self.convert(
            'junction.svg', ('svg_custom/junction.svg\0', '', ''), input_folder=alias
        ))

    def test_git_failure_does_not_raise_unbound_repo_root(self):
        (self.source / 'fallback.svg').touch()
        with (
            patch.object(converter.subprocess, 'check_output', side_effect=subprocess.CalledProcessError(1, 'git')),
            patch.object(converter.subprocess, 'run') as magick,
            patch.object(converter, '__file__', str(self.root / 'converter.py'))
        ):
            converter.convert_svg_to_ico(str(self.source), str(self.output), (16,), only_changed=True)
        self.assertEqual(magick.call_count, 2)


if __name__ == '__main__':
    unittest.main()