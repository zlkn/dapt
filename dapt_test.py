
#!/usr/bin/env python3

import unittest
from unittest import mock

import dapt


class DummyInstalled:
    def __init__(self, version):
        self.version = version


class DummyPkg:
    def __init__(self, name, is_installed, version="1.2.3"):
        self.name = name
        self.is_installed = is_installed
        if is_installed:
            self.installed = DummyInstalled(version)


class TestAptWrapper(unittest.TestCase):
    def verify_format_get_installed_package(self):
        pkgs = [
            DummyPkg("pkg_a", "0.1"),
            DummyPkg("pkg_c", "3.14"),
        ]
        with mock.patch.object(dapt.apt, "Cache", return_value=pkgs):
            wrapper = dapt.AptWrapper()
            installed = wrapper.get_installed_packages()

            self.assertEqual(installed, {
                "pkg_a": "0.1",
                "pkg_c": "3.14",
            })


class TestDApt(unittest.TestCase):
    def test_state_init(self):
        pass

class TestMainCommands(unittest.TestCase):
    def setUp(self):
        # track calls in each test
        self.calls = []

    def test_main_init_invokes_get_and_init(self):
        pass

if __name__ == "__main__":
    unittest.main()
