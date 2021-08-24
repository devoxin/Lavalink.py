import guzzle_sphinx_theme

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys
sys.path.insert(0, os.path.abspath('..'))

# -- Project information -----------------------------------------------------

project = 'Lavalink.py'
copyright = '2020, Devoxin'
author = 'Devoxin'
master_doc = 'index'

projectlink = 'https://github.com/Devoxin/Lavalink.py'

# If true, TOC entries that are not ancestors of the current page are collapsed
globaltoc_collapse = False

# If true, the global TOC tree will also contain hidden entries
globaltoc_includehidden = False

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'guzzle_sphinx_theme',
]

rst_prolog = """
.. |coro| replace:: This function is a |coroutine_link|_.
.. |maybecoro| replace:: This function *could be a* |coroutine_link|_.
.. |coroutine_link| replace:: *coroutine*
.. _coroutine_link: https://docs.python.org/3/library/asyncio-task.html#coroutine
"""

autodoc_member_order = 'bysource'
html_favicon = 'lavalinkpy.ico'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

html_theme = 'guzzle_sphinx_theme'
html_theme_path = guzzle_sphinx_theme.html_theme_path()

# Guzzle theme options (see theme.conf for more information)
html_theme_options = {
    # Set the name of the project to appear in the sidebar
    "project_nav_name": "Lavalink.py",
}

html_sidebars = {
    '**': ['searchbox.html',
           'logo-text.html',
           'globaltoc.html',
           'localtoc.html']
}

html_show_sourcelink = False

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_context = {
    'css_files': ['_static/style.css']
}
