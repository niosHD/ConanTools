#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# Add root directory to the python path to enable import of the package
# via autodoc.
sys.path.insert(0, os.path.abspath('../..'))


# Fully automatically generating the API documentation for a package including all submodules and
# subpackages is apparently not really simple with sphinx. Two approaches exist in the stock sphinx
# package to address this need, i.e., `autosummary` with the `sphinx-autogen` tool and
# `sphinx-apidoc`. However, both fail to some extend. The `autosummary` extension has nice template
# support but requires to manually manage a list of all modules [1]. The `sphinx-apidoc` tool, on
# the other hand, generates stubs for the full documentation but is designed to be executed only
# once. Afterwards, manual modifications of the generated files is intended. Furthermore, executing
# `sphinx-apidoc` as part of the build is not really supported and a workaround [2] is needed.
# Still, the apidoc solution seems to be currently the most promissing approach and is therefore
# used for now. Note that, as an alternative, there is also `better-apidoc` [3] which is a fork of
# `sphinx-apidoc` that adds template support. Unfortunately, at least for the current code base
# which uses implicit namespace packages, using it does not yield the desired results [4].
#
# [1] https://stackoverflow.com/questions/2701998/sphinx-autodoc-is-not-automatic-enough#comment76402071_21665947
# [2] https://github.com/sphinx-doc/sphinx/issues/1861#issuecomment-354083328
# [3] https://github.com/goerz/better-apidoc
# [4] https://github.com/goerz/better-apidoc/issues/11
#
def setup(app):
    import sphinx.apidoc
    sphinx.ext.apidoc.main(['-f', '-T', '-M', '-e', '--implicit-namespaces',
                            '-o', 'doc/_generated', 'ConanTools'])
    # import better_apidoc
    # better_apidoc.main(['<arg...>', '-f', '-T', '-M', '-e', '--implicit-namespaces',
    #                     '-t', 'doc/templates',
    #                     '-o', 'doc/_generated', 'ConanTools'])

# -- General configuration ------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',        # extracts docstrings from python code
    'sphinx_autodoc_typehints',  # extracts type hints
    # 'sphinx.ext.autosummary',
    # 'sphinx.ext.doctest',
    # 'sphinx.ext.todo',
    # 'sphinx.ext.mathjax',
    'sphinx.ext.viewcode',  # include source code into the documentation
]

autoclass_content = "both"  # include both class docstring and __init__
autodoc_default_flags = [
    "members",
    "inherited-members",
    # "private-members",
    "show-inheritance"
]
# autosummary_generate = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
source_suffix = ['.rst', '.md']

# The encoding of source files.
# source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True


# -- Options for HTML output ----------------------------------------------

html_theme = 'nature'

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = False
