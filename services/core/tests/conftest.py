import os

os.environ.setdefault("PROBATE_FAKE", "1")
os.environ.setdefault("PROBATE_ADMIN_BAD_TOKENS_PER_IP", "0")  # many tests send wrong admin tokens
os.environ.setdefault("PROBATE_ADMIN_BAD_TOKENS_GLOBAL", "0")
os.environ.setdefault("PROBATE_WRONG_SECRET_DELAY", "0")  # the wrong-secret wait would slow tests
