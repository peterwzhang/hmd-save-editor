# Third-Party Notices

This project is MIT-licensed (see [LICENSE](LICENSE)), but the packaged
application links against software under other licenses.
This file lists those and the obligations that come with them.

## Qt for Python (PySide6)

The GUI is built on [PySide6](https://pypi.org/project/PySide6/), the
official Qt for Python bindings published by The Qt Company.
PySide6 is distributed under the GNU Lesser General Public License v3
(LGPLv3), which incorporates GPLv3 by reference.
Copies of both are included in this repository:

- [licenses/LGPL-3.0.txt](licenses/LGPL-3.0.txt)
- [licenses/GPL-3.0.txt](licenses/GPL-3.0.txt)

Qt/PySide6 source is publicly available from
[the Qt for Python project](https://download.qt.io/official_releases/QtForPython/)
and [PyPI](https://pypi.org/project/PySide6/), which satisfies the LGPL's
source-availability requirement.

Packaged (`.exe`) builds of this application link Qt/PySide6 dynamically -
the Qt shared libraries ship as separate files alongside the executable
rather than being statically fused into it, so they can be inspected,
replaced, or relinked as the LGPL requires.
No modifications have been made to Qt or PySide6 itself.

## PyInstaller

Packaged builds are produced with [PyInstaller](https://pyinstaller.org/).
PyInstaller's bootloader (the small stub embedded in the frozen executable)
is licensed under the GPL with an explicit exception permitting its use in
applications under any license, including closed-source ones - this
project's own MIT license is unaffected by that bundling.
See [PyInstaller's license](https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt)
for the exact terms.

## Game assets

Sprite images and other art from *How Many Dudes?* (howmanydudes.com) are
never bundled with this application or committed to this repository - see
`.gitignore`'s `cache/sprites/` entry.
The app fetches them on demand, at runtime, directly from the game's own
site into a local cache on the user's machine.
`data/catalog.json` contains item names, kinds, and descriptions scraped
from the game's public wiki pages for lookup purposes; no image assets are
included.
