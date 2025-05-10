# -*- coding: utf-8 -*-
"""
Python Comment Remover Script

This script processes Python (.py) files to remove hash (#) comments
using Python's `tokenize` module for robust parsing.
It can operate on a single file or recursively through a directory.
Removed comments and their locations are logged to a structured file (JSON by default).

Author: Yurika Corporation
Email: hello@yurikacorporation.com
Author URL: https://yurikacorporation.com
GitHub: https://github.com/yuricorp/python-comment-strip/
Architect: David Piner
License: LGPL-2.1 license
Version: 1.2.1
Date: 2024-07-31

Limitations:
  - The script assumes Python files are UTF-8 encoded or compatible.
    If `tokenize.detect_encoding` fails or the file is not valid Python,
    it may be skipped or cause an error.
  - While `tokenize.untokenize` does a good job of preserving formatting,
    minor whitespace differences might occur in rare edge cases compared to original.
"""

import os
import tokenize
import io
import re
import argparse
import json
from typing import List, Tuple, Iterator, Optional, Dict, Any
from dataclasses import dataclass


DEFAULT_REMOVED_COMMENTS_LOG = "removed_comments.json"

@dataclass
class CommentRemovalInfo:
    """Holds information about a single removed comment."""
    file_path: str
    line_number: int
    comment_text: str



def is_preserved_comment(comment: str) -> bool:
    """Checks if a comment should be preserved."""

    lower_comment = comment.lower()
    return (comment.startswith("#!") or
            "# -*- coding:" in comment or
            "# coding:" in comment or
            lower_comment.strip().startswith("# type:") or
            "# noqa" in lower_comment)


def remove_hash_comments(file_path: str) -> Optional[List[CommentRemovalInfo]]:
    """
    Removes hash comments from a single Python file and returns info about them.

    Special comments like shebangs (#!), encoding declarations (e.g., # -*- coding: utf-8 -*-),
    and type checking/linter control comments (e.g. # type: ignore, # noqa) are preserved.

    Args:
        file_path: The absolute path to the Python file to process.

    Returns:
        A list of CommentRemovalInfo objects for successfully removed comments,
        or None if an error occurred that prevented processing the file (read, tokenize, syntax, decode).
        Returns an empty list if no comments were found or all were preserved.
    """
    original_content: str = ""
    tokens: List[tokenize.TokenInfo] = []
    encoding: str = "utf-8"

    try:
        with open(file_path, "rb") as f_binary:

            try:
                encoding, _ = tokenize.detect_encoding(f_binary.readline)
            except SyntaxError as e:
                 print(f"Warning: Could not detect encoding for {file_path}, using utf-8. Error: {e}")
                 encoding = "utf-8"
            except Exception as e:
                 print(f"Warning: Unexpected error detecting encoding for {file_path}, using utf-8. Error: {e}")
                 encoding = "utf-8"

            f_binary.seek(0)


            original_content_bytes = f_binary.read()
            try:
                 original_content = original_content_bytes.decode(encoding)
            except UnicodeDecodeError:
                 print(f"Error: Could not decode file {file_path} with detected encoding {encoding}. Skipping.")
                 return None


            try:
                compile(original_content, file_path, 'exec')
            except SyntaxError as e:
                print(f"Error: Syntax error in file {file_path}: {e}. Skipping.")
                return None

            f_binary.seek(0)


        with io.TextIOWrapper(io.BytesIO(original_content_bytes), encoding=encoding, newline='') as f_text:
             tokens = list(tokenize.generate_tokens(f_text.readline))

    except (IOError, OSError) as e:
        print(f"Error: Could not open or read file {file_path}: {e}. Skipping.")
        return None
    except tokenize.TokenError as e:
        print(f"Error: Could not tokenize file {file_path} (is it valid Python?): {e}. Skipping.")
        return None
    except Exception as e:
        print(f"Error: An unexpected error occurred while reading/tokenizing {file_path}: {e}. Skipping.")
        return None

    kept_tokens: List[tokenize.TokenInfo] = []
    removed_comments_info: List[CommentRemovalInfo] = []

    for token in tokens:
        if token.type == tokenize.COMMENT:
            comment_text = token.string
            if is_preserved_comment(comment_text):
                kept_tokens.append(token)
            else:

                removed_comments_info.append(CommentRemovalInfo(
                    file_path=file_path,
                    line_number=token.start[0],
                    comment_text=comment_text.rstrip("\n")
                ))

        elif token.type != tokenize.ENCODING:
            kept_tokens.append(token)


    if not removed_comments_info:

        return []

    try:


        cleaned_code_lines = tokenize.untokenize(kept_tokens).splitlines()

        cleaned_code = '\n'.join(line.rstrip() for line in cleaned_code_lines) + '\n'


        original_code_lines = original_content.splitlines()
        original_code_normalized = '\n'.join(line.rstrip() for line in original_code_lines) + '\n'

        if cleaned_code == original_code_normalized:

             print(f"Warning: Comments found and logged for {file_path}, but cleaned code is identical to original (possible only whitespace comments?). File not modified.")
             return removed_comments_info

    except Exception as e:
        print(f"Error: Could not untokenize file {file_path}. Original file will be kept. Error: {e}")



        return removed_comments_info


    try:
        with open(file_path, "w", encoding=encoding, newline='') as file:
            file.write(cleaned_code)

        return removed_comments_info
    except (IOError, OSError) as e:
        print(f"Error: Could not write cleaned code to file {file_path}: {e}. Original file kept. Error: {e}")

        return removed_comments_info


def process_directory(directory: str) -> Tuple[List[CommentRemovalInfo], int]:
    """
    Recursively processes all .py files in the given directory.

    Args:
        directory: The absolute path to the directory to process.

    Returns:
        A tuple containing:
        - A list of all CommentRemovalInfo objects from all processed files that
          successfully had comments removed or preserved.
        - The count of files that failed processing entirely (read/tokenize/syntax errors).
    """
    all_removed_comments_info: List[CommentRemovalInfo] = []
    processed_files_count = 0
    failed_files_count = 0

    print(f"Scanning directory: {directory}")

    for root, _, files in os.walk(directory):
        for file_name in files:
            if file_name.lower().endswith(".py"):
                file_path = os.path.join(root, file_name)
                processed_files_count += 1
                print(f"Processing {file_path}...", end='', flush=True)

                removed_info = remove_hash_comments(file_path)

                if removed_info is None:
                    failed_files_count += 1
                    print(" Failed.")
                else:
                    all_removed_comments_info.extend(removed_info)
                    if removed_info:
                        print(f" Removed {len(removed_info)} comment(s).")
                    else:
                         print(" No comments removed.")


    print(f"\nDirectory processing complete.")
    print(f"Scanned {processed_files_count} Python files.")
    if failed_files_count > 0:
        print(f"Failed to process {failed_files_count} Python files (due to read, tokenize, or syntax errors). See messages above.")
    else:
        print("All scanned files were processable.")

    return all_removed_comments_info, failed_files_count


def output_removed_comments(removed_comments_data: List[CommentRemovalInfo], log_path: str) -> bool:
    """
    Writes the collected removed comment data to a log file in JSON format.

    Args:
        removed_comments_data: A list of CommentRemovalInfo objects.
        log_path: The path to the file where removed comments will be logged.

    Returns:
        True if logging was successful (including cleaning up an old log), False otherwise.
    """
    if not removed_comments_data:

        if os.path.exists(log_path):
             try:
                 os.remove(log_path)
                 print(f"Info: No comments were removed, removed empty or outdated log file: {log_path}")
             except (IOError, OSError) as e:
                 print(f"Warning: Could not remove potentially outdated log file {log_path}: {e}")
        else:

            pass

        return True



    log_data = [comment.__dict__ for comment in removed_comments_data]

    try:
        with open(log_path, "w", encoding="utf-8") as log_file:

            json.dump(log_data, log_file, indent=4, ensure_ascii=False)
        print(f"Removed comment details logged to {log_path}")
        return True
    except (IOError, OSError) as e:
        print(f"Error: Could not write to log file {log_path}: {e}")
        return False
    except Exception as e:
        print(f"Error: An unexpected error occurred while writing log file {log_path}: {e}")
        return False


def main():
    """
    Main function to handle command-line arguments and initiate processing.
    """
    parser = argparse.ArgumentParser(
        description="Removes hash comments from Python files using the tokenize module and logs them to a structured file (JSON).",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=f"""
Examples:
  Process a single Python file:
    python %(prog)s --file /path/to/your/script.py

  Process all .py files in a directory recursively:
    python %(prog)s --dir /path/to/your/project/

  Specify a custom log file for removed comments:
    python %(prog)s --dir /path/to/project --log custom_removed_comments.json

  Log file format: By default, removed comments are logged to {DEFAULT_REMOVED_COMMENTS_LOG}
  in JSON format, including file path, line number, and the comment text.
"""
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--file",
        metavar="FILE_PATH",
        type=str,
        help="Path to a single Python file to process."
    )
    group.add_argument(
        "--dir",
        metavar="DIRECTORY_PATH",
        type=str,
        help="Path to a directory to process recursively. All .py files will be processed."
    )
    parser.add_argument(
        "--log",
        metavar="LOG_FILE_PATH",
        type=str,
        default=DEFAULT_REMOVED_COMMENTS_LOG,
        help=f"Path to the file for logging removed comments (default: {DEFAULT_REMOVED_COMMENTS_LOG}). Log format is JSON."
    )

    args = parser.parse_args()


    target_path = os.path.abspath(args.file) if args.file else os.path.abspath(args.dir)
    removed_comments_path = os.path.abspath(args.log)


    log_dir = os.path.dirname(removed_comments_path)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
            print(f"Info: Created log directory: {log_dir}")
        except OSError as e:
            print(f"Error: Could not create log directory {log_dir}: {e}")
            return

    all_removed_data: List[CommentRemovalInfo] = []
    processing_failed = False

    if args.file:
        if not os.path.isfile(target_path):
            print(f"Error: Specified file path '{target_path}' is not a valid file.")
            processing_failed = True
        elif not target_path.lower().endswith(".py"):
            print(f"Error: Specified file '{target_path}' is not a Python (.py) file.")
            processing_failed = True
        else:
            print(f"Processing single file: {target_path}")
            removed_info = remove_hash_comments(target_path)
            if removed_info is None:
                 processing_failed = True
            else:
                 all_removed_data.extend(removed_info)

    elif args.dir:
        if not os.path.isdir(target_path):
            print(f"Error: Specified directory path '{target_path}' is not a valid directory.")
            processing_failed = True
        else:
            removed_data_from_dir, failed_count = process_directory(target_path)
            all_removed_data.extend(removed_data_from_dir)
            if failed_count > 0:
                processing_failed = True



    print("\nAttempting to write removed comments log...")
    output_successful = output_removed_comments(all_removed_data, removed_comments_path)
    if not output_successful:
         processing_failed = True


    if processing_failed:
        print("\nProcessing finished with errors.")
    else:


        print("\nProcessing finished successfully.")


if __name__ == "__main__":



    main()
