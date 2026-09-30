"""Roles defined by the platform spec (README section 8.1).

Shared here so the placeholder core module and the learning module agree on values.
Developer C owns the canonical definition.
"""

from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    LEARNER = "learner"
    CONTRIBUTOR = "contributor"
    ELDER_TEACHER = "elder_teacher"
    REVIEWER = "reviewer"
    COMMUNITY_ADMIN = "community_admin"
    PLATFORM_ADMIN = "platform_admin"
