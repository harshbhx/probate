import os

os.environ.setdefault("PROBATE_FAKE", "1")
os.environ.setdefault("PROBATE_ADMIN_BAD_TOKENS_PER_IP", "0")  # many tests send wrong admin tokens
