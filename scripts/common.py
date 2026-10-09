# -*- coding: utf-8 -*-
"""Tiện ích dùng chung cho các script (chạy được trên Windows, macOS, Linux)."""
import sys


def utf8_console():
    """Windows: in tiếng Việt ra console/tệp không bị lỗi mã hóa."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding='utf-8')
        except Exception:
            pass
