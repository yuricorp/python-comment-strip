import unittest
import os
import shutil
import tempfile
import json
from unittest import mock
import builtins
import argparse
import sys
from typing import List, Optional, Dict, Any




current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import rmcom
from rmcom import CommentRemovalInfo


def _read_json_log(file_path: str) -> Optional[List[Dict[str, Any]]]:
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:

            content = f.read()
            if not content:
                return []
            return json.loads(content)
    except json.JSONDecodeError:

        return None
    except (IOError, OSError):

         return None

class TestRmcom(unittest.TestCase):
    def setUp(self):

        self.test_dir = tempfile.mkdtemp()
        self.log_file_path = os.path.join(self.test_dir, "removed_comments.json")


        self.default_log_file_path_cwd = os.path.join(os.getcwd(), rmcom.DEFAULT_REMOVED_COMMENTS_LOG)
        if os.path.exists(self.default_log_file_path_cwd):
            os.remove(self.default_log_file_path_cwd)

        if os.path.exists(self.log_file_path):
            os.remove(self.log_file_path)


    def tearDown(self):

        shutil.rmtree(self.test_dir)


        if os.path.exists(self.default_log_file_path_cwd) and not self.default_log_file_path_cwd.startswith(os.path.abspath(self.test_dir)):
             try:
                 os.remove(self.default_log_file_path_cwd)
             except OSError:

                  pass


    def _create_temp_file(self, filename="test_script.py", content="", encoding="utf-8"):
        file_path = os.path.join(self.test_dir, filename)

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)
        return file_path

    def _read_file_content(self, file_path, encoding="utf-8"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except FileNotFoundError:
            return None


    def test_is_preserved_comment(self):
        self.assertTrue(rmcom.is_preserved_comment("#!/usr/bin/env python"))
        self.assertTrue(rmcom.is_preserved_comment("# -*- coding: utf-8 -*-"))
        self.assertTrue(rmcom.is_preserved_comment("# coding: utf-8"))
        self.assertTrue(rmcom.is_preserved_comment("# type: ignore"))
        self.assertTrue(rmcom.is_preserved_comment(" # type: list[int]"))
        self.assertTrue(rmcom.is_preserved_comment("# noqa"))
        self.assertTrue(rmcom.is_preserved_comment("# NOQA: E501"))
        self.assertTrue(rmcom.is_preserved_comment(" # noqa"))

        self.assertFalse(rmcom.is_preserved_comment("# This is a regular comment"))
        self.assertFalse(rmcom.is_preserved_comment("print(1) # Inline comment"))
        self.assertFalse(rmcom.is_preserved_comment("# Just a comment"))


    def test_remove_comments_simple_removal(self):
        content = """
print("Hello") # This is a comment
# Another comment
def func(): # Comment on function line
    pass
"""




        expected_content_after_processing = """
print("Hello")

def func():
    pass
"""
        file_path = self._create_temp_file(content=content)
        abs_file_path = os.path.abspath(file_path)

        removed_info = rmcom.remove_hash_comments(abs_file_path)

        self.assertIsNotNone(removed_info)
        self.assertEqual(len(removed_info), 3)



        expected_info = [
            CommentRemovalInfo(file_path=abs_file_path, line_number=2, comment_text="# This is a comment"),
            CommentRemovalInfo(file_path=abs_file_path, line_number=3, comment_text="# Another comment"),
            CommentRemovalInfo(file_path=abs_file_path, line_number=4, comment_text="# Comment on function line"),
        ]

        self.assertEqual(sorted(removed_info, key=lambda x: (x.line_number, x.comment_text)), sorted(expected_info, key=lambda x: (x.line_number, x.comment_text)))


        processed_content = self._read_file_content(file_path)
        processed_content_normalized = "\n".join(line.rstrip() for line in processed_content.strip().splitlines())
        expected_content_normalized = "\n".join(line.rstrip() for line in expected_content_after_processing.strip().splitlines())
        self.assertEqual(expected_content_normalized, processed_content_normalized)


    def test_remove_comments_preserves_shebang_and_encoding(self):
        content = """#!/usr/bin/env python
# -*- coding: utf-8 -*-
# coding: ascii
print("Hello") # A normal comment
# type: ignore
# noqa
# noqa: E501
# type: list[int]
"""



        expected_content = """#!/usr/bin/env python
# -*- coding: utf-8 -*-
# coding: ascii
print("Hello")
# type: ignore
# noqa
# noqa: E501
# type: list[int]
"""

        file_path = self._create_temp_file(content=content)
        abs_file_path = os.path.abspath(file_path)

        removed_info = rmcom.remove_hash_comments(abs_file_path)

        self.assertIsNotNone(removed_info)
        self.assertEqual(len(removed_info), 1)


        expected_info = [CommentRemovalInfo(file_path=abs_file_path, line_number=4, comment_text="# A normal comment")]
        self.assertEqual(removed_info, expected_info)


        processed_content = self._read_file_content(file_path)
        processed_content_normalized = "\n".join(line.rstrip() for line in processed_content.strip().splitlines())
        expected_content_normalized = "\n".join(line.rstrip() for line in expected_content.strip().splitlines())
        self.assertEqual(expected_content_normalized, processed_content_normalized)


    def test_remove_comments_no_comments_to_remove(self):
        content = 'print("Hello")\n'
        file_path = self._create_temp_file(content=content)
        abs_file_path = os.path.abspath(file_path)
        original_content = self._read_file_content(file_path)

        removed_info = rmcom.remove_hash_comments(abs_file_path)

        self.assertIsNotNone(removed_info)
        self.assertEqual(len(removed_info), 0)


        processed_content = self._read_file_content(file_path)
        self.assertEqual(original_content, processed_content)


    def test_remove_comments_only_preserved_comments(self):
        content = """#!/usr/bin/env python
# -*- coding: utf-8 -*-
# type: ignore
"""
        file_path = self._create_temp_file(content=content)
        abs_file_path = os.path.abspath(file_path)
        original_content = self._read_file_content(file_path)

        removed_info = rmcom.remove_hash_comments(abs_file_path)

        self.assertIsNotNone(removed_info)
        self.assertEqual(len(removed_info), 0)


        processed_content = self._read_file_content(file_path)
        self.assertEqual(original_content, processed_content)


    def test_remove_comments_file_not_found(self):

        non_existent_file_path = os.path.join(self.test_dir, "non_existent_file.py")
        abs_non_existent_file_path = os.path.abspath(non_existent_file_path)

        removed_info = rmcom.remove_hash_comments(abs_non_existent_file_path)

        self.assertIsNone(removed_info)


    def test_remove_comments_tokenization_error(self):

        file_path = self._create_temp_file(content="print('hello')\x00print('world')")
        abs_file_path = os.path.abspath(file_path)

        removed_info = rmcom.remove_hash_comments(abs_file_path)

        self.assertIsNone(removed_info)


    def test_remove_comments_syntax_error(self):

        file_path = self._create_temp_file(content="print 'hello' # Python 2 syntax")
        abs_file_path = os.path.abspath(file_path)

        removed_info = rmcom.remove_hash_comments(abs_file_path)

        self.assertIsNone(removed_info)


    def test_remove_comments_untokenize_error_returns_info_but_keeps_file(self):
        content = "print(1) # comment to remove"
        file_path = self._create_temp_file(content=content)
        abs_file_path = os.path.abspath(file_path)
        original_content = self._read_file_content(file_path)


        with mock.patch("tokenize.untokenize", side_effect=Exception("Simulated untokenize failure")):
            removed_info = rmcom.remove_hash_comments(abs_file_path)

        self.assertIsNotNone(removed_info)
        self.assertEqual(len(removed_info), 1)


        expected_info = [CommentRemovalInfo(file_path=abs_file_path, line_number=1, comment_text="# comment to remove")]
        self.assertEqual(removed_info, expected_info)


        processed_content = self._read_file_content(file_path)
        self.assertEqual(original_content, processed_content)


    def test_remove_comments_write_error_returns_info_but_keeps_file(self):
        content = "print(0) # to be removed"
        file_path = self._create_temp_file(content=content)
        abs_file_path = os.path.abspath(file_path)
        original_content = self._read_file_content(file_path)


        original_open = builtins.open
        def faulty_open(name, mode='r', *args, **kwargs):

            if os.path.abspath(name) == abs_file_path and 'w' in mode:
                raise IOError("Simulated write error")

            return original_open(name, mode, *args, **kwargs)


        with mock.patch("builtins.open", side_effect=faulty_open):
            removed_info = rmcom.remove_hash_comments(abs_file_path)

        self.assertIsNotNone(removed_info)
        self.assertEqual(len(removed_info), 1)


        expected_info = [CommentRemovalInfo(file_path=abs_file_path, line_number=1, comment_text="# to be removed")]
        self.assertEqual(removed_info, expected_info)


        processed_content = self._read_file_content(file_path)
        self.assertEqual(original_content, processed_content)


    def test_remove_comments_different_encodings_cp1252(self):


        content_cp1252 = """# -*- coding: cp1252 -*-
# Comentário com acentuação: áéíóú
print("Olá Mundo") # Olá
"""


        expected_content_cp1252 = """# -*- coding: cp1252 -*-

print("Olá Mundo")
"""
        file_path = self._create_temp_file(filename="test_cp1252.py", content=content_cp1252, encoding="cp1252")
        abs_file_path = os.path.abspath(file_path)

        removed_info = rmcom.remove_hash_comments(abs_file_path)

        self.assertIsNotNone(removed_info)
        self.assertEqual(len(removed_info), 2)


        expected_info = [
             CommentRemovalInfo(file_path=abs_file_path, line_number=2, comment_text="# Comentário com acentuação: áéíóú"),
             CommentRemovalInfo(file_path=abs_file_path, line_number=3, comment_text="# Olá"),
        ]
        self.assertEqual(sorted(removed_info, key=lambda x: x.line_number), sorted(expected_info, key=lambda x: x.line_number))


        processed_content = self._read_file_content(file_path, encoding="cp1252")
        processed_content_normalized = "\n".join(line.rstrip() for line in processed_content.strip().splitlines())
        expected_content_normalized = "\n".join(line.rstrip() for line in expected_content_cp1252.strip().splitlines())
        self.assertEqual(processed_content_normalized, expected_content_normalized)


    def test_remove_comments_idempotency(self):
        content = """print('hello') # comment one
# comment two"""

        expected_after_first_pass = """print('hello')
"""
        file_path = self._create_temp_file(content=content)
        abs_file_path = os.path.abspath(file_path)


        removed_info_1 = rmcom.remove_hash_comments(abs_file_path)
        self.assertIsNotNone(removed_info_1)
        self.assertEqual(len(removed_info_1), 2)
        content_after_first_pass = self._read_file_content(file_path)
        content_after_first_pass_normalized = "\n".join(line.rstrip() for line in content_after_first_pass.strip().splitlines())
        expected_after_first_pass_normalized = "\n".join(line.rstrip() for line in expected_after_first_pass.strip().splitlines())
        self.assertEqual(content_after_first_pass_normalized, expected_after_first_pass_normalized)


        removed_info_2 = rmcom.remove_hash_comments(abs_file_path)
        self.assertIsNotNone(removed_info_2)
        self.assertEqual(len(removed_info_2), 0)


        content_after_second_pass = self._read_file_content(file_path)
        self.assertEqual(content_after_first_pass, content_after_second_pass)

    def test_empty_file_processing(self):
        file_path = self._create_temp_file(content="")
        abs_file_path = os.path.abspath(file_path)

        removed_info = rmcom.remove_hash_comments(abs_file_path)

        self.assertIsNotNone(removed_info)
        self.assertEqual(len(removed_info), 0)
        self.assertEqual(self._read_file_content(file_path), "")

    def test_file_with_only_whitespace_and_comments(self):
        content = """    # comment line 1

# comment line 2
   """

        expected_content = """


"""
        file_path = self._create_temp_file(content=content)
        abs_file_path = os.path.abspath(file_path)

        removed_info = rmcom.remove_hash_comments(abs_file_path)

        self.assertIsNotNone(removed_info)
        self.assertEqual(len(removed_info), 2)


        expected_info = [
            CommentRemovalInfo(file_path=abs_file_path, line_number=1, comment_text="# comment line 1"),
            CommentRemovalInfo(file_path=abs_file_path, line_number=3, comment_text="# comment line 2"),
        ]
        self.assertEqual(sorted(removed_info, key=lambda x: x.line_number), sorted(expected_info, key=lambda x: x.line_number))


        processed_content = self._read_file_content(file_path)
        processed_content_normalized = "\n".join(line.rstrip() for line in processed_content.strip().splitlines())
        expected_content_normalized = "\n".join(line.rstrip() for line in expected_content.strip().splitlines())
        self.assertEqual(processed_content_normalized, expected_content_normalized)



class TestOutputRemovedComments(unittest.TestCase):
     def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.log_file_path = os.path.join(self.test_dir, "removed_comments.json")

        if os.path.exists(self.log_file_path):
            os.remove(self.log_file_path)


     def tearDown(self):
        shutil.rmtree(self.test_dir)


     def test_output_removed_comments_creates_json_log(self):
         comments_info = [
             CommentRemovalInfo(file_path="/fake/path/file1.py", line_number=5, comment_text="# comment 1"),
             CommentRemovalInfo(file_path="/fake/path/file2.py", line_number=10, comment_text="# comment 2"),
         ]

         result = rmcom.output_removed_comments(comments_info, self.log_file_path)
         self.assertTrue(result)
         self.assertTrue(os.path.exists(self.log_file_path))

         log_data = _read_json_log(self.log_file_path)
         self.assertIsNotNone(log_data)
         self.assertEqual(len(log_data), 2)


         expected_data = [
            {"file_path": "/fake/path/file1.py", "line_number": 5, "comment_text": "# comment 1"},
            {"file_path": "/fake/path/file2.py", "line_number": 10, "comment_text": "# comment 2"},
         ]
         self.assertEqual(log_data, expected_data)


     def test_output_removed_comments_empty_list_no_log_created(self):

         self.assertFalse(os.path.exists(self.log_file_path))
         result = rmcom.output_removed_comments([], self.log_file_path)
         self.assertTrue(result)
         self.assertFalse(os.path.exists(self.log_file_path))


     def test_output_removed_comments_empty_list_cleans_existing_log(self):

         with open(self.log_file_path, "w") as f:
             f.write("Some old log content")
         self.assertTrue(os.path.exists(self.log_file_path))

         result = rmcom.output_removed_comments([], self.log_file_path)
         self.assertTrue(result)
         self.assertFalse(os.path.exists(self.log_file_path))

     def test_output_removed_comments_write_error(self):
         comments_info = [CommentRemovalInfo(file_path="dummy.py", line_number=1, comment_text="# c")]


         original_open = builtins.open
         def faulty_open(name, mode='r', *args, **kwargs):
            if os.path.abspath(name) == os.path.abspath(self.log_file_path) and 'w' in mode:
                 raise IOError("Simulated log write error")
            return original_open(name, mode, *args, **kwargs)

         with mock.patch("builtins.open", side_effect=faulty_open):
             result = rmcom.output_removed_comments(comments_info, self.log_file_path)

         self.assertFalse(result)



         self.assertIsNone(_read_json_log(self.log_file_path))



class TestProcessDirectory(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _create_temp_py_file(self, dir_path, filename, content):

        file_path = os.path.join(dir_path, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    @mock.patch("rmcom.remove_hash_comments")
    def test_process_directory_calls_remove_hash_comments_for_py_files(self, mock_remove_comments):

        mock_remove_comments.return_value = []

        py_file1_content = "print(1) # comment1"
        py_file2_content = """# comment2
print(2)"""
        non_py_file_content = "This is not a python file"

        file1_path = self._create_temp_py_file(self.test_dir, "script1.py", py_file1_content)
        file2_path = self._create_temp_py_file(self.test_dir, "script2.py", py_file2_content)
        txt_file_path = self._create_temp_py_file(self.test_dir, "script.txt", non_py_file_content)

        subdir = os.path.join(self.test_dir, "subdir")
        file3_path = self._create_temp_py_file(subdir, "script3.py", py_file1_content)

        abs_file1_path = os.path.abspath(file1_path)
        abs_file2_path = os.path.abspath(file2_path)
        abs_file3_path = os.path.abspath(file3_path)
        abs_test_dir = os.path.abspath(self.test_dir)


        with mock.patch("builtins.print"):
             removed_data, failed_count = rmcom.process_directory(abs_test_dir)



        expected_calls = [
            mock.call(abs_file1_path),
            mock.call(abs_file2_path),
            mock.call(abs_file3_path),
        ]
        self.assertEqual(mock_remove_comments.call_count, 3)
        mock_remove_comments.assert_has_calls(expected_calls, any_order=True)


        non_py_abs_path = os.path.abspath(txt_file_path)
        for call in mock_remove_comments.call_args_list:
            self.assertNotEqual(call.args[0], non_py_abs_path)


        self.assertEqual(len(removed_data), 0)
        self.assertEqual(failed_count, 0)


    @mock.patch("rmcom.remove_hash_comments")
    def test_process_directory_collects_removed_info(self, mock_remove_comments):
        file1_path = self._create_temp_py_file(self.test_dir, "file1.py", "print(1) # c1")
        file2_path = self._create_temp_py_file(self.test_dir, "file2.py", "# c2\npass")
        file3_path = self._create_temp_py_file(self.test_dir, "file3_no_comments.py", "print('no comments')")

        abs_file1_path = os.path.abspath(file1_path)
        abs_file2_path = os.path.abspath(file2_path)
        abs_file3_path = os.path.abspath(file3_path)
        abs_test_dir = os.path.abspath(self.test_dir)




        info1 = [CommentRemovalInfo(file_path=abs_file1_path, line_number=1, comment_text=" # c1")]
        info2 = [CommentRemovalInfo(file_path=abs_file2_path, line_number=1, comment_text="# c2")]
        info_empty = []


        def side_effect_func(file_path):
            if file_path == abs_file1_path:
                return info1
            elif file_path == abs_file2_path:
                 return info2
            elif file_path == abs_file3_path:
                 return info_empty
            else:
                 return []

        mock_remove_comments.side_effect = side_effect_func

        with mock.patch("builtins.print"):
            removed_data, failed_count = rmcom.process_directory(abs_test_dir)


        self.assertEqual(mock_remove_comments.call_count, 3)
        self.assertEqual(len(removed_data), 2)
        self.assertEqual(failed_count, 0)


        expected_collected_data = sorted(info1 + info2, key=lambda x: (x.file_path, x.line_number))
        actual_collected_data = sorted(removed_data, key=lambda x: (x.file_path, x.line_number))
        self.assertEqual(actual_collected_data, expected_collected_data)


    @mock.patch("rmcom.remove_hash_comments")
    def test_process_directory_handles_remove_hash_comments_failure(self, mock_remove_comments):
        file1_path = self._create_temp_py_file(self.test_dir, "bad_script.py", "invalid content")
        file2_path = self._create_temp_py_file(self.test_dir, "good_script.py", "print(2) # comment")
        abs_file1_path = os.path.abspath(file1_path)
        abs_file2_path = os.path.abspath(file2_path)
        abs_test_dir = os.path.abspath(self.test_dir)



        info2 = [CommentRemovalInfo(file_path=abs_file2_path, line_number=1, comment_text=" # comment")]

        def side_effect_func(file_path):
            if file_path == abs_file1_path:
                return None
            elif file_path == abs_file2_path:
                return info2
            return []

        mock_remove_comments.side_effect = side_effect_func

        with mock.patch("builtins.print") as mock_print:
            removed_data, failed_count = rmcom.process_directory(abs_test_dir)


        self.assertEqual(mock_remove_comments.call_count, 2)
        self.assertEqual(failed_count, 1)
        self.assertEqual(len(removed_data), 1)


        self.assertEqual(removed_data, info2)


        printed_failure_message = False
        for call_args in mock_print.call_args_list:
            if isinstance(call_args[0][0], str) and "Failed to process 1 Python files" in call_args[0][0]:
                printed_failure_message = True
                break
        self.assertTrue(printed_failure_message, "Failure count message not found in print output")


    @mock.patch("rmcom.remove_hash_comments")
    def test_process_directory_empty_dir(self, mock_remove_comments):

        empty_subdir = os.path.join(self.test_dir, "empty_subdir")
        os.makedirs(empty_subdir)
        abs_test_dir = os.path.abspath(self.test_dir)

        with mock.patch("builtins.print"):
             removed_data, failed_count = rmcom.process_directory(abs_test_dir)


        mock_remove_comments.assert_not_called()
        self.assertEqual(len(removed_data), 0)
        self.assertEqual(failed_count, 0)


class TestMainFunction(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()


        self.log_file_path = os.path.join(self.test_dir, rmcom.DEFAULT_REMOVED_COMMENTS_LOG)
        self.custom_log_path = os.path.join(self.test_dir, "custom.log")


        default_log_cwd = os.path.join(os.getcwd(), rmcom.DEFAULT_REMOVED_COMMENTS_LOG)
        if os.path.exists(default_log_cwd):
            os.remove(default_log_cwd)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

        default_log_cwd = os.path.join(os.getcwd(), rmcom.DEFAULT_REMOVED_COMMENTS_LOG)
        if os.path.exists(default_log_cwd) and not default_log_cwd.startswith(os.path.abspath(self.test_dir)):
             try:
                 os.remove(default_log_cwd)
             except OSError:
                 pass

        if os.path.exists(self.custom_log_path) and not self.custom_log_path.startswith(os.path.abspath(self.test_dir)):
             try:
                 os.remove(self.custom_log_path)
             except OSError:
                 pass


    def _create_temp_py_file(self, filename, content):

        file_path = os.path.join(self.test_dir, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path


    def _mock_args(self, file=None, dir=None, log=None):

        abs_file = os.path.abspath(file) if file else None
        abs_dir = os.path.abspath(dir) if dir else None


        abs_log = os.path.abspath(log) if log else os.path.abspath(rmcom.DEFAULT_REMOVED_COMMENTS_LOG)

        return argparse.Namespace(file=abs_file, dir=abs_dir, log=abs_log)

    @mock.patch("rmcom.output_removed_comments")
    @mock.patch("rmcom.remove_hash_comments")
    @mock.patch("argparse.ArgumentParser.parse_args")
    @mock.patch("builtins.print")
    def test_main_with_file_arg(self, mock_print, mock_parse_args, mock_remove_comments, mock_output_comments):
        temp_py_file = self._create_temp_py_file("single.py", "print(1) # comment")
        abs_temp_py_file = os.path.abspath(temp_py_file)
        abs_log_path = os.path.abspath(self.log_file_path)


        mock_parse_args.return_value = self._mock_args(file=temp_py_file, log=self.log_file_path)

        removed_info = [CommentRemovalInfo(file_path=abs_temp_py_file, line_number=1, comment_text=" # comment")]
        mock_remove_comments.return_value = removed_info
        mock_output_comments.return_value = True

        rmcom.main()


        mock_remove_comments.assert_called_once_with(abs_temp_py_file)
        mock_output_comments.assert_called_once_with(removed_info, abs_log_path)


    @mock.patch("rmcom.output_removed_comments")
    @mock.patch("rmcom.process_directory")
    @mock.patch("argparse.ArgumentParser.parse_args")
    @mock.patch("builtins.print")
    def test_main_with_dir_arg(self, mock_print, mock_parse_args, mock_process_directory, mock_output_comments):
        abs_test_dir = os.path.abspath(self.test_dir)
        abs_log_path = os.path.abspath(self.log_file_path)


        mock_parse_args.return_value = self._mock_args(dir=self.test_dir, log=self.log_file_path)

        removed_info_list = [CommentRemovalInfo(file_path=os.path.join(abs_test_dir, "dummy.py"), line_number=1, comment_text="# c")]
        mock_process_directory.return_value = (removed_info_list, 0)
        mock_output_comments.return_value = True

        rmcom.main()


        mock_process_directory.assert_called_once_with(abs_test_dir)
        mock_output_comments.assert_called_once_with(removed_info_list, abs_log_path)

    @mock.patch("rmcom.output_removed_comments")
    @mock.patch("rmcom.remove_hash_comments")
    @mock.patch("argparse.ArgumentParser.parse_args")
    @mock.patch("builtins.print")
    def test_main_with_custom_log_arg(self, mock_print, mock_parse_args, mock_remove_comments, mock_output_comments):
        temp_py_file = self._create_temp_py_file("another.py", "print(1) # comment")
        abs_temp_py_file = os.path.abspath(temp_py_file)
        abs_custom_log_path = os.path.abspath(self.custom_log_path)


        mock_parse_args.return_value = self._mock_args(file=temp_py_file, log=self.custom_log_path)

        removed_info = [CommentRemovalInfo(file_path=abs_temp_py_file, line_number=1, comment_text=" # comment")]
        mock_remove_comments.return_value = removed_info
        mock_output_comments.return_value = True

        rmcom.main()


        mock_remove_comments.assert_called_once_with(abs_temp_py_file)
        mock_output_comments.assert_called_once_with(removed_info, abs_custom_log_path)


    @mock.patch("argparse.ArgumentParser.parse_args")
    @mock.patch("builtins.print")
    @mock.patch("rmcom.remove_hash_comments")
    @mock.patch("rmcom.output_removed_comments")
    def test_main_invalid_file_path(self, mock_output_comments, mock_remove_comments, mock_print, mock_parse_args):
        invalid_path = os.path.join(self.test_dir, "nonexistent.py")
        mock_parse_args.return_value = self._mock_args(file=invalid_path, log=self.log_file_path)

        rmcom.main()

        mock_remove_comments.assert_not_called()

        abs_log_path = os.path.abspath(self.log_file_path)
        mock_output_comments.assert_called_once_with([], abs_log_path)



        printed_error = any(
            isinstance(call_args[0][0], str) and
            os.path.abspath(invalid_path) in call_args[0][0] and "not a valid file" in call_args[0][0]
            for call_args in mock_print.call_args_list
        )
        self.assertTrue(printed_error)


    @mock.patch("argparse.ArgumentParser.parse_args")
    @mock.patch("builtins.print")
    @mock.patch("rmcom.remove_hash_comments")
    @mock.patch("rmcom.output_removed_comments")
    def test_main_not_a_py_file(self, mock_output_comments, mock_remove_comments, mock_print, mock_parse_args):
        temp_txt_file = self._create_temp_py_file("test.txt", "content")
        abs_temp_txt_file = os.path.abspath(temp_txt_file)
        mock_parse_args.return_value = self._mock_args(file=temp_txt_file, log=self.log_file_path)

        rmcom.main()

        mock_remove_comments.assert_not_called()

        abs_log_path = os.path.abspath(self.log_file_path)
        mock_output_comments.assert_called_once_with([], abs_log_path)

        printed_error = any(
             isinstance(call_args[0][0], str) and
             abs_temp_txt_file in call_args[0][0] and "not a Python (.py) file" in call_args[0][0]
             for call_args in mock_print.call_args_list
        )
        self.assertTrue(printed_error)



    @mock.patch("argparse.ArgumentParser.parse_args")
    @mock.patch("builtins.print")
    @mock.patch("rmcom.process_directory")
    @mock.patch("rmcom.output_removed_comments")
    def test_main_invalid_dir_path(self, mock_output_comments, mock_process_directory, mock_print, mock_parse_args):
        invalid_path = os.path.join(self.test_dir, "nonexistent_dir")
        mock_parse_args.return_value = self._mock_args(dir=invalid_path, log=self.log_file_path)

        rmcom.main()

        mock_process_directory.assert_not_called()

        abs_log_path = os.path.abspath(self.log_file_path)
        mock_output_comments.assert_called_once_with([], abs_log_path)


        printed_error = any(
             isinstance(call_args[0][0], str) and
             os.path.abspath(invalid_path) in call_args[0][0] and "not a valid directory" in call_args[0][0]
             for call_args in mock_print.call_args_list
        )
        self.assertTrue(printed_error)



    @mock.patch("rmcom.remove_hash_comments")
    @mock.patch("rmcom.output_removed_comments")
    @mock.patch("argparse.ArgumentParser.parse_args")
    @mock.patch("builtins.print")
    def test_main_creates_log_directory(self, mock_print, mock_parse_args, mock_output_comments, mock_remove_hash):
        log_dir = os.path.join(self.test_dir, "logs")
        custom_log_in_subdir = os.path.join(log_dir, "output.json")
        abs_custom_log_in_subdir = os.path.abspath(custom_log_in_subdir)




        original_makedirs = os.makedirs
        mock_makedirs = mock.Mock(side_effect=original_makedirs)



        original_exists = os.path.exists
        def mock_exists(path):
             if os.path.abspath(path) == os.path.abspath(log_dir):
                  return False
             return original_exists(path)


        with mock.patch("os.path.exists", side_effect=mock_exists),\
             mock.patch("os.makedirs", side_effect=mock_makedirs) as patched_makedirs:

            temp_py_file = self._create_temp_py_file("file_for_log_dir_test.py", "print(0) # c")
            abs_temp_py_file = os.path.abspath(temp_py_file)

            mock_parse_args.return_value = self._mock_args(file=temp_py_file, log=abs_custom_log_in_subdir)


            removed_info = [CommentRemovalInfo(file_path=abs_temp_py_file, line_number=1, comment_text=" # c")]
            mock_remove_hash.return_value = removed_info
            mock_output_comments.return_value = True

            rmcom.main()


        patched_makedirs.assert_any_call(os.path.abspath(log_dir), exist_ok=True)


        mock_remove_hash.assert_called_once_with(abs_temp_py_file)

        mock_output_comments.assert_called_once_with(removed_info, abs_custom_log_in_subdir)




    @mock.patch("argparse.ArgumentParser.parse_args")
    @mock.patch("builtins.print")
    @mock.patch("rmcom.remove_hash_comments")
    @mock.patch("rmcom.output_removed_comments")
    def test_main_log_directory_creation_fails(self, mock_output_comments, mock_remove_comments, mock_print, mock_parse_args):
        log_dir = os.path.join(self.test_dir, "uncreatable_logs", "subdir_that_wont_exist")
        custom_log_in_subdir = os.path.join(log_dir, "output.json")
        abs_custom_log_in_subdir = os.path.abspath(custom_log_in_subdir)


        original_makedirs = os.makedirs
        def conditional_makedirs(path, exist_ok=False):

             if os.path.abspath(path) == os.path.abspath(log_dir):
                  raise OSError("Simulated Cannot create dir error")

             return original_makedirs(path, exist_ok=exist_ok)

        original_exists = os.path.exists
        def mock_exists(path):

             if os.path.abspath(path) == os.path.abspath(log_dir):
                  return False
             return original_exists(path)


        with mock.patch("os.path.exists", side_effect=mock_exists),\
             mock.patch("os.makedirs", side_effect=conditional_makedirs) as patched_makedirs:
             temp_py_file = self._create_temp_py_file("file_for_log_dir_fail.py", "print(0)")


             mock_parse_args.return_value = self._mock_args(file=temp_py_file, log=abs_custom_log_in_subdir)

             rmcom.main()


        patched_makedirs.assert_any_call(os.path.abspath(log_dir), exist_ok=True)


        mock_remove_comments.assert_not_called()
        mock_output_comments.assert_not_called()

        printed_error = any(
             isinstance(call_args[0][0], str) and
             "Could not create log directory" in call_args[0][0] and os.path.abspath(log_dir) in call_args[0][0]
             for call_args in mock_print.call_args_list
        )
        self.assertTrue(printed_error)



    @mock.patch("rmcom.remove_hash_comments", return_value=None)
    @mock.patch("argparse.ArgumentParser.parse_args")
    @mock.patch("builtins.print")
    @mock.patch("rmcom.output_removed_comments")
    def test_main_file_processing_fails(self, mock_output_comments, mock_print, mock_parse_args, mock_remove_comments_fail):
        temp_py_file = self._create_temp_py_file("bad_file.py", "invalid content")
        abs_temp_py_file = os.path.abspath(temp_py_file)
        abs_log_path = os.path.abspath(self.log_file_path)
        mock_parse_args.return_value = self._mock_args(file=temp_py_file, log=self.log_file_path)

        rmcom.main()

        mock_remove_comments_fail.assert_called_once_with(abs_temp_py_file)

        mock_output_comments.assert_called_once_with([], abs_log_path)


        printed_error = any(isinstance(call_args[0][0], str) and "Processing finished with errors." in call_args[0][0] for call_args in mock_print.call_args_list)
        self.assertTrue(printed_error)



    @mock.patch("rmcom.process_directory", return_value=([], 1))
    @mock.patch("argparse.ArgumentParser.parse_args")
    @mock.patch("builtins.print")
    @mock.patch("rmcom.output_removed_comments")
    def test_main_dir_processing_has_failures_but_no_comments_removed(self, mock_output_comments, mock_print, mock_parse_args, mock_process_directory):
        abs_test_dir = os.path.abspath(self.test_dir)
        abs_log_path = os.path.abspath(self.log_file_path)
        mock_parse_args.return_value = self._mock_args(dir=self.test_dir, log=self.log_file_path)

        rmcom.main()

        mock_process_directory.assert_called_once_with(abs_test_dir)

        mock_output_comments.assert_called_once_with([], abs_log_path)


        printed_error = any(isinstance(call_args[0][0], str) and "Processing finished with errors." in call_args[0][0] for call_args in mock_print.call_args_list)
        self.assertTrue(printed_error)



    @mock.patch("rmcom.remove_hash_comments", return_value=[CommentRemovalInfo("f",1,"#c")])
    @mock.patch("argparse.ArgumentParser.parse_args")
    @mock.patch("builtins.print")
    @mock.patch("rmcom.output_removed_comments", return_value=False)
    def test_main_log_writing_fails(self, mock_output_comments_fail, mock_print, mock_parse_args, mock_remove_comments_success):
        temp_py_file = self._create_temp_py_file("ok_file.py", "print(0) # c")
        abs_temp_py_file = os.path.abspath(temp_py_file)
        abs_log_path = os.path.abspath(self.log_file_path)
        mock_parse_args.return_value = self._mock_args(file=temp_py_file, log=self.log_file_path)



        removed_info = [CommentRemovalInfo(file_path=abs_temp_py_file, line_number=1, comment_text=" # c")]
        mock_remove_comments_success.return_value = removed_info

        rmcom.main()

        mock_remove_comments_success.assert_called_once_with(abs_temp_py_file)
        mock_output_comments_fail.assert_called_once_with(removed_info, abs_log_path)


        printed_error = any(isinstance(call_args[0][0], str) and "Processing finished with errors." in call_args[0][0] for call_args in mock_print.call_args_list)
        self.assertTrue(printed_error)


if __name__ == "__main__":


    unittest.main(argv=['first-arg-is-ignored'], exit=False)
