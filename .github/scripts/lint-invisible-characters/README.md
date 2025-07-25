# Invisible Character Linter

The `lint-invisible.py` script detects invisible Unicode characters in text files that might cause issues or be used maliciously. It ignores common legitimate whitespace characters (space, tab, CR, LF).

### Usage

```bash
python3 lint-invisible.py <file1> <file2> ... [--ignore <pattern1>,<pattern2>,...]
```

#### Arguments
- `<file1> <file2> ...`: One or more files to scan
- `--ignore`: Optional comma-separated list of patterns to ignore

### Testing

To test the linter with the provided test file:

```bash
# Basic test
python3 lint-invisible.py lint-invisible-test-file.md
```

Expected output will show detected invisible characters with their Unicode code points and descriptions. The script will exit with status code 1 if any invisible characters are found.
