"""
Filters downloaded file by
* file type
* language

"""
import os
from typing import Generator

HTML_EXTENSIONS = {".html", ".htm", ".php"}


def detect_language(filepath: str) -> str:
    """Decide the language of an HTML-like file.

    @param filepath: path to the file.
    @return: detected language code (e.g. 'en', 'ja').
    """
    raise NotImplementedError


def walk_tree(root: str) -> Generator[str, None, None]:
    """Recursively yield all files under root.

    @param root: root directory to walk.
    @return: generator yielding file paths as strings.
    """
    for dirpath, _, fnames in os.walk(root):
        for fname in fnames:
            filepath = os.path.join(dirpath, fname)
            _, ext = os.path.splitext(fname)
            ext = ext.lower()

            if ext in HTML_EXTENSIONS:
                detect_language(filepath)

            yield filepath
