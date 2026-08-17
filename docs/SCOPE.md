# Framework scope decisions

> **Sample / Portfolio Assessment.** FinFlow Technologies is a fictional company.
> No certification body or audit firm has assessed any of this.

This document records what GRCShield assesses, what it only maps, what it defers, and
why. Scope is the first thing an auditor asks about and the first thing a portfolio
project usually gets wrong — four frameworks at 15% depth each demonstrates less than
one framework done properly.

## FinFlow at a glance

| Attribute | Value |
| --- | --- |
| Headcount | ~40, fully remote |
| Premises | None owned or leased |
| Production infrastructure | AWS, eu-west-1 |
| Product | SaaS payments; cardholder data handled by a third-party PSP |
| Customers | EU and India |
| Identity | Okta |
| Source control | GitHub |
| Endpoints | Company-issued macOS laptops |
| Development | Entirely in-house |

Every applicability decision below traces back to a row in that table.

## The four frameworks

### ISO/IEC 27001:2022 — PRIMARY

All 93 Annex A controls are catalogued with their official identifiers and titles
(A.5 Organizational 37, A.6 People 8, A.7 Physical 14, A.8 Technological 34). Each
receives an applicability decision, recorded formally in the Statement of
Applicability required by Clause 6.1.3 d).

ISO is primary because it is the only one of the four that is *certifiable against a
control set*, which makes the Statement of Applicability a real artefact with real
consequences rather than a spreadsheet.

### AICPA SOC 2 Trust Services Criteria — SECONDARY

SOC 2 is reached by **mapping from** ISO, never assessed on its own. Two consequences
follow, and both are deliberate:

1. An ISO control that is excluded from scope produces no evidence, so it cannot
   satisfy a Trust Services criterion. The seed loader raises rather than writing such
   a mapping.
2. FinFlow elects Security (Common Criteria), Availability and Confidentiality. It does
   **not** elect Processing Integrity or Privacy. Privacy obligations are met through
   the GDPR Article 30 and 35 modules instead of a second, parallel privacy scorecard.

That second decision leaves exactly one visible gap: **A.5.34 (Privacy and protection
of PII) has no SOC 2 mapping.** The gap is left visible rather than filled with a
loose mapping into an unelected category.

Criteria descriptions in the seed data are plain-English summaries written for this
project. They are not the AICPA's wording, which is copyrighted.

### NIST CSF 2.0 — ROADMAP

Registered, not assessed, no control catalogue loaded.

CSF 2.0 is an outcome-and-profile framework. For a 40-person company it would largely
restate the ISO control set in different language, so running both concurrently
produces breadth without adding assurance. Revisit after the ISMS completes one full
internal audit cycle.

### GDPR — ROADMAP, with two live modules

Registered, not assessed article-by-article.

GDPR is a legal obligation, not a control framework. A control-by-control scorecard
against a regulation invites false precision — "87% GDPR compliant" is not a statement
anyone can defend. Two operational artefacts are built as real modules instead:

- **Record of Processing Activities** (Article 30)
- **Data Protection Impact Assessments** (Article 35)

Legal and regulatory obligations still enter the ISMS, through **A.5.31** (Legal,
statutory, regulatory and contractual requirements) and **A.5.34** (Privacy and
protection of PII).

## Provisional exclusions

Nine of the 93 Annex A controls are provisionally out of scope. Each exclusion note
records **where the risk went** — a control that is merely "not applicable" with no
onward destination is an unmanaged risk with paperwork.

| Control | Title | Where the risk went |
| --- | --- | --- |
| A.7.1 | Physical security perimeters | AWS, shared responsibility model; assured via provider SOC 2 Type II |
| A.7.2 | Physical entry | AWS, shared responsibility model |
| A.7.3 | Securing offices, rooms and facilities | Home-working risk → A.6.7 and A.7.9 |
| A.7.4 | Physical security monitoring | Logical monitoring → A.8.16 |
| A.7.5 | Protecting against physical and environmental threats | AWS; residual availability risk → A.8.14 |
| A.7.6 | Working in secure areas | Logical restriction → A.8.3 |
| A.7.11 | Supporting utilities | AWS, shared responsibility model |
| A.7.12 | Cabling security | Data-in-transit risk → A.8.24 |
| A.8.30 | Outsourced development | No outsourced development exists |

Five A.7 controls are **kept**, because a remote workforce does not eliminate physical
risk, it relocates it: A.7.7 (clear desk and screen), A.7.8 (equipment siting), A.7.9
(assets off-premises), A.7.10 (storage media), A.7.13 (equipment maintenance) and
A.7.14 (secure disposal). Excluding all fourteen A.7 controls is the standard mistake
in a remote-first SoA.

As of Phase 3 the **Statement of Applicability is the authoritative record**. It carries
the full inclusion and exclusion justifications, owners, review dates and approval, and
`scripts/check_seed_data.py` fails if the SoA exclusions ever disagree with the nine
listed above. The `in_scope` flag on `framework_controls` remains only so that the SOC 2
crosswalk has something to filter on.

See [SOA.md](SOA.md) for the applicability rules and how they are enforced.

## Report set

Three reports, not seven. Each has a named audience and a decision it supports:

| Report | Audience | Decision it supports |
| --- | --- | --- |
| Risk Register | Risk owners, management review | Which risks exceed category appetite and need treatment or formal acceptance |
| SoA + Gap Analysis | Certification auditor, ISMS manager | Whether every control has a defensible applicability decision, and where gaps need remediation |
| Executive Summary | Founders, board | Where to spend the next quarter of budget and headcount |

## What is deliberately absent

Notification cards, breadcrumbs, rate-limiting middleware, and any chart not backed by
a KRI defined in Phase 6. None of these carry assurance value, and each one is
surface area to defend.

## Mapping statistics

Produced by `scripts/check_seed_data.py`:

```
Annex A controls      : 93  {'A.5': 37, 'A.6': 8, 'A.7': 14, 'A.8': 34}
Provisional exclusions: 9
SOC 2 criteria        : 61  (33 Common Criteria)
Elected TSC criteria  : 38
ISO -> SOC 2 mappings : 127  covering 83 ISO controls
In-scope but unmapped : ['A.5.34']
```
