"""Generate the Skills pages while MkDocs builds the site.

mkdocs-gen-files runs this file during `mkdocs build` and `mkdocs serve`.
The pages exist only inside the build. Never run this file directly:
outside MkDocs it would append to the real docs/index.md.
"""

import sys
from pathlib import Path

# Inside a build, MkDocs is already imported. Run directly, it is not.
if "mkdocs" not in sys.modules:
    sys.exit("Run this through MkDocs: just docs")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mkdocs_gen_files  # noqa: E402

from skill_pages import build_pages  # noqa: E402

for page in build_pages():
    with mkdocs_gen_files.open(page.path, page.mode) as f:
        f.write(page.content)
    if page.edit_path:
        mkdocs_gen_files.set_edit_path(page.path, page.edit_path)
