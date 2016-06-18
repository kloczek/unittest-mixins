# -*- coding: utf-8 -*-
# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/nedbat/unittest-mixins/blob/master/NOTICE.txt

"""Tests that our test infrastructure is really working!"""

import os
import os.path
import re
import shutil
import sys
import tempfile
import textwrap
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import six

from unittest_mixins import (
    change_dir,
    DelayedAssertionMixin,
    EnvironmentAwareMixin,
    StdStreamCapturingMixin,
    TempDirMixin,
)


class ChangeDirTest(unittest.TestCase):
    """Test the change_dir decorator."""
    def setUp(self):
        super(ChangeDirTest, self).setUp()
        self.root = tempfile.mkdtemp(prefix="change_dir_test")
        self.addCleanup(shutil.rmtree, self.root)
        self.a_dir = os.path.join(self.root, "a_dir")
        os.mkdir(self.a_dir)
        self.b_dir = os.path.join(self.root, "b_dir")
        os.mkdir(self.b_dir)

    def assert_same_file(self, f1, f2):
        """Assert that f1 and f2 are the same file."""
        self.assertEqual(os.path.realpath(f1), os.path.realpath(f2))

    def assert_different_file(self, f1, f2):
        """Assert that f1 and f2 are not the same file."""
        self.assertNotEqual(os.path.realpath(f1), os.path.realpath(f2))

    def test_change_dir(self):
        here = os.getcwd()
        self.assert_different_file(here, self.root)
        with change_dir(self.root):
            self.assert_same_file(os.getcwd(), self.root)
        self.assert_same_file(os.getcwd(), here)

    def test_change_dir_twice(self):
        here = os.getcwd()
        self.assert_different_file(here, self.root)
        with change_dir(self.root):
            self.assert_same_file(os.getcwd(), self.root)
            os.chdir("a_dir")
            self.assert_same_file(os.getcwd(), self.a_dir)
        self.assert_same_file(os.getcwd(), here)

    def test_change_dir_with_exception(self):
        here = os.getcwd()
        self.assert_different_file(here, self.root)
        try:
            with change_dir(self.root):
                self.assert_same_file(os.getcwd(), self.root)
                raise ValueError("hi")
        except ValueError:
            pass
        self.assert_same_file(os.getcwd(), here)


class TempDirMixinTest(TempDirMixin, unittest.TestCase):
    """Test the methods in TempDirMixin."""

    def file_text(self, fname):
        """Return the text read from a file."""
        with open(fname, "rb") as f:
            return f.read().decode('ascii')

    def test_make_file(self):
        # A simple file.
        self.make_file("fooey.boo", "Hello there")
        self.assertEqual(self.file_text("fooey.boo"), "Hello there")
        # A file in a sub-directory
        self.make_file("sub/another.txt", "Another")
        self.assertEqual(self.file_text("sub/another.txt"), "Another")
        # A second file in that sub-directory
        self.make_file("sub/second.txt", "Second")
        self.assertEqual(self.file_text("sub/second.txt"), "Second")
        # A deeper directory
        self.make_file("sub/deeper/evenmore/third.txt")
        self.assertEqual(self.file_text("sub/deeper/evenmore/third.txt"), "")

    def test_make_file_newline(self):
        self.make_file("unix.txt", "Hello\n")
        self.assertEqual(self.file_text("unix.txt"), "Hello\n")
        self.make_file("dos.txt", "Hello\n", newline="\r\n")
        self.assertEqual(self.file_text("dos.txt"), "Hello\r\n")
        self.make_file("mac.txt", "Hello\n", newline="\r")
        self.assertEqual(self.file_text("mac.txt"), "Hello\r")

    def test_make_file_non_ascii(self):
        self.make_file("unicode.txt", "tabblo: «ταБЬℓσ»")
        with open("unicode.txt", "rb") as f:
            text = f.read()
        self.assertEqual(
            text,
            b"tabblo: \xc2\xab\xcf\x84\xce\xb1\xd0\x91\xd0\xac\xe2\x84\x93\xcf\x83\xc2\xbb"
        )


class EnvironmentAwareMixinTest(EnvironmentAwareMixin, unittest.TestCase):
    """Tests of test_helpers.EnvironmentAwareMixin."""

    def setUp(self):
        super(EnvironmentAwareMixinTest, self).setUp()

        # Find a pre-existing environment variable.
        # Not sure what environment variables are available in all of our
        # different testing environments, so try a bunch.
        for envvar in ["HOME", "HOMEDIR", "USER", "SYSTEMDRIVE", "TEMP"]:   # pragma: no branch
            if envvar in os.environ:                                        # pragma: no branch
                self.envvar = envvar
                self.original_text = os.environ[envvar]
                break

    def test_setting_and_cleaning_existing_env_vars(self):
        self.assertNotEqual(self.original_text,  "Some Strange Text")

        # Change the environment.
        self.set_environ(self.envvar, "Some Strange Text")
        self.assertEqual(os.environ[self.envvar],  "Some Strange Text")

        # Do the clean ups early.
        self.doCleanups()

        # The environment should be restored.
        self.assertEqual(os.environ[self.envvar], self.original_text)

    def test_setting_and_cleaning_existing_env_vars_twice(self):
        self.assertNotEqual(self.original_text,  "Some Strange Text")

        # Change the environment.
        self.set_environ(self.envvar, "Some Strange Text")
        self.assertEqual(os.environ[self.envvar],  "Some Strange Text")

        # Change the environment again.
        self.set_environ(self.envvar, "Some Other Thing")
        self.assertEqual(os.environ[self.envvar],  "Some Other Thing")

        # Do the clean ups early.
        self.doCleanups()

        # The environment should be restored.
        self.assertEqual(os.environ[self.envvar], self.original_text)

    def test_setting_and_cleaning_nonexisting_env_vars(self):
        self.assertNotIn("XYZZY_PLUGH", os.environ)

        # Change the environment.
        self.set_environ("XYZZY_PLUGH", "Vogon")

        self.assertEqual(os.environ["XYZZY_PLUGH"], "Vogon")

        # Do the clean ups early.
        self.doCleanups()

        # The environment should be restored.
        self.assertNotIn("XYZZY_PLUGH", os.environ)


class DelayedAssertionMixinTest(DelayedAssertionMixin, unittest.TestCase):
    """Test the `delayed_assertions` method."""

    def test_two_delayed_assertions(self):
        # Two assertions can be shown at once:
        msg = re.escape(textwrap.dedent("""\
            2 failed assertions:
            'x' != 'y'
            - x
            + y

            'w' != 'z'
            - w
            + z
            """))
        with six.assertRaisesRegex(self, AssertionError, msg):
            with self.delayed_assertions():
                self.assertEqual("x", "y")
                self.assertEqual("w", "z")

    def test_only_one_fails(self):
        # It's also OK if only one fails:
        msg = re.escape(textwrap.dedent("""\
            'w' != 'z'
            - w
            + z
            """))
        with six.assertRaisesRegex(self, AssertionError, msg):
            with self.delayed_assertions():
                self.assertEqual("x", "x")
                self.assertEqual("w", "z")

    def test_non_assert_error(self):
        # If an error happens, it gets reported immediately, no special
        # handling:
        with self.assertRaises(ZeroDivisionError):
            with self.delayed_assertions():
                self.assertEqual("x", "y")
                self.assertEqual("w", 1/0)

    def test_no_problem_at_all(self):
        # If all assert pass, then all is well:
        with self.delayed_assertions():
            self.assertEqual("x", "x")
            self.assertEqual("y", "y")


def run_tests_from_class(klass):
    """Run the unittest tests in klass, and return a TestResult."""
    suite = unittest.TestLoader().loadTestsFromTestCase(klass)
    results = unittest.TestResult()
    suite.run(results)
    return results


def assert_all_passed(results, tests_run):
    assert results.testsRun == tests_run
    assert results.failures == []
    assert results.errors == []
    assert results.skipped == []


class RunTestsFromClassTest(unittest.TestCase):
    """Tests of the run_tests_from_class function."""

    class TheTestsToTest(unittest.TestCase):
        """Sample tests to test the run_tests_from_class function."""

        def test_pass(self):
            self.assertEqual(1, 1)

        def test_fail(self):
            self.assertEqual(1, 0)

        def test_skip(self):
            self.skipTest("I feel like it")

        def test_error(self):
            raise Exception("BOOM")

    def test_the_tests_to_test(self):
        results = run_tests_from_class(self.TheTestsToTest)
        self.assertEqual(results.testsRun, 4)
        self.assertEqual(len(results.failures), 1)
        self.assertEqual(results.failures[0][0]._testMethodName, 'test_fail')
        self.assertEqual(len(results.errors), 1)
        self.assertEqual(results.errors[0][0]._testMethodName, 'test_error')
        self.assertEqual(len(results.skipped), 1)
        self.assertEqual(results.skipped[0][0]._testMethodName, 'test_skip')


class StdStreamCapturingMixinTest(unittest.TestCase):
    """Tests of StdStreamCapturingMixin."""

    class TheTestsToTest(StdStreamCapturingMixin, unittest.TestCase):
        def test_stdout(self):
            sys.stdout.write("Xyzzy")
            self.assertIn("Xyzzy", self.stdout())
            self.assertNotIn("Xyzzy", self.stderr())

        def test_stderr(self):
            sys.stderr.write("Plugh")
            self.assertIn("Plugh", self.stderr())
            self.assertNotIn("Plugh", self.stdout())

    def test_the_tests_to_test(self):
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        self.addCleanup(self._cleanup_streams, old_stdout, old_stderr)
        sys.stdout = my_stdout = six.StringIO()
        sys.stderr = my_stderr = six.StringIO()

        results = run_tests_from_class(self.TheTestsToTest)
        assert_all_passed(results, tests_run=2)

        self.assertIn(my_stdout.getvalue(), "Xyzzy")
        self.assertIn(my_stderr.getvalue(), "Plugh")

    def _cleanup_streams(self, stdout, stderr):
        sys.stdout = stdout
        sys.stderr = stderr
