# AI resource and retention policy

**Sample / Portfolio Assessment** — fictional FinFlow Technologies.

Inference requests are limited per authenticated user and feature, with a shared
in-process concurrency ceiling. A 429 includes Retry-After; acquired slots are
released on success, outage, invalid responses and cancellation. Defaults are 30
requests per 60 seconds per feature and two concurrent inference requests. Configure
AI_REQUEST_LIMIT, AI_RATE_WINDOW_SECONDS and AI_CONCURRENCY_LIMIT as needed.

The limiter is process-local. The supported single-process demo is bounded; a
multi-worker deployment must add a shared gateway limiter before being treated as
equivalently bounded. Status and read-only history views do not consume inference.

The maintenance worker prunes AI interaction diagnostics older than AI_RETENTION_DAYS
(default 30). It uses wall-clock UTC retention, independent of the fictional business
date. The latest cutoff and deleted count are observable at `/maintenance/policy`.
Administrators can trigger `/maintenance/prune-ai`; scheduled maintenance uses the
same service. GRC audit events are not deleted by this policy. Failed model output
or provider response fragments are not retained in error notes.
