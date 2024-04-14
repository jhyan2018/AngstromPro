# -*- coding: utf-8 -*-
"""
Created on Sun Apr 14 00:30:04 2024

@author: jiahaoYan
"""

class NumberExpression:
    @staticmethod
    def float_to_simplified_number(num, precision=3):
        number_exp = f"{num:.{precision+2}e}"  # Generating the exponent string with increased precision
        power = int(number_exp.split('e')[-1])  # Extracting the power of ten
        base = float(number_exp.split('e')[0])  # Extracting the base

        if -18 <= power < 15:
            quotient, remainder = divmod(power, 3)
            suffix = {
                -6: 'a', -5: 'f', -4: 'p', -3: 'n', -2: 'u', -1: 'm',
                 0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'
            }.get(quotient, '?')
            base *= 10 ** remainder 
        else:
            suffix = '?'

        return f"{base:.{precision}f}{suffix}"

    @staticmethod
    def simplified_number_to_float(num_str):
        suffix = num_str[-1]
        
        if suffix in {'a', 'f', 'p', 'n', 'u', 'm', 'K', 'M', 'G', 'T', 'k'}:
            num_base = float(num_str[:-1])
            power = {
                'a': 1e-18, 'f': 1e-15, 'p': 1e-12, 'n': 1e-9,
                'u': 1e-6, 'm': 1e-3, 'K': 1e3, 'M': 1e6,
                'G': 1e9, 'T': 1e12, 'k': 1e3
            }.get(suffix, 1)

            return num_base * power
        else:
            num_base = float(num_str)
            return num_base

