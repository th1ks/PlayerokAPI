"""Конфигурация Sphinx."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PlayerokAPI import __version__

project = "PlayerokAPI"
author = "th1ks"
copyright = "2026, th1ks"
release = __version__
version = __version__
language = "ru"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "myst_parser",
]

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
exclude_patterns = ["_build"]

# --- autodoc -------------------------------------------------------------

autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented_params"
autodoc_class_signature = "separated"
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
    "member-order": "bysource",
}
# Внутренние переменные окружения в сигнатурах не нужны.
autodoc_preserve_defaults = True

# httpx не публикует objects.inv, поэтому в маппинге только стандартная библиотека.
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
intersphinx_disabled_reftypes = ["*"]

nitpicky = False

# --- MyST ----------------------------------------------------------------

myst_enable_extensions = ["colon_fence", "deflist", "fieldlist"]
myst_heading_anchors = 3

# --- HTML ----------------------------------------------------------------

html_theme = "furo"
html_title = f"PlayerokAPI {release}"
html_static_path: list[str] = []
html_theme_options = {
    "source_repository": "https://github.com/th1ks/PlayerokAPI",
    "source_branch": "main",
    "source_directory": "docs/",
}
