# Ροές εργασίας και εγκρίσεις 2026

Συνθετικά δεδομένα NexaTech Solutions.

## WF-SM-001 · BlueHarbor – αντιπρόταση και τελική προσφορά

- **workflow id:** WF-SM-001
- **persona id:** PERS-SM-APETROU
- **Τίτλος:** BlueHarbor – αντιπρόταση και τελική προσφορά
- **related decisions:**
  - DEC-SM-001
  - DEC-SM-002
- **start time:** 2026-02-10T14:02:00+02:00
- **end time:** 2026-02-13T12:10:00+02:00
- **Βήματα:**
  - **ts:** 2026-02-10T14:02:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** open_opportunity
  - **detail:** OPP-2026-014

  - **ts:** 2026-02-10T14:05:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** view_account_history
  - **detail:** 2 orders, avg days-to-pay 31,5, overdue 0

  - **ts:** 2026-02-10T14:11:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** open_margin_sheet
  - **detail:** scenarios 7% / 10% / 15%

  - **ts:** 2026-02-10T15:40:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** edit_quote_lines
  - **detail:** QT-2026-0112: discount 7%, add line 'Onboarding 4h – €0', delivery split 30/20

  - **ts:** 2026-02-10T15:42:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** approve_discount
  - **detail:** 7% approved by Sales Manager (SALE-DISC-v1 5–10%)

  - **ts:** 2026-02-10T16:20:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Outlook
  - **action:** send_email
  - **detail:** E01 counteroffer, non-binding, valid to 20/02

  - **ts:** 2026-02-11T09:10:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Outlook
  - **action:** send_email
  - **detail:** E02 Finance review request (net90 → CEO cc)

  - **ts:** 2026-02-13T09:05:00+02:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ERP
  - **action:** set_payment_terms
  - **detail:** NET45, FIN-APR-2026-009

  - **ts:** 2026-02-13T11:20:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** update_quote_terms
  - **detail:** payment terms NET45 (ref FIN-APR-2026-009)

  - **ts:** 2026-02-13T12:10:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** send_final_quote_manual
  - **detail:** Ο Sales Manager πάτησε ο ίδιος αποστολή, μετά από έλεγχο

## WF-SM-002 · Orion – έγκριση 9% και προσφορά

- **workflow id:** WF-SM-002
- **persona id:** PERS-SM-APETROU
- **Τίτλος:** Orion – έγκριση 9% και προσφορά
- **related decisions:**
  - DEC-SM-003
- **start time:** 2026-03-09T17:14:00+02:00
- **end time:** 2026-03-13T12:30:00+02:00
- **Βήματα:**
  - **ts:** 2026-03-09T17:14:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Teams
  - **action:** request_margin_scenarios
  - **detail:** 8/9/10/12%

  - **ts:** 2026-03-09T17:28:00+02:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** NexaCRM
  - **action:** export_margin_sheet
  - **detail:** QT-2026-0168

  - **ts:** 2026-03-11T10:00:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Teams
  - **action:** negotiation_call
  - **detail:** T01, recorded with consent

  - **ts:** 2026-03-11T10:41:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** log_call_outcome
  - **detail:** 9%, single order, 3 deliveries

  - **ts:** 2026-03-11T16:50:00+02:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** NexaCRM
  - **action:** create_quote_draft
  - **detail:** QT-2026-0168 v2 draft 9%

  - **ts:** 2026-03-12T09:30:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** review_draft
  - **detail:** edits: deliverables per store, removed generic intro

  - **ts:** 2026-03-12T09:35:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** approve_discount
  - **detail:** 9% approved by Sales Manager (SALE-DISC-v1), margin 24%

  - **ts:** 2026-03-13T12:30:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** send_final_quote_manual
  - **detail:** net45 ref FIN-APR-2026-014

## WF-SM-003 · Orion – handoff όρων στο Finance

- **workflow id:** WF-SM-003
- **persona id:** PERS-SM-APETROU
- **Τίτλος:** Orion – handoff όρων στο Finance
- **related decisions:**
  - DEC-SM-004
- **start time:** 2026-03-12T11:20:00+02:00
- **end time:** 2026-03-12T15:20:00+02:00
- **Βήματα:**
  - **ts:** 2026-03-12T11:20:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** view_account_history
  - **detail:** 5 orders since 2023, avg 33 days, 1 late (6d, 2024)

  - **ts:** 2026-03-12T11:25:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** ERP (read-only)
  - **action:** view_open_exposure
  - **detail:** €0

  - **ts:** 2026-03-12T11:35:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Outlook
  - **action:** send_email
  - **detail:** E03 Finance review request net45

  - **ts:** 2026-03-12T15:10:00+02:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ERP
  - **action:** approve_payment_terms
  - **detail:** NET45 per order, FIN-APR-2026-014

  - **ts:** 2026-03-12T15:20:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** update_quote_terms
  - **detail:** NET45 (this order only)

## WF-SM-004 · AegeanWorks – κλιμάκωση αποκλειστικότητας και pilot

- **workflow id:** WF-SM-004
- **persona id:** PERS-SM-APETROU
- **Τίτλος:** AegeanWorks – κλιμάκωση αποκλειστικότητας και pilot
- **related decisions:**
  - DEC-SM-005
- **start time:** 2026-04-14T09:40:00+03:00
- **end time:** 2026-04-22T11:00:00+03:00
- **Βήματα:**
  - **ts:** 2026-04-14T09:40:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** view_account_history
  - **detail:** 2 orders €18.400, on-time

  - **ts:** 2026-04-14T10:05:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** report_accounts_by_region
  - **detail:** Δωδεκάνησα: 2 integrators, €46k 2025

  - **ts:** 2026-04-14T11:30:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Outlook
  - **action:** send_email
  - **detail:** E04 escalation to CEO

  - **ts:** 2026-04-14T11:32:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Outlook Calendar
  - **action:** create_tentative_meeting
  - **detail:** 16/04 10:00, CEO

  - **ts:** 2026-04-16T10:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Teams
  - **action:** meeting
  - **detail:** με CEO, σημείωση N03

  - **ts:** 2026-04-17T18:05:00+03:00
  - **Ποιος:** Δανάη Καρρά
  - **system:** Outlook
  - **action:** send_email
  - **detail:** E05 decision: no exclusivity, 6-month pilot

  - **ts:** 2026-04-21T16:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** create_quote_draft
  - **detail:** QT-2026-0204 pilot, net30 per order, limit €15k

  - **ts:** 2026-04-21T16:05:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** submit_for_review
  - **detail:** reviewer: Δανάη Καρρά

  - **ts:** 2026-04-22T11:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** send_final_quote_manual
  - **detail:** μετά από έγκριση CEO

## WF-SM-005 · Lumen Dental – απόρριψη draft 8%

- **workflow id:** WF-SM-005
- **persona id:** PERS-SM-APETROU
- **Τίτλος:** Lumen Dental – απόρριψη draft 8%
- **related decisions:**
  - DEC-SM-006
- **start time:** 2026-05-20T11:05:00+03:00
- **end time:** 2026-05-21T10:15:00+03:00
- **Βήματα:**
  - **ts:** 2026-05-20T11:05:00+03:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** NexaCRM
  - **action:** submit_discount_approval
  - **detail:** QT-2026-0247, 8%

  - **ts:** 2026-05-20T11:12:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** open_margin_sheet
  - **detail:** 8% → 20,1%

  - **ts:** 2026-05-20T11:15:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** view_account_history
  - **detail:** new account, no history

  - **ts:** 2026-05-20T11:20:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** reject_discount
  - **detail:** reason field: 'margin <22%, no counterpart'

  - **ts:** 2026-05-20T15:30:00+03:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** NexaCRM
  - **action:** create_quote_draft
  - **detail:** 3% + Onboarding 2h €0

  - **ts:** 2026-05-21T10:15:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** send_final_quote_manual
  - **detail:** after review

## WF-SM-006 · Pineworks – δομή όρων με Finance

- **workflow id:** WF-SM-006
- **persona id:** PERS-SM-APETROU
- **Τίτλος:** Pineworks – δομή όρων με Finance
- **related decisions:**
  - DEC-SM-007
- **start time:** 2026-06-09T16:00:00+03:00
- **end time:** 2026-06-12T11:00:00+03:00
- **Βήματα:**
  - **ts:** 2026-06-09T16:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** view_account_history
  - **detail:** 3 orders €41k, avg 38 days

  - **ts:** 2026-06-09T16:20:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** open_margin_sheet
  - **detail:** 3% → 26%

  - **ts:** 2026-06-09T17:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** create_delivery_schedule
  - **detail:** Jul ATH / Aug SKG / Sep PAT

  - **ts:** 2026-06-10T10:20:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Outlook
  - **action:** send_email
  - **detail:** E06 to Finance

  - **ts:** 2026-06-11T09:40:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ERP
  - **action:** report_exposure
  - **detail:** €6.200 open, not overdue

  - **ts:** 2026-06-11T11:15:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ERP
  - **action:** approve_payment_terms
  - **detail:** NET60 conditional, FIN-APR-2026-031

  - **ts:** 2026-06-11T14:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** update_quote_terms
  - **detail:** NET60 + prepayment 30% + 3 conditions verbatim

  - **ts:** 2026-06-12T11:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** send_final_quote_manual
  - **detail:** QT-2026-0289

## WF-SM-007 · Kallisto – από support σε αλλαγή configuration

- **workflow id:** WF-SM-007
- **persona id:** PERS-SM-APETROU
- **Τίτλος:** Kallisto – από support σε αλλαγή configuration
- **related decisions:**
  - DEC-SM-008
- **start time:** 2026-07-03T10:15:00+03:00
- **end time:** 2026-07-10T11:22:00+03:00
- **Βήματα:**
  - **ts:** 2026-07-03T10:15:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** open_margin_sheet
  - **detail:** 14% → 16%; 5% → 24,1%

  - **ts:** 2026-07-03T10:35:00+03:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** NexaCRM
  - **action:** send_quote
  - **detail:** rev.1: 5% + onboarding 4h + support 8h (non-binding indicative)

  - **ts:** 2026-07-06T09:30:00+03:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** NexaCRM
  - **action:** log_customer_response
  - **detail:** rejected: in-house IT, budget cap €33.000

  - **ts:** 2026-07-06T10:12:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** open_attachment
  - **detail:** customer usage profile

  - **ts:** 2026-07-06T14:40:00+03:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** Product catalog
  - **action:** price_alternative_config
  - **detail:** i5/16/512 list €34.300; i7 x26 within budget

  - **ts:** 2026-07-06T14:50:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** open_margin_sheet
  - **detail:** i5 at 4% → 23,5%

  - **ts:** 2026-07-08T12:30:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** create_quote_revision
  - **detail:** rev.2 (i5) + rev.2b (26×i7)

  - **ts:** 2026-07-08T12:40:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Outlook
  - **action:** send_email
  - **detail:** E07

  - **ts:** 2026-07-10T11:20:00+03:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** NexaCRM
  - **action:** mark_won
  - **detail:** rev.2 i5

## WF-SM-008 · Μετάβαση CRM σε SALE-DISC-v2

- **workflow id:** WF-SM-008
- **persona id:** PERS-SM-APETROU
- **Τίτλος:** Μετάβαση CRM σε SALE-DISC-v2
- **start time:** 2026-08-11T10:05:00+03:00
- **end time:** 2026-08-15T00:00:00+03:00
- **Βήματα:**
  - **ts:** 2026-08-11T10:09:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Teams
  - **action:** answer_team_question
  - **detail:** ST-C08 effective date

  - **ts:** 2026-08-13T15:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM Admin
  - **action:** clone_quote_template
  - **detail:** QTEMPLATE-v1 → QTEMPLATE-v2

  - **ts:** 2026-08-13T15:30:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM Admin
  - **action:** edit_approval_routing
  - **detail:** ≤6% & margin≥23% draft; 6,01–12% → SM; >12% → CEO

  - **ts:** 2026-08-13T15:45:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM Admin
  - **action:** add_required_field
  - **detail:** Free support hours (≤4 draft, 5–12 SM)

  - **ts:** 2026-08-14T11:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM Admin
  - **action:** test_routing_sandbox
  - **detail:** test cases 5,5% / 6% / 9% / 12,5%

  - **ts:** 2026-08-14T16:30:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** SharePoint
  - **action:** publish_document
  - **detail:** D01 team guide

  - **ts:** 2026-08-14T16:35:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM Admin
  - **action:** schedule_activation
  - **detail:** QTEMPLATE-v2 active 2026-08-15 00:00

  - **ts:** 2026-08-15T00:00:00+03:00
  - **Ποιος:** system
  - **system:** NexaCRM
  - **action:** activate_template
  - **detail:** QTEMPLATE-v2 live; v1 archived

## WF-SM-009 · Northbridge – επιβεβαίωση margin και έγκριση 11%

- **workflow id:** WF-SM-009
- **persona id:** PERS-SM-APETROU
- **Τίτλος:** Northbridge – επιβεβαίωση margin και έγκριση 11%
- **related decisions:**
  - DEC-SM-010
- **start time:** 2026-09-14T13:26:00+03:00
- **end time:** 2026-09-17T14:40:00+03:00
- **Βήματα:**
  - **ts:** 2026-09-14T13:30:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** open_margin_sheet
  - **detail:** 11% → 25,6% (cost date 2026-07-08)

  - **ts:** 2026-09-14T13:36:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** flag_stale_cost
  - **detail:** cost >30 days old

  - **ts:** 2026-09-15T15:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Teams
  - **action:** negotiation_call
  - **detail:** T02

  - **ts:** 2026-09-15T16:10:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Teams
  - **action:** request_margin_verification
  - **detail:** SF-C06 to Finance

  - **ts:** 2026-09-16T10:30:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ERP
  - **action:** recalculate_margin
  - **detail:** current cost → 25,0% at 11%

  - **ts:** 2026-09-16T10:34:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** approve_discount
  - **detail:** 11% approved by SM (SALE-DISC-v2 >6–12%)

  - **ts:** 2026-09-16T17:30:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Outlook
  - **action:** send_email
  - **detail:** E08 to Sales/Finance

  - **ts:** 2026-09-17T11:40:00+03:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** NexaCRM
  - **action:** create_quote_draft
  - **detail:** 11%, support 4h

  - **ts:** 2026-09-17T14:40:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** send_final_quote_manual
  - **detail:** after review

## WF-SM-010 · Northbridge – όριο support στις 4h

- **workflow id:** WF-SM-010
- **persona id:** PERS-SM-APETROU
- **Τίτλος:** Northbridge – όριο support στις 4h
- **related decisions:**
  - DEC-SM-011
- **start time:** 2026-09-15T15:01:00+03:00
- **end time:** 2026-09-17T11:50:00+03:00
- **Βήματα:**
  - **ts:** 2026-09-15T15:03:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Teams
  - **action:** clarify_scope
  - **detail:** support scope: setup, PMS, training

  - **ts:** 2026-09-15T15:36:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** view_service_history
  - **detail:** prior PMS integration 2025, 3,5h

  - **ts:** 2026-09-15T15:40:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** set_field
  - **detail:** Free support hours = 4

  - **ts:** 2026-09-16T09:00:00+03:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** SharePoint
  - **action:** attach_document
  - **detail:** check-in quick guide + video link

  - **ts:** 2026-09-17T11:50:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** add_quote_note
  - **detail:** additional hours at standard rate

## WF-SM-011 · Kestrel – πάγωμα quote και exception review

- **workflow id:** WF-SM-011
- **persona id:** PERS-SM-APETROU
- **Τίτλος:** Kestrel – πάγωμα quote και exception review
- **related decisions:**
  - DEC-SM-012
- **start time:** 2026-10-05T16:22:00+03:00
- **end time:** 2026-10-21T11:30:00+03:00
- **Βήματα:**
  - **ts:** 2026-10-05T16:30:00+03:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** NexaCRM
  - **action:** create_quote_draft
  - **detail:** QT-2026-0423 4% + 6h

  - **ts:** 2026-10-06T11:40:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ERP
  - **action:** flag_overdue
  - **detail:** INV-2026-0877 €9.400, 38 days

  - **ts:** 2026-10-06T11:44:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** ERP (read-only)
  - **action:** view_ar_aging
  - **detail:** confirmed 38d overdue

  - **ts:** 2026-10-06T11:46:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** set_quote_status
  - **detail:** On hold – credit

  - **ts:** 2026-10-07T09:05:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Outlook
  - **action:** send_email
  - **detail:** E09 exception review request

  - **ts:** 2026-10-07T12:15:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Teams
  - **action:** customer_call
  - **detail:** Finance Director, N05

  - **ts:** 2026-10-09T13:15:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ERP
  - **action:** record_exception_review
  - **detail:** FIN-EXC-2026-004

  - **ts:** 2026-10-20T16:05:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ERP
  - **action:** record_payment
  - **detail:** INV-2026-0877 paid

  - **ts:** 2026-10-21T09:46:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** set_quote_status
  - **detail:** Active – rev.2: 5%, support 0h, NET30

  - **ts:** 2026-10-21T11:30:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** send_final_quote_manual
  - **detail:** after review

## WF-SM-012 · HelioMed – handoff net60 στο Finance

- **workflow id:** WF-SM-012
- **persona id:** PERS-SM-APETROU
- **Τίτλος:** HelioMed – handoff net60 στο Finance
- **start time:** 2026-10-14T13:20:00+03:00
- **end time:** 2026-10-19T10:30:00+03:00
- **Βήματα:**
  - **ts:** 2026-10-14T13:20:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** view_account_history
  - **detail:** 3 orders, avg 27 days, 0 overdue

  - **ts:** 2026-10-14T13:30:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** open_margin_sheet
  - **detail:** 4% → 27% (cost date 2026-10-09)

  - **ts:** 2026-10-14T13:40:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** complete_credit_checklist
  - **detail:** history ✔ exposure ✔ payment source: pending

  - **ts:** 2026-10-14T14:10:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Outlook
  - **action:** send_email
  - **detail:** E10 Finance review

  - **ts:** 2026-10-16T12:30:00+03:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** NexaCRM
  - **action:** attach_document
  - **detail:** funding confirmation letter

  - **ts:** 2026-10-16T15:45:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ERP
  - **action:** approve_payment_terms
  - **detail:** NET60 conditional, FIN-APR-2026-058, limit €50.000

  - **ts:** 2026-10-19T10:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** update_quote_terms
  - **detail:** 3 Finance conditions verbatim

  - **ts:** 2026-10-19T10:30:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** send_final_quote_manual
  - **detail:** QT-2026-0437
