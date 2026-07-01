# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 23:36:22 2026

@author: jiahaoYan

Importing this package triggers all @register_process decorators so that
ProcessRegistry.__init__ can snapshot _PENDING.
"""

from . import crop2d
from . import extend_region
from . import fft
from . import fft_filter
from . import spatial_mask
from . import background_subtract
from . import rotate2d
from . import perfect_lattice
