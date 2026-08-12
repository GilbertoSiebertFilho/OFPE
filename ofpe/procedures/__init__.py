"""The procedure knowledge base: how to get files in and out of a display.

This is the centre of the platform. Generating a guidance line is a side
quest; the thing people actually need at 6am with a USB stick in their hand is
*where exactly does this file go, and which button do I press*.

A procedure is addressed by five coordinates, and the UI asks for them in that
order because each answer narrows the next:

    equipment type -> brand -> monitor -> software version -> objective -> transport

The **version** axis matters more than it looks. The same display with a
different software release moves menus, renames "Data Transfer" to "File
Manager", and in one notable case stops accepting a file format it used to
take. Where a version genuinely changes the steps there is a version-specific
entry; where it does not, one entry marked ``ANY_VERSION`` covers the lot, and
:func:`resolve` reports which one it used so the answer is never silently
generic.

Layout::

    _core.py     types, registry and resolver
    brands/      the knowledge, one module per manufacturer family
"""

from ._core import *  # noqa: F401,F403
from ._core import __all__  # noqa: F401
from .screens import (  # noqa: F401
    SCREEN_ICONS,
    ScreenIcon,
    folder_for,
    icon_credit,
    icons_for,
)
from .walkthroughs import (  # noqa: F401
    VERSION_HELP,
    WALKTHROUGHS,
    ProcedureWalk,
    VersionHelp,
    VersionStep,
    WalkStep,
    version_help_for,
    walkthrough_for,
)
from . import brands  # noqa: F401  (populates the registry on import)
from . import voice  # noqa: F401  (reads that registry, so it comes after)
from .checklist import (  # noqa: F401
    CHECKLISTS,
    Check,
    Stage,
    checklist_for,
)
