# -*- coding:utf-8 -*-
import sys

inPy3k = sys.version_info[0] == 3

class OldStyleClass:
    pass
ClassType = type(OldStyleClass)

ClassTypes = (type,)
if not inPy3k:
    ClassTypes = (type, ClassType)
