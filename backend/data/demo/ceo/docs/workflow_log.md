# Ροές εργασίας και εγκρίσεις 2026

Συνθετικά δεδομένα NexaTech Solutions.

## WF01 · BlueHarbor — κλιμάκωση έκπτωσης 15% και net90

- **workflow id:** WF01
- **Τίτλος:** BlueHarbor — κλιμάκωση έκπτωσης 15% και net90
- **Υπεύθυνος:** Αλέξανδρος Πέτρου
- **Πολιτικές:**
  - SALE-DISC-v1
  - FIN-CREDIT-v1
- **Βήματα:**
  - **timestamp:** 2026-02-11T16:50:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** open_opportunity
  - **object id:** OPP-2026-0211
  - **result:** Άνοιγμα ευκαιρίας BlueHarbor, 50 laptops, €40.000

  - **timestamp:** 2026-02-11T17:05:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** review_margin
  - **object id:** OPP-2026-0211
  - **result:** Margin 30% λίστα / 23,9% στο 8% / 17,6% στο 15%

  - **timestamp:** 2026-02-11T17:20:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** ApprovalHub
  - **action:** submit_approval_request
  - **object id:** APR-2026-0042
  - **result:** Αίτημα 15% + net90 → routing σε CEO (>10%, net90)

  - **timestamp:** 2026-02-11T17:35:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Outlook
  - **action:** send_email
  - **object id:** E02
  - **result:** Ενημέρωση CEO, cc Finance

  - **timestamp:** 2026-02-12T09:05:00+02:00
  - **Ποιος:** Δανάη Καρρά
  - **system:** ApprovalHub
  - **action:** reject_request
  - **object id:** APR-2026-0042
  - **result:** Απορρίφθηκε: 15% και net90

  - **timestamp:** 2026-02-12T09:10:00+02:00
  - **Ποιος:** Δανάη Καρρά
  - **system:** Outlook
  - **action:** send_email
  - **object id:** E03
  - **result:** Αιτιολόγηση απόρριψης, επιστροφή στα όρια managers

## WF02 · BlueHarbor — τελικοί όροι 8% και net45

- **workflow id:** WF02
- **Τίτλος:** BlueHarbor — τελικοί όροι 8% και net45
- **Υπεύθυνος:** Αλέξανδρος Πέτρου
- **Πολιτικές:**
  - SALE-DISC-v1
  - FIN-CREDIT-v1
- **Βήματα:**
  - **timestamp:** 2026-02-13T10:00:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** ApprovalHub
  - **action:** approve_discount
  - **object id:** APR-2026-0045
  - **result:** Έγκριση 8% από Sales Manager

  - **timestamp:** 2026-02-16T14:00:00+02:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ERP
  - **action:** run_credit_check
  - **object id:** CR-2026-0019
  - **result:** Credit check BlueHarbor: καθαρό

  - **timestamp:** 2026-02-17T11:30:00+02:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ERP
  - **action:** approve_credit_terms
  - **object id:** CR-2026-0019
  - **result:** Έγκριση net45 (Finance review)

  - **timestamp:** 2026-02-17T15:00:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** draft_proposal
  - **object id:** PRP-2026-0031
  - **result:** Draft προσφοράς 8% / net45

  - **timestamp:** 2026-02-18T09:30:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Outlook
  - **action:** send_proposal_human
  - **object id:** PRP-2026-0031
  - **result:** Αποστολή προσφοράς από άνθρωπο

  - **timestamp:** 2026-02-26T15:00:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** DocDrive
  - **action:** upload_signed_contract
  - **object id:** CTR-2026-0012
  - **result:** Υπογεγραμμένη σύμβαση

## WF03 · Orion Retail — έγκριση έκπτωσης 9%

- **workflow id:** WF03
- **Τίτλος:** Orion Retail — έγκριση έκπτωσης 9%
- **Υπεύθυνος:** Αλέξανδρος Πέτρου
- **Πολιτικές:**
  - SALE-DISC-v1
- **Βήματα:**
  - **timestamp:** 2026-03-10T14:10:00+02:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** NexaCRM
  - **action:** open_opportunity
  - **object id:** OPP-2026-0309
  - **result:** Ευκαιρία Orion Retail, €72k

  - **timestamp:** 2026-03-10T14:40:00+02:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** NexaCRM
  - **action:** review_margin
  - **object id:** OPP-2026-0309
  - **result:** Margin στο 9%: 24%

  - **timestamp:** 2026-03-10T15:00:00+02:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** ApprovalHub
  - **action:** submit_approval_request
  - **object id:** APR-2026-0071
  - **result:** 9% → routing σε Sales Manager (5–10%)

  - **timestamp:** 2026-03-11T11:20:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** ApprovalHub
  - **action:** approve_discount
  - **object id:** APR-2026-0071
  - **result:** Εγκρίθηκε 9%

  - **timestamp:** 2026-03-11T11:45:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** draft_proposal
  - **object id:** PRP-2026-0048
  - **result:** Draft προσφοράς, εκκρεμεί πιστωτικός όρος

## WF04 · Orion Retail — net45

- **workflow id:** WF04
- **Τίτλος:** Orion Retail — net45
- **Υπεύθυνος:** Μυρτώ Αντωνίου
- **Πολιτικές:**
  - FIN-CREDIT-v1
- **Βήματα:**
  - **timestamp:** 2026-03-12T09:30:00+02:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ERP
  - **action:** open_credit_review
  - **object id:** CR-2026-0027
  - **result:** Αίτημα net45 Orion Retail

  - **timestamp:** 2026-03-12T12:00:00+02:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ERP
  - **action:** attach_payment_history
  - **object id:** CR-2026-0027
  - **result:** Ιστορικό πληρωμών επισυνάφθηκε

  - **timestamp:** 2026-03-13T16:15:00+02:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ERP
  - **action:** approve_credit_terms
  - **object id:** CR-2026-0027
  - **result:** Εγκρίθηκε net45· πεδίο αιτιολόγησης κενό

  - **timestamp:** 2026-03-13T17:00:00+02:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Outlook
  - **action:** send_proposal_human
  - **object id:** PRP-2026-0048
  - **result:** Αποστολή προσφοράς 9% / net45 από άνθρωπο

## WF05 · AegeanWorks — αντιπρόταση pilot 6 μηνών

- **workflow id:** WF05
- **Τίτλος:** AegeanWorks — αντιπρόταση pilot 6 μηνών
- **Υπεύθυνος:** Αλέξανδρος Πέτρου
- **Πολιτικές:**
  - SALE-DISC-v1
  - FIN-CREDIT-v1
- **Βήματα:**
  - **timestamp:** 2026-04-22T17:30:00+03:00
  - **Ποιος:** Δανάη Καρρά
  - **system:** DocDrive
  - **action:** publish_document
  - **object id:** DOC01
  - **result:** Decision memo AegeanWorks

  - **timestamp:** 2026-04-23T08:45:00+03:00
  - **Ποιος:** Δανάη Καρρά
  - **system:** Outlook
  - **action:** send_email
  - **object id:** E05
  - **result:** Απόφαση προς Sales, cc Finance

  - **timestamp:** 2026-04-23T11:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** log_call
  - **object id:** OPP-2026-0417
  - **result:** Τηλεφωνική ενημέρωση AegeanWorks

  - **timestamp:** 2026-04-23T16:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** ApprovalHub
  - **action:** approve_discount
  - **object id:** APR-2026-0118
  - **result:** Έγκριση 7% (Sales Manager)

  - **timestamp:** 2026-04-24T12:40:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** draft_proposal
  - **object id:** PRP-2026-0077
  - **result:** Draft email/προσφοράς pilot

  - **timestamp:** 2026-04-24T13:25:00+03:00
  - **Ποιος:** Δανάη Καρρά
  - **system:** NexaCRM
  - **action:** review_edit_draft
  - **object id:** PRP-2026-0077
  - **result:** Αφαίρεση αναφοράς σε μελλοντική αποκλειστικότητα

  - **timestamp:** 2026-04-24T15:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Outlook
  - **action:** send_proposal_human
  - **object id:** PRP-2026-0077
  - **result:** Αποστολή από άνθρωπο

  - **timestamp:** 2026-04-28T10:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** update_stage
  - **object id:** OPP-2026-0417
  - **result:** Closed-won (pilot) · stop-loss KPIs ενεργά

## WF06 · Kyma Couriers — pilot dual-sourcing

- **workflow id:** WF06
- **Τίτλος:** Kyma Couriers — pilot dual-sourcing
- **Υπεύθυνος:** Μυρτώ Αντωνίου
- **Βήματα:**
  - **timestamp:** 2026-05-15T17:40:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** DocDrive
  - **action:** upload_report
  - **object id:** RPT-OTD-2026-04
  - **result:** On-time Απριλίου ανά περιοχή

  - **timestamp:** 2026-05-20T09:00:00+03:00
  - **Ποιος:** Δανάη Καρρά
  - **system:** Outlook
  - **action:** send_email
  - **object id:** E06
  - **result:** Απόφαση pilot 3 μηνών

  - **timestamp:** 2026-05-22T10:00:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ERP
  - **action:** create_vendor
  - **object id:** VND-KYMA
  - **result:** Καταχώριση Kyma Couriers

  - **timestamp:** 2026-05-27T12:00:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** DocDrive
  - **action:** upload_contract_draft
  - **object id:** CTR-2026-0044
  - **result:** Σύμβαση με ρήτρα εξόδου 30 ημερών, cap €6.000

  - **timestamp:** 2026-05-29T16:00:00+03:00
  - **Ποιος:** Δανάη Καρρά
  - **system:** DocDrive
  - **action:** sign_contract_human
  - **object id:** CTR-2026-0044
  - **result:** Υπογραφή από CEO

  - **timestamp:** 2026-06-01T08:00:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ERP
  - **action:** set_routing_rule
  - **object id:** RTE-ISLANDS
  - **result:** Έως 30% όγκου (νησιά) → Kyma

## WF07 · Pineworks — πιστωτική δομή

- **workflow id:** WF07
- **Τίτλος:** Pineworks — πιστωτική δομή
- **Υπεύθυνος:** Μυρτώ Αντωνίου
- **Πολιτικές:**
  - FIN-CREDIT-v1
- **Βήματα:**
  - **timestamp:** 2026-06-15T11:30:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ERP
  - **action:** open_credit_review
  - **object id:** CR-2026-0081
  - **result:** Αίτημα net90, €110k

  - **timestamp:** 2026-06-15T11:50:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ERP
  - **action:** attach_payment_history
  - **object id:** CR-2026-0081
  - **result:** Μέση πληρωμή 38 ημέρες σε net30, 24 μήνες

  - **timestamp:** 2026-06-16T15:05:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** DocDrive
  - **action:** upload_model
  - **object id:** MDL-PINE-01
  - **result:** Exposure model: 30% προκαταβολή, 3 παραδόσεις, cap €40k

  - **timestamp:** 2026-06-16T18:10:00+03:00
  - **Ποιος:** Δανάη Καρρά
  - **system:** Outlook
  - **action:** send_email
  - **object id:** E07
  - **result:** Απόρριψη net90, πρόταση δομής

  - **timestamp:** 2026-06-17T09:00:00+03:00
  - **Ποιος:** Δανάη Καρρά
  - **system:** ApprovalHub
  - **action:** reject_request
  - **object id:** APR-2026-0163
  - **result:** net90 απορρίφθηκε (CEO)

  - **timestamp:** 2026-06-18T12:00:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ERP
  - **action:** approve_credit_terms
  - **object id:** CR-2026-0081
  - **result:** Εγκρίθηκε net60 με προκαταβολή 30% και cap €40k

  - **timestamp:** 2026-06-19T10:30:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Outlook
  - **action:** send_proposal_human
  - **object id:** PRP-2026-0102
  - **result:** Αποστολή προσφοράς από άνθρωπο

## WF08 · Πολιτικές v2 — έγκριση και ανακοίνωση

- **workflow id:** WF08
- **Τίτλος:** Πολιτικές v2 — έγκριση και ανακοίνωση
- **Υπεύθυνος:** Δανάη Καρρά
- **Πολιτικές:**
  - SALE-DISC-v2
  - FIN-CREDIT-v2
- **Βήματα:**
  - **timestamp:** 2026-07-16T12:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** DocDrive
  - **action:** upload_report
  - **object id:** RPT-APR-Q2
  - **result:** Ανάλυση εγκρίσεων Φεβ–Ιουν

  - **timestamp:** 2026-07-21T10:20:00+03:00
  - **Ποιος:** Δανάη Καρρά
  - **system:** Outlook
  - **action:** send_email
  - **object id:** E08
  - **result:** Αποδοχή 6% με margin 23%

  - **timestamp:** 2026-07-27T10:00:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** DocDrive
  - **action:** upload_document
  - **object id:** DOC02-draft
  - **result:** Τελικό draft πολιτικών

  - **timestamp:** 2026-07-28T14:30:00+03:00
  - **Ποιος:** Δανάη Καρρά
  - **system:** ApprovalHub
  - **action:** approve_policy
  - **object id:** APR-POL-2026-07
  - **result:** Έγκριση SALE-DISC-v2 & FIN-CREDIT-v2

  - **timestamp:** 2026-07-28T14:45:00+03:00
  - **Ποιος:** Δανάη Καρρά
  - **system:** DocDrive
  - **action:** publish_document
  - **object id:** DOC02
  - **result:** Δημοσίευση τελικού κειμένου

  - **timestamp:** 2026-07-28T15:00:00+03:00
  - **Ποιος:** Δανάη Καρρά
  - **system:** Outlook
  - **action:** send_email
  - **object id:** E09
  - **result:** Ανακοίνωση προς όλους

## WF09 · Πολιτικές v2 — παραμετροποίηση ApprovalHub

- **workflow id:** WF09
- **Τίτλος:** Πολιτικές v2 — παραμετροποίηση ApprovalHub
- **Υπεύθυνος:** Νίκος Ζήσης
- **Πολιτικές:**
  - SALE-DISC-v2
  - FIN-CREDIT-v2
- **Βήματα:**
  - **timestamp:** 2026-08-14T17:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** ApprovalHub
  - **action:** configure_rule
  - **object id:** RULE-SALE-DISC-v2
  - **result:** Ενεργοποίηση από 15/08 00:00

  - **timestamp:** 2026-08-14T17:10:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** ApprovalHub
  - **action:** deactivate_rule
  - **object id:** RULE-SALE-DISC-v1
  - **result:** Λήξη 14/08 23:59

  - **timestamp:** 2026-08-31T16:00:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ApprovalHub
  - **action:** configure_rule
  - **object id:** RULE-FIN-CREDIT-v2
  - **result:** Ενεργοποίηση από 01/09 00:00

  - **timestamp:** 2026-08-31T16:05:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ApprovalHub
  - **action:** deactivate_rule
  - **object id:** RULE-FIN-CREDIT-v1
  - **result:** Λήξη 31/08 23:59

  - **timestamp:** 2026-09-01T11:00:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ApprovalHub
  - **action:** run_test_cases
  - **object id:** TEST-FC-v2
  - **result:** 5/5 σωστό routing

## WF10 · Northbridge Hotels — 11% και support 4h

- **workflow id:** WF10
- **Τίτλος:** Northbridge Hotels — 11% και support 4h
- **Υπεύθυνος:** Αλέξανδρος Πέτρου
- **Πολιτικές:**
  - SALE-DISC-v2
- **Βήματα:**
  - **timestamp:** 2026-09-16T10:00:00+03:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** NexaCRM
  - **action:** open_opportunity
  - **object id:** OPP-2026-0916
  - **result:** Ευκαιρία Northbridge Hotels, €28k

  - **timestamp:** 2026-09-17T11:00:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ERP
  - **action:** verify_margin
  - **object id:** OPP-2026-0916
  - **result:** Margin στο 11%: 25% επαληθευμένο

  - **timestamp:** 2026-09-17T12:00:00+03:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** ApprovalHub
  - **action:** submit_approval_request
  - **object id:** APR-2026-0288
  - **result:** 11% → routing σε Sales Manager (>6–12%)

  - **timestamp:** 2026-09-18T09:40:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** ApprovalHub
  - **action:** approve_discount
  - **object id:** APR-2026-0288
  - **result:** Εγκρίθηκε 11%· support 4h (draft)

  - **timestamp:** 2026-09-18T11:00:00+03:00
  - **Ποιος:** Ελένη Ράπτη
  - **system:** NexaCRM
  - **action:** draft_proposal
  - **object id:** PRP-2026-0190
  - **result:** Draft προσφοράς

  - **timestamp:** 2026-09-18T15:30:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Outlook
  - **action:** send_proposal_human
  - **object id:** PRP-2026-0190
  - **result:** Αποστολή από άνθρωπο

## WF11 · HelioMed Labs — net60 υπό όρους

- **workflow id:** WF11
- **Τίτλος:** HelioMed Labs — net60 υπό όρους
- **Υπεύθυνος:** Μυρτώ Αντωνίου
- **Πολιτικές:**
  - FIN-CREDIT-v2
- **Βήματα:**
  - **timestamp:** 2026-10-12T10:00:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ERP
  - **action:** open_credit_review
  - **object id:** CR-2026-0142
  - **result:** Αίτημα net60, €46k

  - **timestamp:** 2026-10-12T11:30:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ERP
  - **action:** check_overdue
  - **object id:** CR-2026-0142
  - **result:** Μηδέν ληξιπρόθεσμα, 14 μήνες ιστορικό

  - **timestamp:** 2026-10-12T14:00:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ERP
  - **action:** calc_exposure
  - **object id:** CR-2026-0142
  - **result:** Έκθεση μετά την παραγγελία: €46k

  - **timestamp:** 2026-10-13T10:00:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ERP
  - **action:** verify_payment_source
  - **object id:** CR-2026-0142
  - **result:** Πηγή πληρωμής επιβεβαιωμένη

  - **timestamp:** 2026-10-14T09:30:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ERP
  - **action:** approve_credit_terms
  - **object id:** CR-2026-0142
  - **result:** net60, cap €50k, επιστροφή σε net30 αν >15 ημέρες ληξιπρόθεσμο

  - **timestamp:** 2026-10-14T12:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** Outlook
  - **action:** send_proposal_human
  - **object id:** PRP-2026-0221
  - **result:** Αποστολή όρων από άνθρωπο

## WF12 · Q4 — προτεραιότητες και αναθέσεις

- **workflow id:** WF12
- **Τίτλος:** Q4 — προτεραιότητες και αναθέσεις
- **Υπεύθυνος:** Δανάη Καρρά
- **Πολιτικές:**
  - SALE-DISC-v2
  - FIN-CREDIT-v2
- **Βήματα:**
  - **timestamp:** 2026-10-06T10:00:00+03:00
  - **Ποιος:** Δανάη Καρρά
  - **system:** Teams
  - **action:** hold_meeting
  - **object id:** M02
  - **result:** Leadership Q4

  - **timestamp:** 2026-10-07T08:00:00+03:00
  - **Ποιος:** Δανάη Καρρά
  - **system:** DocDrive
  - **action:** publish_document
  - **object id:** DOC03
  - **result:** Q4 memo

  - **timestamp:** 2026-10-07T08:30:00+03:00
  - **Ποιος:** Δανάη Καρρά
  - **system:** Outlook
  - **action:** send_email
  - **object id:** E10
  - **result:** Προτεραιότητες προς managers

  - **timestamp:** 2026-10-08T09:00:00+03:00
  - **Ποιος:** Μυρτώ Αντωνίου
  - **system:** ERP
  - **action:** create_purchase_request
  - **object id:** PR-2026-0311
  - **result:** Dashboard εγκρίσεων/SLA, €7.000

  - **timestamp:** 2026-10-09T10:00:00+03:00
  - **Ποιος:** Αλέξανδρος Πέτρου
  - **system:** NexaCRM
  - **action:** reassign_accounts
  - **object id:** ACC-TOP20
  - **result:** Owner renewals top-20 → Ελένη Ράπτη

  - **timestamp:** 2026-10-12T09:00:00+03:00
  - **Ποιος:** Νίκος Ζήσης
  - **system:** ERP
  - **action:** schedule_report
  - **object id:** RPT-OVERDUE-WEEKLY
  - **result:** Εβδομαδιαίο overdue report
