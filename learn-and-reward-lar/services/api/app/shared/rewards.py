"""Coin economy constants (README section 11.2 reward rules)."""

# Completing a practice session rewards the learner.
REWARD_PRACTICE_COINS = 5

# A resource passing review rewards the contributor; the community pool receives a share.
REWARD_CONTRIBUTION_COINS = 10
REWARD_CONTRIBUTION_COMMUNITY_COINS = 5

# Course unlock (COURSE_UNLOCK): the buyer pays the course price; the community pool
# receives 70% and the platform 30% (README: -10 user / +7 community / +3 platform).
COMMUNITY_SHARE = 0.7
PLATFORM_SHARE = 0.3

# Ledger account identifiers used by the stub adapter and shared with Developer C's
# CoinService account naming (README section 8.5: user / community / platform / escrow).
ACCOUNT_TYPE_USER = "user"
ACCOUNT_TYPE_COMMUNITY = "community"
ACCOUNT_TYPE_PLATFORM = "platform"
PLATFORM_ACCOUNT_ID = "platform"
