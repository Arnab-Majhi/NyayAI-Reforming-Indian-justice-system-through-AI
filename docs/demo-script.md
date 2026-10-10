# NyayaAI: 5–7 minute demonstration

Run the backend and frontend using the README. Open http://localhost:3000. Use only synthetic information. Reset beforehand if you want the original 36-case counts.

## 0:00–0:45 — Introduce the platform

- Show the landing page and its five modules.
- Explain: independent prototype, not government-endorsed; no real filings, hearings or verdicts.
- Enter the citizen demo using **Citizen 1**. Explain that these are 12 authorized fictional cases, not the full registry.
- Dashboard counts and charts come from stored records, not hardcoded visualizations.

## 0:45–2:00 — Filing Assistant

1. Select `DEMO/2026/0001` in Filing Assistant.
2. Download the complete and defective sample PDFs using the page links.
3. Upload the defective PDF. Classify it as **Statement**, then inspect extracted text.
4. Keep reviewed applicant `Demo Citizen 1`, respondent `Demo Supplier`; run readiness checks.
5. Show missing supporting record, mismatched names, and invalid calendar date. Distinguish warnings from detected defects and “unable to verify”.
6. Upload the complete PDF twice; exclude the defective file and classify the new files as **Statement** and **Supporting record**. This duplicated-file exercise is deliberately synthetic.
7. Confirm the incident date displayed in the complete PDF, rerun checks, and download/print the checklist.
8. Explain that fees, jurisdiction, limitation and official forms still require official verification. There is no “accepted by court” claim.

## 2:00–3:00 — Research and citizen assistance

- Ask Legal Research: **How can I find case status without a CNR number?**
- Open the retrieved eCourts passage and official URL. Show unknown publication/effective dates rather than inventing them.
- Generate a downloadable research brief.
- Ask Citizen Legal Assistant: **Where can I find legal aid?**
- Expand source passages and create a general preparation checklist.
- Ask an unsupported question such as **quantum pineapple zeppelin** to demonstrate insufficient evidence.
- Explain that this demo shares one retrieval engine and uses retrieved excerpts, not a paid model. Conversation history is stored per user, but each question is retrieved independently.

## 3:00–4:30 — Court staff operations

- Sign out; select **Court staff · Registry Officer 1**.
- Show the 36-case registry; filter by status/category and search by reference.
- Open `DEMO/2026/0001`. Inspect timeline, shared documents and risk indicators.
- Create a task, edit its deadline/assignee, mark it complete.
- Add a simulated procedural note.
- Open Scheduling; suggest slots, inspect conflicts and confirm a slot in the confirmation dialog.
- Reiterate: no actual court hearing was booked.

## 4:30–5:30 — Administrative analytics

- Open Predictive Analysis. Show risk bands, stages and filing history charts.
- Show the model card: 900 synthetic snapshots, first 600 training, 30-day embargo, final 270 test.
- Compare logistic regression with prior-probability baseline, including Brier score.
- Explain that the target is a **procedural milestone not completed within 30 days**, never guilt or verdict.
- Metrics demonstrate computation on a synthetic process; they are not evidence of real judicial forecasting accuracy.

## 5:30–6:45 — Non-binding judicial issue analysis

- Open Decision Support. The first three cases cover a desk-delivery dispute, rental deposit disagreement and service-invoice dispute.
- Select a case, edit the opposing argument and questions, inspect any uploaded material.
- Confirm reviewed inputs, then generate the report.
- Show assertion classifications and input/document references; none silently become verified facts.
- Compare claimant/opponent presentations, text-pattern dispute flags and missing information.
- Show the abstention: the small guidance corpus cannot establish substantive legal elements or responsible outcome scenarios.
- Download the non-binding report and show it associated with the case.

## Closing

Explain the roadmap honestly: expand verified statutory/judgment corpus, provenance approval, semantic embeddings, independent legal review, production identity provider, database-scale authorization queries, transactional multi-worker scheduling and real-world validation. This prototype is a working demo workflow, not a deployable judicial decision-maker.