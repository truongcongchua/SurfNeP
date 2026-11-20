# Bộ test telnet dùng chung: judge/runner/suite_telnet.py (thiết kế: docs/TEST-DESIGN.md).
from suite_telnet import telnet_suite

globals().update(telnet_suite(fork=True))
