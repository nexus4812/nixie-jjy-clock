"""macOSのKiCad SWIG実行で必要なwxアプリケーションを用意する。"""

import sys


def initialize_gui_runtime():
    if sys.platform == "darwin":
        import wx
        return wx.App(False)
    return None
