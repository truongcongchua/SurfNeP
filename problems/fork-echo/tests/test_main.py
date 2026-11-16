# Bộ test echo dùng chung: judge/runner/suites.py (thiết kế: docs/TEST-DESIGN.md).
from suites import echo_suite

globals().update(echo_suite(concurrent=True, slow_reader=True, zombie_check=True))
