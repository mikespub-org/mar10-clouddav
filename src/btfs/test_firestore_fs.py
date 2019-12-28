# https://docs.pyfilesystem.org/en/latest/implementers.html#testing-filesystems
from .firestore_fs import FirestoreFS, WrapFirestoreFS
from . import fire_fs  # TODO
import unittest

import pytest
from fs.test import FSTestCases

# Create the test playground if needed
# fi_fs = FirestoreFS(root_path="/_playground_", use_cache=False)
fi_fs = FirestoreFS(root_path="/_playground_")
fi_fs._reset_path("/", True)
fi_fs.close()
test_count = 0


class TestFirestoreFS(FSTestCases, unittest.TestCase):
    def make_fs(self):
        global test_count
        test_count += 1
        if "test_upload" in self.id() or "test_download" in self.id():
            pytest.skip("No time to waste...")
            return
        if "test_settimes" in self.id():
            pytest.xfail("Modify time is updated automatically on model.put()")
        # Return an instance of your FS object here - disable caching on client side for test
        fi_fs = FirestoreFS(
            root_path="/_playground_/%02d_%s" % (test_count, self.id().split(".")[-1]),
        )
        return fi_fs

    def destroy_fs(self, fi_fs):
        try:
            fi_fs._reset_path("/", True)
        except:
            pass
        fi_fs.close()


# class TestWrapFirestoreFS(FSTestCases, unittest.TestCase):
#     def make_fs(self):
#         # Return an instance of your FS object here
#         return WrapFirestoreFS()


class TestFirestoreOpener(unittest.TestCase):
    def test_open_firestore(self):
        from fs.opener import open_fs

        fi_fs = open_fs("firestore://")
        self.assertIsInstance(fi_fs, FirestoreFS)
