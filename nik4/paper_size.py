import math
import re

def get_paper_size(name):
    """Returns paper size for name, [long, short] sides in mm"""
    # ISO A*
    m = re.match(r'^a?(\d)$', name)
    if m:
        return [math.floor(1000 / 2**((2*int(m.group(1)) - 1) / 4.0) + 0.2),
                math.floor(1000 / 2**((2*(int(m.group(1)) + 1) - 1) / 4.0) + 0.2)]
    # ISO B*
    m = re.match(r'^b(\d)$', name)
    if m:
        return [math.floor(1000 / 2**((int(m.group(1)) - 1) / 2.0) + 0.2),
                math.floor(1000 / 2**(int(m.group(1)) / 2.0) + 0.2)]
    # German extensions
    if name == '4a0':
        return [2378, 1682]
    if name == '2a0':
        return [1682, 1189]
    # US Legal
    if re.match(r'^leg', name):
        return [355.6, 215.9]
    # US Letter
    if re.match(r'^l', name):
        return [279.4, 215.9]
    # Cards
    if re.match(r'^c(?:re|ar)d', name):
        return [85.6, 54]
    return None
