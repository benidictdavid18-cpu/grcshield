"""Counters initialize from existing references at first allocation, never reset on seed."""

REFERENCE_POLICY = "Existing reference high-water marks are preserved; allocation is transactional."
