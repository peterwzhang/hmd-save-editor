"""PyInstaller entry point - see .github/workflows/build.yml.

Importing hmd_editor.app (rather than pointing PyInstaller at a file inside
the package directly) keeps its relative imports resolving correctly:
PyInstaller executes whatever script it's given as top-level `__main__`, and
a module run that way can't use `from .foo import bar` - it has no parent
package. hmd_editor.app specifically (not hmd_editor.__main__) because
PyInstaller also refuses to bundle any submodule literally named __main__,
reserving that name for its own bootstrap.
"""

import sys

from hmd_editor.app import main

if __name__ == "__main__":
    sys.exit(main())
