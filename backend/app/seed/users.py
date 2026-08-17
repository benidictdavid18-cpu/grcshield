"""Demo accounts.

Three accounts, published in the README on purpose so the demo can be opened by anyone
looking at the portfolio. They are demo credentials for a fictional company holding
fictional data; treating them as secrets would be theatre.

The auditor account is the point of the exercise: read everything, change nothing. That
role is only meaningful because unauthenticated reads are refused — an ISMS holds the
map of an organisation's weaknesses, and "read-only" has to mean something.
"""

from typing import NamedTuple


class UserSpec(NamedTuple):
    username: str
    full_name: str
    email: str
    role: str
    password_setting: str


DEMO_USERS: list[UserSpec] = [
    UserSpec(
        "auditor", "Demo Auditor (read-only)", "auditor@finflow.example",
        "AUDITOR", "demo_auditor_password",
    ),
    UserSpec(
        "isms.manager", "Demo ISMS Manager", "isms.manager@finflow.example",
        "ISMS_MANAGER", "demo_manager_password",
    ),
]
