# Bộ test chat dùng chung: judge/runner/suite_chat.py (thiết kế: docs/TEST-DESIGN.md).
from suite_chat import chat_suite

globals().update(chat_suite())
