# pylint: disable=redefined-builtin
"""
Configuration file for the Sphinx documentation builder.
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""
from typing import Final, Sequence
import os
import sys

# region Path setup
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))
# endregion

author: Final[str] = ''
copyright: Final[str] = '2020'
project: Final[str] = 'Xirvik Tools'
"""The short X.Y version."""
version: Final[str] = '1.2.7'
"""The full version, including alpha/beta/rc tags."""
release: Final[str] = f'v{version}'
"""
Add any Sphinx extension module names here, as strings. They can be extensions
coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
"""
extensions: Final[Sequence[str]] = [
    'sphinx.ext.autodoc', 'sphinx.ext.napoleon'
]
"""Add any paths that contain templates here, relative to this directory."""
templates_path: Final[Sequence[str]] = ['_templates']
"""
List of patterns, relative to source directory, that match files and
directories to ignore when looking for source files. This pattern also affects
html_static_path and html_extra_path.
"""
exclude_patterns: Final[Sequence[str]] = []
master_doc: Final[str] = 'index'
"""
Add any paths that contain custom static files (such as style sheets) here,
relative to this directory. They are copied after the builtin static files, so
a file named "default.css" will overwrite the builtin "default.css".
"""
html_static_path: Final[Sequence[str]] = ['_static']
"""
The theme to use for HTML and HTML Help pages.  See the documentation for a
list of builtin themes.
"""
html_theme: Final[str] = 'alabaster'
