import string
from typing import Optional


# https://docs.gitlab.com/ee/ci/variables/predefined_variables.html
def slug(input: Optional[str]) -> Optional[str]:
    if input is None:
        return None
    whitelist = set(string.ascii_letters + string.digits)

    def sanitize_char(ch):
        if ch in whitelist:
            return ch.lower()
        return '-'

    return ''.join([sanitize_char(ch) for ch in input]).strip('-')
