# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 23:36:22 2026

@author: jiahaoYan

Importing this package triggers all @register_process decorators so that
ProcessRegistry.__init__ can snapshot _PENDING.
"""

from . import crop
from . import simulate
from . import extend_region
from . import fft
from . import fft_filter
from . import spatial_mask
from . import background_subtract
from . import rotate
from . import perfect_lattice
from . import lock_in
from . import lf_correction
from . import math_ops
from . import r_map
from . import gap_map
from . import register
from . import cross_correlation
from . import extract_layer
from . import integral
from . import normalization
from . import line_circle_cut
from . import interpolation
from . import symmetrize
from . import smooth
from . import transpose
