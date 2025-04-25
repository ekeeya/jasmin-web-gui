import re

from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator


class ReeveEmailValidator(EmailValidator):
    user_regex = re.compile(
        r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*\Z"  # dot-atom
        r'|^"([\001-\010\013\014\016-\[\]-\177]|\\[\001-\011\013\014\016-\177])*"\Z)',  # quoted-string
        re.IGNORECASE,
    )
    domain_regex = re.compile(
        r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,63}|[A-Z0-9-]{2,}(?<!-))\Z",
        re.IGNORECASE,
    )


reeve_validate_email = ReeveEmailValidator()


def is_valid_address(address):
    if not address:
        return False

    try:
        reeve_validate_email(address)
    except ValidationError:
        return False

    return True
