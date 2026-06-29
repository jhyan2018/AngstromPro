# -*- coding: utf-8 -*-
"""
Created on Sun Apr 14 00:13:24 2024

@author: jiahaoYan
"""
from angstrompro.utils.qt_compat import QtCore


class RegExpSimplifiedNumber:
    rxInteger  = QtCore.QRegularExpression(r'^-?\d{1,4}\.?[TGMKkmunpfa]?$')
    rxDecimals = QtCore.QRegularExpression(r'^-?\d{1,4}\.\d{1,3}[TGMKkmunpfa]?$')

    @staticmethod
    def isSimplifiedNumber(s):
        match_integer = RegExpSimplifiedNumber.rxInteger.match(s)
        match_decimal  = RegExpSimplifiedNumber.rxDecimals.match(s)
        return match_integer.hasMatch() or match_decimal.hasMatch()
