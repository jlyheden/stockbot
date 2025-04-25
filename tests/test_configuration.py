import unittest
import os

from stockbot.configuration import Configuration
from unittest.mock import patch


class TestConfiguration(unittest.TestCase):

    @patch.dict(os.environ, {'SERVER_NAME': 'foo'})
    def test_get_env_successful(self):
        self.assertEquals("foo", Configuration().server_name)

    @patch.dict(os.environ, {})
    def test_get_env_fail_without_default(self):
        with self.assertRaisesRegex(RuntimeError, "Must set environment variable SERVER_NAME"):
            Configuration().server_name

    @patch.dict(os.environ, {})
    def test_get_env_fail_with_default(self):
        Configuration().scheduler

    @patch.dict(os.environ, {'BOOL_TRUE': 'true', 'BOOL_FALSE': 'false'})
    def test_get_env_bool(self):
        self.assertEquals(True, Configuration().bool_true)
        self.assertEquals(False, Configuration().bool_false)

    @patch.dict(os.environ, {'GAME_IGNORE_LIST': '[G1],[G2]'})
    def test_get_env_list(self):
        self.assertEquals(["[G1]", "[G2]"], Configuration().game_ignore_list)

    def test_get_empty_env_list(self):
        self.assertEquals([], Configuration().game_ignore_list)
