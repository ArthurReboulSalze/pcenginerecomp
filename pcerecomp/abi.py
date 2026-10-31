"""Current runtime ABI and admitted original capture producer versions.

Capture producers retain their original labels; emission targets ABI below.
"""

ABI = 27
CAPTURE_ABIS = tuple(range(12, ABI + 1))
