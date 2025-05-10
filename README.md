# Python Comment Strip

One of the problems with LLMs is that they like to use comments
to explain their code. This can be useful, to learn and understand
some of the decisions that they made, but it's not
a production best practice. You want to remove those comments and
then purposefully go through and comment anything yourself.

This script will remove all in-line comments from Python code.

It will not remove docstrings, only in-line # comments.

## Features

- Removes inline `#` comments from Python files.
- Preserves docstrings.
- Can process a single file or an entire directory recursively.
- Creates a JSON log file detailing removed comments (file path, line number, comment text).
- Configurable log file path.

## Installation

To install the `python-comment-strip` package, you can use pip:

```bash
pip install .
```

(Or, once published to PyPI: `pip install python-comment-strip`)

This will also install the `rmcom` command-line tool.

## Usage

To use the script, you can run it from the command line with various options.

### Process a Single File

To remove comments from a single Python file:

```bash
python rmcom.py --file /path/to/your/script.py
```

### Process a Directory

To remove comments from all `.py` files within a specific directory and its subdirectories:

```bash
python rmcom.py --dir /path/to/your/project/
```

### Specify a Custom Log File

You can specify a custom path for the JSON log file where details of removed comments will be stored:

```bash
python rmcom.py --file /path/to/your/script.py --log custom_removed_comments.log
```

or for a directory:

```bash
python rmcom.py --dir /path/to/your/project/ --log custom_removed_comments.json
```

By default, the log file is named `removed_comments.json` and is created in the current working directory from which the script is run.

### Help

To see all available options and their descriptions:

```bash
python rmcom.py --help
```

## Log File

The script generates a JSON log file (default: `removed_comments.json`) that records information about each removed comment, including:

- `file_path`: The path to the file from which the comment was removed.
- `line_number`: The line number where the comment was located.
- `comment_text`: The actual text of the removed comment.

This log file is useful for reviewing the comments that were stripped from the codebase. If no comments are removed (or if all comments were of a type to be preserved), the log file will not be created, or an existing one might be removed if it was from a previous run.

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines.

## Code of Conduct

Please note that this project is released with a Contributor [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

## License

This project is licensed under the GNU Lesser General Public License v2.1 or later - see the [LICENSE](LICENSE) file for details.
