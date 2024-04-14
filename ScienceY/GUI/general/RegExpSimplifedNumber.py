# -*- coding: utf-8 -*-
"""
Created on Sun Apr 14 00:13:18 2024

@author: jiahaoYan
"""

from PyQt5.QtCore import QRegularExpression

class RegExpSimplifiedNumber:
    # Regular expressions for integer and decimal numbers
    rxInteger = QRegularExpression(r'^-?\d{1,4}\.?[TGMKkmunpfa]?$')
    rxDecimals = QRegularExpression(r'^-?\d{1,4}\.\d{1,3}[TGMKkmunpfa]?$')

    @staticmethod
    def isSimplifiedNumber(s):
        """
        Check if the string `s` is a simplified number according to predefined patterns.
        
        Parameters:
            s (str): The string to check.
            
        Returns:
            bool: True if the string matches the integer or decimal patterns, False otherwise.
        """
        # Match integer pattern
        match_integer = RegExpSimplifiedNumber.rxInteger.match(s)
        # Match decimal pattern
        match_decimal = RegExpSimplifiedNumber.rxDecimals.match(s)

        # If either pattern matches from the start, return True
        return match_integer.hasMatch() or match_decimal.hasMatch()

