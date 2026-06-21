"""Value objects and enums for the groups domain."""

from enum import Enum


class GroupType(str, Enum):
    EVENT = "EVENT"
    TRIP = "TRIP"
    GENERAL = "GENERAL"


class GroupStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class MemberRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class InviteStatus(str, Enum):
    ACTIVE = "ACTIVE"
    USED = "USED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
