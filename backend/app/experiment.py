"""A/B split. Half of users see the chart (test), half see the current flow (control).

The group comes from a hash of the user ID, so it never changes for a user and needs no database
column. Trade-off: the split cannot be changed later without a stored assignment.
"""
import hashlib

GROUPS = ("chart", "control")


def group_for(user_id: int) -> str:
    digest = hashlib.sha256(f"chart-exp-v1:{user_id}".encode()).digest()
    return GROUPS[digest[0] % 2]
