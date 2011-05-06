import errno
from unittest import TestCase
from mock import Mock
from cumulonimbus.fs import FS
from fuse import Direntry

class TestFS(TestCase):

    def setUp(self):
        self.mock_swift = self.prepare_mock_swift()
        self.fs = FS(self.mock_swift)

    def prepare_mock_swift(self):
        dir = Mock()
        dir.children = Mock()
        dir.children_names.return_value = []
        mock = Mock()
        mock.get = Mock()
        mock.get.return_value = dir
        return mock

class EmptyFS(TestFS):

    def test_opening_root_dir(self):
        self.assertIsNone(self.fs.opendir('/'))
        self.assertFalse(self.mock_swift.get.called)

    def test_opening_dir_with_incorrect_path(self):
        self.assertEquals(self.fs.opendir('dir'), -errno.EINVAL)
        self.assertFalse(self.mock_swift.get.called)

    def test_opening_empty_string_directory(self):
        self.assertEquals(self.fs.opendir(''), -errno.ENOENT)
        self.assertFalse(self.mock_swift.get.called)

    def test_opening_nonexistent_dir(self):
        self.assertEquals(self.fs.opendir('/no_such_directory'), -errno.ENOENT)
        self.assertTrue(self.mock_swift.get.called)

class SmallFS(TestFS):

    def prepare_mock_swift(self):
        """
        We're mocking a following directory structure:

          /
            dir1
            dir2
              dir3

        """
        swift = super(SmallFS, self).prepare_mock_swift()
        def get_side_effect(path):
            m = Mock()
            m.children_names.return_value = {
                    '/': ['dir1', 'dir2'],
                    '/dir1' : [],
                    '/dir2' : ['dir3'],
                    }[path]
            return m
        swift.get.side_effect = get_side_effect
        return swift

    def test_opening_dir(self):
        self.assertIsNone(self.fs.opendir('/dir1'))
        self.assertTrue(self.mock_swift.get.called)

    def test_opening_nonexistent_dir(self):
        self.assertEquals(self.fs.opendir('/no_such_directory'), -errno.ENOENT)
        self.assertTrue(self.mock_swift.get.called)

    def test_readdir_empty_dir(self):
        self.fs.opendir('/dir1')
        self.mock_swift.get.called = False
        entries_names = [ent.name for ent in self.fs.readdir('/dir1', 0, None)]
        entries_names.sort()
        self.assertEquals(entries_names, ['.', '..'])
        self.assertTrue(self.mock_swift.get.called)

    def test_readdir_dir(self):
        self.fs.opendir('/dir2')
        self.mock_swift.get.called = False
        entries_names = [ent.name for ent in self.fs.readdir('/dir2', 0, None)]
        entries_names.sort()
        self.assertEquals(entries_names, ['.', '..', 'dir3'])
        self.assertTrue(self.mock_swift.get.called)

    def test_readdir_root_dir(self):
        self.fs.opendir('/')
        self.mock_swift.get.called = False
        entries_names = [ent.name for ent in self.fs.readdir('/', 0, None)]
        entries_names.sort()
        self.assertEquals(entries_names, ['.', '..', 'dir1', 'dir2'])
        self.assertTrue(self.mock_swift.get.called)
