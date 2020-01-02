# https://docs.pyfilesystem.org/en/latest/implementers.html#testing-filesystems
from mapper.fs_from_dav_provider import DAVProvider2FS
from data.datastore_dav import DatastoreDAVProvider
import unittest

import pytest
from fs.test import FSTestCases

# Create the test playground if needed
dav_provider = DatastoreDAVProvider()
dav_fs = DAVProvider2FS(dav_provider)
dav_fs.environ["wsgidav.auth.user_name"] = "tester"
dav_fs.environ["wsgidav.auth.roles"] = ["admin"]
path = "/_playground_"
dav_fs.removetree(path)
dav_fs.makedir(path, recreate=True)
test_count = 0


class TestDatastoreFS(FSTestCases, unittest.TestCase):
    def make_fs(self):
        global test_count
        test_count += 1
        test_name = self.id().split(".")[-1]
        if test_name in ("test_upload", "test_download"):
            pytest.skip("No time to waste...")
            return
        if test_name in ("test_appendbytes", "test_appendtext"):
            pytest.xfail("Appending is not supported")
        if test_name in ("test_bin_files", "test_files", "test_open_files"):
            pytest.xfail("Updating is not supported")
        if test_name in ("test_invalid_chars"):
            pytest.xfail("TODO: get list of invalid characters from the DAV Provider")
        if test_name in ("test_settimes", "test_setinfo", "test_touch"):
            pytest.xfail("Modify time is updated automatically on model.put()")
        # Return an instance of your FS object here - disable caching on client side for test
        dav_provider = DatastoreDAVProvider()
        dav_fs = DAVProvider2FS(dav_provider)
        dav_fs.environ["wsgidav.auth.user_name"] = "tester"
        dav_fs.environ["wsgidav.auth.roles"] = ["admin"]
        path = "/_playground_/%02d_%s" % (test_count, test_name)
        dav_fs.makedir(path, recreate=True)
        data_fs = dav_fs.opendir(path)
        return data_fs

    def destroy_fs(self, data_fs):
        try:
            # data_fs._reset_path("/", True)
            data_fs.removetree("/")
        except:
            pass
        data_fs.close()
