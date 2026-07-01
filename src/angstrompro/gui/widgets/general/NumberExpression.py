# -*- coding: utf-8 -*-
"""
Created on Sun Apr 14 00:30:04 2024

@author: jiahaoYan
"""


class NumberExpression:
    @staticmethod
    def float_to_simplified_number(num, precision=3):
        number_exp = f"{num:.{precision+2}e}"
        power = int(number_exp.split('e')[-1])
        base = float(number_exp.split('e')[0])

        if -18 <= power < 15:
            quotient, remainder = divmod(power, 3)
            suffix = {
                -6: 'a', -5: 'f', -4: 'p', -3: 'n', -2: 'u', -1: 'm',
                 0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'
            }.get(quotient, None)
            if suffix is not None:
                base *= 10 ** remainder
                return f"{base:.{precision}f}{suffix}"

        return f"{num:.{precision}e}"

    @staticmethod
    def simplified_number_to_float(num_str):
        suffix = num_str[-1]

        if suffix in {'a', 'f', 'p', 'n', 'u', 'm', 'K', 'M', 'G', 'T', 'k'}:
            num_base = float(num_str[:-1])
            power = {
                'a': 1e-18, 'f': 1e-15, 'p': 1e-12, 'n': 1e-9,
                'u': 1e-6,  'm': 1e-3,  'K': 1e3,   'M': 1e6,
                'G': 1e9,   'T': 1e12,  'k': 1e3
            }.get(suffix, 1)
            return num_base * power
        else:
            return float(num_str)  # handles both plain floats and scientific notation (e.g. "1.23e-20")
