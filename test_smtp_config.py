#!/usr/bin/env python3
"""
SentriEnv — Root Gmail SMTP Diagnostic Shortcut
Delegates directly to sentrienv/test_smtp_config.py
"""
import os
import sys

target = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sentrienv", "test_smtp_config.py")
if os.path.isfile(target):
    with open(target, "rb") as f:
        code = compile(f.read(), target, "exec")
        exec(code)
else:
    print(f"Error: Could not locate {target}")
    sys.exit(1)
