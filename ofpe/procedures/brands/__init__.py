"""Brand knowledge. Importing a module registers its procedures.

Order does not matter -- the registry indexes lazily -- but the modules are
listed roughly by installed base so the file reads like the market.
"""

from . import (  # noqa: F401  (imported for the side effect of registering)
    john_deere,
    cnh,
    trimble,
    ag_leader,
    raven,
    isobus,
    specialists,
    media,
)
