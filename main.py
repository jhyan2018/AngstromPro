# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 18:26:31 2026

@author: jiahaoYan
"""
from angstrompro.app.main import main

def running_in_ipython():
    try:
        get_ipython()
        return True
    except NameError:
        return False

if __name__ == "__main__":
    in_ipython = running_in_ipython()
    main(
        external_namespace=globals(),
        start_event_loop=not in_ipython,
    )