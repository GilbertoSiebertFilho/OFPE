"""OFPE Field Data Platform.

Build agricultural guidance lines from field boundaries, recorded machine data
or hand-entered AB parameters, and export them in the file format a given
display actually reads.

The layers, outermost first:

``web``       FastAPI app and the browser client.
``db``        SQLite persistence.
``catalog``   what every brand and terminal will accept, and how sure we are.
``readers``   somebody else's file  ->  our objects.
``writers``   our objects           ->  somebody else's file.
``generate``  authoring and expanding guidance patterns.
``fitting``   recovering a line from a track a machine already drove.
``models``    the canonical objects everything else speaks.
``geo``       the projection and geodesy the line maths sits on.
"""

__version__ = "1.0.0"

__all__ = ["__version__"]
