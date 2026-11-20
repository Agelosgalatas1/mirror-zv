# Ροές εργασίας και εγκρίσεις 2026

Συνθετικά δεδομένα NexaTech Solutions.

## WF-FIN-001 · 3-way match & μερική έγκριση πληρωμής Vertex

- **workflow id:** WF-FIN-001
- **Τίτλος:** 3-way match & μερική έγκριση πληρωμής Vertex
- **Ποιος:** Μυρτώ Αντωνίου
- **related decision:** DEC-FIN-001
- **event time start:** 2026-01-19T15:00:00+02:00
- **event time end:** 2026-01-20T11:41:00+02:00
- **Βήματα:**
  - **ts:** 2026-01-19T15:00:00+02:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** NexaERP
  - **action:** open AP queue → run 3-way match INV-VC-2026-0112
  - **result:** MISMATCH amount: invoice 19150.00 / PO 18400.00 / GRN qty 120=120

  - **ts:** 2026-01-19T15:10:00+02:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** NexaERP
  - **action:** open PO-2026-0021 line detail
  - **result:** unit price PO 153.33 / invoice 159.58

  - **ts:** 2026-01-20T11:30:00+02:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ApprovalFlow
  - **action:** create partial payment PAY-2026-0034 amount=18400.00, hold=750.00 reason='price variance vs PO'
  - **result:** submitted

  - **ts:** 2026-01-20T11:40:00+02:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ApprovalFlow
  - **action:** approve PAY-2026-0034
  - **result:** approved (limit ≤ €25.000)

  - **ts:** 2026-01-20T11:52:00+02:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** Outlook
  - **action:** send supplier query re: price variance €750
  - **result:** sent

## WF-FIN-002 · Credit check νέου πελάτη BlueHarbor

- **workflow id:** WF-FIN-002
- **Τίτλος:** Credit check νέου πελάτη BlueHarbor
- **Ποιος:** Μυρτώ Αντωνίου
- **related decision:** DEC-FIN-002
- **event time start:** 2026-02-11T10:10:00+02:00
- **event time end:** 2026-02-11T16:05:00+02:00
- **Βήματα:**
  - **ts:** 2026-02-11T10:10:00+02:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** NexaERP
  - **action:** search customer 'BlueHarbor Logistics'
  - **result:** no customer record

  - **ts:** 2026-02-11T10:30:00+02:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** NexaCRM
  - **action:** open account BlueHarbor
  - **result:** prospect created 2026-02-10 by e.rapti; 0 invoices

  - **ts:** 2026-02-11T10:51:00+02:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** NexaERP
  - **action:** lookup last GRN cost for laptop SKU NB-14P
  - **result:** 579.20/unit; 50 units = 28960.00

  - **ts:** 2026-02-11T11:20:00+02:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** Excel
  - **action:** compute margin scenarios 0/8/10/15%
  - **result:** 27.6% / 21.3% / 19.6% / 14.8%

  - **ts:** 2026-02-11T15:50:00+02:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ApprovalFlow
  - **action:** set request FR-2026-004 status='info requested' fields=[financials_2y, trade_refs_2, payment_source]
  - **result:** updated

  - **ts:** 2026-02-11T16:05:00+02:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** Outlook
  - **action:** reply to a.petrou cc d.karra with recommendation
  - **result:** sent (E03)

## WF-FIN-003 · Καταχώρηση τελικών όρων BlueHarbor

- **workflow id:** WF-FIN-003
- **Τίτλος:** Καταχώρηση τελικών όρων BlueHarbor
- **Ποιος:** Νίκος Ζήσης
- **related decision:** DEC-FIN-003
- **event time start:** 2026-02-18T12:35:00+02:00
- **event time end:** 2026-02-26T17:10:00+02:00
- **Βήματα:**
  - **ts:** 2026-02-18T12:41:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** ApprovalFlow
  - **action:** approve discount DSC-2026-011 8% (SALE-DISC-v1 5–10%)
  - **result:** approved

  - **ts:** 2026-02-18T12:50:00+02:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ApprovalFlow
  - **action:** close FR-2026-004 with outcome='net30 default; net90 rejected by CEO'
  - **result:** closed

  - **ts:** 2026-02-26T16:20:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** mark opportunity won; signed order 36800.00
  - **result:** won (signature by human)

  - **ts:** 2026-02-26T17:05:00+02:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** NexaERP
  - **action:** create customer record BlueHarbor; terms=NET30; credit_limit=40000
  - **result:** created

  - **ts:** 2026-02-26T17:10:00+02:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** NexaERP
  - **action:** issue invoice BH-0001 36800.00 due 2026-03-28
  - **result:** issued

## WF-FIN-004 · Finance review Orion Retail net45

- **workflow id:** WF-FIN-004
- **Τίτλος:** Finance review Orion Retail net45
- **Ποιος:** Μυρτώ Αντωνίου
- **related decision:** DEC-FIN-004
- **event time start:** 2026-03-04T10:25:00+02:00
- **event time end:** 2026-03-06T10:30:00+02:00
- **Βήματα:**
  - **ts:** 2026-03-04T10:25:00+02:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** ApprovalFlow
  - **action:** submit FR-2026-007 terms=NET45 amount=72000.00
  - **result:** submitted

  - **ts:** 2026-03-05T17:15:00+02:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** NexaERP
  - **action:** export AR aging + 12m payment history customer=Orion Retail
  - **result:** 11 invoices; avg DSO 34; max 40; open 18200.00 current

  - **ts:** 2026-03-06T09:40:00+02:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** NexaERP
  - **action:** verify margin quote Q-2026-0318
  - **result:** 24.3%

  - **ts:** 2026-03-06T09:45:00+02:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ApprovalFlow
  - **action:** check linked discount approval DSC-2026-019 9%
  - **result:** approved by a.petrou

  - **ts:** 2026-03-06T10:18:00+02:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ApprovalFlow
  - **action:** approve FR-2026-007 conditions=[credit_limit 95000, revert NET30 if >15d late]
  - **result:** approved

  - **ts:** 2026-03-06T10:30:00+02:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** NexaERP
  - **action:** update customer Orion credit_limit=95000; order terms NET45
  - **result:** updated

## WF-FIN-005 · Q1 close: bank reconciliation & duplicate detection

- **workflow id:** WF-FIN-005
- **Τίτλος:** Q1 close: bank reconciliation & duplicate detection
- **Ποιος:** Νίκος Ζήσης
- **related decision:** DEC-FIN-005
- **event time start:** 2026-03-30T09:00:00+03:00
- **event time end:** 2026-03-31T10:30:00+03:00
- **Βήματα:**
  - **ts:** 2026-03-30T09:00:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** Bank portal
  - **action:** download statements March (main, POS)
  - **result:** 2 files

  - **ts:** 2026-03-30T11:30:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** NexaERP
  - **action:** run bank reconciliation main account
  - **result:** diff 0.00 after 3 timing items

  - **ts:** 2026-03-30T12:10:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** NexaERP
  - **action:** run bank reconciliation POS account
  - **result:** diff 212.40 (bank fees not posted)

  - **ts:** 2026-03-30T14:20:00+03:00
  - **Ποιος:** NexaERP (auto)
  - **system:** NexaERP
  - **action:** duplicate check AP queue
  - **result:** BLOCK LC-2026-0341 x2 (same no., amount 4860.00, PO)

  - **ts:** 2026-03-30T14:35:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ApprovalFlow
  - **action:** reject duplicate entry (source=PDF) reason='διπλοεγγραφή, ίδιο τιμολόγιο από 2 κανάλια'
  - **result:** rejected

  - **ts:** 2026-03-30T18:40:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** NexaERP
  - **action:** review & sign off reconciliation; post bank fees 212.40
  - **result:** posted

  - **ts:** 2026-03-31T08:10:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** NexaERP
  - **action:** run AR aging as of 2026-03-31
  - **result:** open 238400.00; >30d 9150.00 (2 customers)

## WF-FIN-006 · Exposure & concentration model AegeanWorks

- **workflow id:** WF-FIN-006
- **Τίτλος:** Exposure & concentration model AegeanWorks
- **Ποιος:** Μυρτώ Αντωνίου
- **related decision:** DEC-FIN-006
- **event time start:** 2026-04-14T12:00:00+03:00
- **event time end:** 2026-04-15T18:45:00+03:00
- **Βήματα:**
  - **ts:** 2026-04-14T12:05:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** Teams
  - **action:** request segment revenue 2025 from n.zisis
  - **result:** sent

  - **ts:** 2026-04-14T13:20:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** NexaERP
  - **action:** report revenue by customer segment='marine/metal' FY2025
  - **result:** AegeanWorks 23600.00; other 3 customers 61000.00

  - **ts:** 2026-04-15T10:00:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** Document repository
  - **action:** open draft contract AegeanWorks_exclusivity_draft_v1
  - **result:** no minimum volume clause; no penalty clause

  - **ts:** 2026-04-15T15:30:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** Excel
  - **action:** build AegeanWorks_exposure_v2.xlsx (concentration, at-risk revenue scenarios)
  - **result:** concentration ~9%; at-risk up to ~60000/yr (estimate)

  - **ts:** 2026-04-15T18:45:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** Outlook
  - **action:** send assessment to d.karra cc a.petrou
  - **result:** sent (E05)

## WF-FIN-007 · Budget exception BX-2026-03

- **workflow id:** WF-FIN-007
- **Τίτλος:** Budget exception BX-2026-03
- **Ποιος:** Μυρτώ Αντωνίου
- **related decision:** DEC-FIN-007
- **event time start:** 2026-05-13T10:30:00+03:00
- **event time end:** 2026-05-14T10:05:00+03:00
- **Βήματα:**
  - **ts:** 2026-05-13T10:30:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** ApprovalFlow
  - **action:** submit BX-2026-03 +3200.00 with line items
  - **result:** submitted

  - **ts:** 2026-05-13T16:40:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** NexaERP
  - **action:** budget vs actual Q2 dept=Sales/Marketing
  - **result:** available 4100.00

  - **ts:** 2026-05-13T16:55:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** NexaERP
  - **action:** inventory lookup promo materials
  - **result:** 140 units (count 2026-04-30)

  - **ts:** 2026-05-13T17:05:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** NexaCRM
  - **action:** search leads tag 'EXPO-THES-2025'
  - **result:** tag not found

  - **ts:** 2026-05-14T09:45:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ApprovalFlow
  - **action:** partial approve BX-2026-03 amount=2400.00 cap=10400.00 conditions=[CRM tag EXPO-THES-2026 by 2026-06-05]
  - **result:** partially approved

  - **ts:** 2026-05-14T10:05:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** NexaERP
  - **action:** set PO cap event budget 10400.00
  - **result:** updated

## WF-FIN-008 · Pineworks staged payment schedule

- **workflow id:** WF-FIN-008
- **Τίτλος:** Pineworks staged payment schedule
- **Ποιος:** Μυρτώ Αντωνίου
- **related decision:** DEC-FIN-008
- **event time start:** 2026-06-08T14:00:00+03:00
- **event time end:** 2026-06-18T15:00:00+03:00
- **Βήματα:**
  - **ts:** 2026-06-08T14:00:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** NexaERP
  - **action:** payment history customer=Pineworks
  - **result:** 2 invoices 14300.00; paid day 39, 43 on NET30

  - **ts:** 2026-06-08T15:10:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** Excel
  - **action:** model exposure: single delivery NET90 vs 3 deliveries NET60 with advance 25%
  - **result:** peak 110000 vs ~55000

  - **ts:** 2026-06-09T16:20:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** Excel
  - **action:** rerun model with advance 30% (CEO decision)
  - **result:** peak ~51333; tranche 25666.67

  - **ts:** 2026-06-09T18:55:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ApprovalFlow
  - **action:** approve FR-2026-019 NET60 per invoice, conditions=[advance 30%, 3 tranches, next tranche only if prior invoice ≤15d late]; NET90 marked 'rejected by CEO'
  - **result:** approved with conditions

  - **ts:** 2026-06-09T19:10:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** Outlook
  - **action:** send recommendation to d.karra, a.petrou
  - **result:** sent (E07)

  - **ts:** 2026-06-18T15:00:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** NexaERP
  - **action:** create billing schedule Pineworks: advance 33000.00 + 3x25666.67 NET60; delivery hold rule
  - **result:** created

## WF-FIN-009 · Kalyx overdue check για νέα παραγγελία

- **workflow id:** WF-FIN-009
- **Τίτλος:** Kalyx overdue check για νέα παραγγελία
- **Ποιος:** Μυρτώ Αντωνίου
- **related decision:** DEC-FIN-009
- **event time start:** 2026-07-08T12:05:00+03:00
- **event time end:** 2026-07-16T10:00:00+03:00
- **Βήματα:**
  - **ts:** 2026-07-08T12:05:00+03:00
  - **Ποιος:** NexaERP (auto)
  - **system:** NexaERP
  - **action:** sales order SO-2026-0412 credit check
  - **result:** WARN customer has overdue KX-0612 6200.00 (12d)

  - **ts:** 2026-07-08T12:20:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** NexaERP
  - **action:** payment history customer=Kalyx Interiors
  - **result:** 6 invoices; 5 on time; 1 overdue

  - **ts:** 2026-07-08T12:40:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** NexaERP
  - **action:** set SO-2026-0412 terms='50% prepayment 4500.00, balance NET30'; release_on=prepayment_received
  - **result:** updated

  - **ts:** 2026-07-10T11:15:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** Bank portal
  - **action:** match incoming 4500.00 Kalyx
  - **result:** matched → SO released

  - **ts:** 2026-07-16T10:00:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** Bank portal
  - **action:** match incoming 6200.00 Kalyx → KX-0612
  - **result:** invoice closed

## WF-FIN-010 · Rollout FIN-CREDIT-v2 & exception review Kestrel

- **workflow id:** WF-FIN-010
- **Τίτλος:** Rollout FIN-CREDIT-v2 & exception review Kestrel
- **Ποιος:** Μυρτώ Αντωνίου
- **related decision:** DEC-FIN-010
- **event time start:** 2026-08-31T09:00:00+03:00
- **event time end:** 2026-10-02T09:15:00+03:00
- **Βήματα:**
  - **ts:** 2026-08-31T09:00:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** NexaERP
  - **action:** run AR aging filter >30d
  - **result:** 1 customer: Kestrel Print KP-0627 12400.00 (35d)

  - **ts:** 2026-08-31T09:25:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** NexaERP
  - **action:** set customer flag Kestrel='no new credit — exception review' effective 2026-09-01
  - **result:** flag set

  - **ts:** 2026-09-01T08:30:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ApprovalFlow
  - **action:** enable mandatory fields [payment_history, exposure, payment_source] for credit requests
  - **result:** config updated (FIN-CREDIT-v2)

  - **ts:** 2026-09-03T10:00:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ApprovalFlow
  - **action:** open exception review EXR-2026-001 Kestrel; payment plan 6200.00 by 2026-09-15, 6200.00 by 2026-09-30; new orders prepaid only
  - **result:** opened

  - **ts:** 2026-09-03T10:05:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** Outlook
  - **action:** send payment plan proposal to Kestrel (accounts.kestrel@example.com)
  - **result:** sent

  - **ts:** 2026-09-14T16:15:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** Bank portal
  - **action:** match incoming 6200.00 Kestrel
  - **result:** installment 1 received

  - **ts:** 2026-10-01T15:00:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** Bank portal
  - **action:** match incoming 6200.00 Kestrel
  - **result:** installment 2 received (1 day after plan)

  - **ts:** 2026-10-02T09:12:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ApprovalFlow
  - **action:** close EXR-2026-001; remove flag; add history note
  - **result:** closed

## WF-FIN-011 · Margin verification Northbridge Hotels

- **workflow id:** WF-FIN-011
- **Τίτλος:** Margin verification Northbridge Hotels
- **Ποιος:** Μυρτώ Αντωνίου
- **related decision:** DEC-FIN-011
- **event time start:** 2026-09-14T15:30:00+03:00
- **event time end:** 2026-09-15T12:25:00+03:00
- **Βήματα:**
  - **ts:** 2026-09-14T15:30:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** NexaCRM
  - **action:** open quote draft Q-2026-0877 Northbridge
  - **result:** net 28000.00; discount 11%; margin field 25.4%; support 6h

  - **ts:** 2026-09-14T15:58:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** NexaERP
  - **action:** lookup GRN cost Aug-2026 for POS-T10, TAB-11 + internal support cost
  - **result:** total cost 20990.00

  - **ts:** 2026-09-14T16:02:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** Excel
  - **action:** compute verified margin
  - **result:** 25.0%

  - **ts:** 2026-09-14T16:08:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** NexaERP
  - **action:** AR check customer=Northbridge Hotels
  - **result:** 1 invoice 3100.00 paid day 27; overdue 0 → NET30 default (v2)

  - **ts:** 2026-09-14T16:12:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** Outlook
  - **action:** send verification to e.rapti, a.petrou
  - **result:** sent (E09)

  - **ts:** 2026-09-15T12:20:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** ApprovalFlow
  - **action:** approve DSC-2026-071 11% margin=25.0% support=4h (SALE-DISC-v2)
  - **result:** approved

## WF-FIN-012 · Finance review HelioMed net60 (v2)

- **workflow id:** WF-FIN-012
- **Τίτλος:** Finance review HelioMed net60 (v2)
- **Ποιος:** Μυρτώ Αντωνίου
- **related decision:** DEC-FIN-012
- **event time start:** 2026-10-12T15:20:00+03:00
- **event time end:** 2026-10-14T11:05:00+03:00
- **Βήματα:**
  - **ts:** 2026-10-12T15:20:00+03:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** ApprovalFlow
  - **action:** submit FR-2026-031 NET60 46000.00 fields=[history, exposure, payment_source]
  - **result:** submitted (complete)

  - **ts:** 2026-10-12T15:40:00+03:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** ApprovalFlow
  - **action:** attach CFO letter dated 2026-10-09
  - **result:** attached

  - **ts:** 2026-10-13T09:40:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** NexaERP
  - **action:** payment history + open items customer=HelioMed Labs
  - **result:** 3 invoices 17800.00; days 24/27/31; open 0

  - **ts:** 2026-10-13T16:00:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** NexaERP
  - **action:** AR aging >30d check customer=HelioMed
  - **result:** none → no exception review

  - **ts:** 2026-10-14T10:35:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ApprovalFlow
  - **action:** approve FR-2026-031 conditions=[credit_limit 55000, invoice on delivery acceptance, revert NET30 if >15d late, authorised signatory]
  - **result:** approved with conditions

  - **ts:** 2026-10-14T11:05:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** NexaERP
  - **action:** update HelioMed credit_limit=55000; add day-45 alert rule
  - **result:** updated
