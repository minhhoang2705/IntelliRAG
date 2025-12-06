"""
Locust User Behavior Profiles for Load Testing
"""

from .normal_user import NormalRAGUser, CasualUser, PowerUser
from .stress_user import StressTestUser, BurstUser, SpikeUser, SustainedLoadUser

__all__ = [
    # Normal users
    "NormalRAGUser",
    "CasualUser",
    "PowerUser",
    # Stress users
    "StressTestUser",
    "BurstUser",
    "SpikeUser",
    "SustainedLoadUser",
]
