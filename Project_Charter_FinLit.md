# Project Charter: Multimodal Financial Literacy Chatbot [cite: 1]

## Overview
* **Project Name:** FinLit Multi-Phase [cite: 2]
* **Project Length:** January - May 2026 [cite: 3]
* **Team Members:** [cite: 4]
    * Gabriel Ponsot [cite: 6]
    * Shubh Vaishnav [cite: 8]
    * Daniel Kang [cite: 9]

## Project Goal
To build a multimodal financial literacy chatbot that guides early-career users through critical financial onboarding tasks—such as budgeting, 401(k) basics, borrowing fundamentals, and credit management—using a structured, multi-phase architecture. [cite: 10]

---

## 1. Project Objectives & Scope
The agent is designed to provide orientation, not optimization [cite: 12]. It focuses on five educational pillars for users in their early 20s to early 30s: [cite: 12]

* **Financial Foundations:** Explaining take-home pay, taxes, and deductions. [cite: 13]
* **Budget & Cash Flow:** Categorizing fixed vs. variable expenses. [cite: 13]
* **Credit Management:** Understanding APR, credit scores, and minimum payments. [cite: 14]
* **Workplace 401(k):** Explaining employer matches and Roth vs. Traditional concepts. [cite: 14]
* **Student Loan Transition:** Managing grace periods and repayment starts. [cite: 15]
* **Loans & Large Payments:** Explanation of loan specifics and borrowing money from institutions. [cite: 16]

**Scope Creep:** The agent will block specific financial advice (e.g., "buy this stock" or "apply for X card") to remain a safe educational tool. [cite: 17]

---

## 2. Technical Architecture
The project utilizes a Separation of Concerns model where AI handles natural language while deterministic code manages state and logic. [cite: 19]

### System Components [cite: 20]
* **Pre-Processing Layer:** Converts uploads (PDFs, CSVs, Images) into structured text and metadata. [cite: 21]
* **Analyzer (AI):** Extracts facts from user messages and proposes state updates using analyzer.md skills. [cite: 22]
* **Orchestrator (Code):** The "Boss" that validates AI proposals, updates the canonical state, and enforces phase transitions. [cite: 23]
* **Speaker (AI):** Generates conversational responses based on speaker.md guidance and missing state data. [cite: 24]
* **Artifact Renderer:** Generates deterministic outputs like PDF plan summaries, CSV budget tables, and chart images. [cite: 25]

### Team Roles (3-Person Structure) [cite: 26]
| Role | Key Responsibilities |
| :--- | :--- |
| **Architect & Backend Engineer** (Daniel Kang) | Manages the Orchestrator logic, state model (JSON), and database integration. Ensures deterministic phase transitions and safety gates are enforced in code. [cite: 27] |
| **AI Strategy & Prompt Engineer** (Shubh Vaishnav) | Develops the Analyzer and Speaker Markdown skills (analyzer.md, speaker.md) for all five goals. Tunes extraction accuracy and conversational tone. [cite: 27] |
| **Data & Integration Specialist** (Gabriel Ponsot) | Builds the Pre-Processing Layer (OCR/parsing) and the Artifact Renderer. Ensures PDF/CSV/Chart generation matches the structured data in the state model. [cite: 27] |

---

## 3. Execution Phases (The "Chapters") [cite: 28]
The conversation progresses through six distinct phases to ensure data is collected before a plan is generated: [cite: 29]
* **Phase 0:** Consent, scope, and output preference selection. [cite: 30]
* **Phase 1:** Baseline profile collection (Income, life stage). [cite: 31]
* **Phase 2:** Primary goal selection (e.g., "Build Credit"). [cite: 32]
* **Phase 3:** Evidence Intake (User uploads statements or provides manual answers). [cite: 33]
* **Phase 4:** Plan Builder (Generates the structured plan and artifacts). [cite: 34]
* **Phase 5:** Follow-up and action tracking. [cite: 35]

---

## 4. AI Workflow & Logic Flow (Pseudo-code) [cite: 36]
The system follows the "Back-to-start" planning method for the data pipeline: [cite: 37]

```python
# Phase 3: Evidence Intake & Processing
content = py_extractContentFromUploads(files) # OCR/Parsing [cite: 40]
topicsAndMarkers = llm_extractKeyFinancialTopics(content) # Identify APR, debt, etc. [cite: 41]

for {topic, marker} in topicsAndMarkers: [cite: 42]
    contentSegment = py_extractRelevantData(marker, content) # Isolate specific facts [cite: 43]
    extractedFacts = llm_analyzeSegment(topic, contentSegment) # Analyze for state delta [cite: 45]

# Phase 4: Plan Builder [cite: 47]
structuredPlan = llm_generatePlanText(state.profile, state.evidence) # Orientation logic [cite: 48]
artifacts = py_renderArtifacts(structuredPlan) # Generate PDF/CSV/Charts [cite: 49]

# Phase 5: Communication [cite: 50]
userMessage = llm_speakerResponse(state, artifacts) # Natural language output [cite: 51]
```

---

## 5. Implementation Requirements (Tool Assignment) [cite: 52]
| Step | Tool Type | Rationale |
| :--- | :--- | :--- |
| **Data Extraction** | py_ (Python) | High reliability for parsing PDFs/CSVs using standard libraries. [cite: 55] |
| **Intent & Fact Analysis** | llm_ (LLM) | Best for understanding messy human input and extracting context. [cite: 55] |
| **State Orchestration** | py_ (Code) | Deterministic code ensures business rules and safety gates are never bypassed. [cite: 55] |
| **Response Generation** | llm_ (LLM) | Provides natural, supportive tone for educational guidance. [cite: 55] |
| **Artifact Rendering** | py_ (Python) | Precise file manipulation for generating valid PDF and CSV files. [cite: 55] |

---

## 6. Iterative Development Plan [cite: 56]
1. **Pass 1 (MVP):** Focus on the "Financial Foundations" goal using text-only input to validate the Orchestrator's state tracking. [cite: 58]
2. **Pass 2 (Multimodal):** Integrate the py_extraction layer for document and image uploads. [cite: 59]
3. **Pass 3 (Prompt Optimization):** Refine analyzer.md and speaker.md templates through hands-on testing to resolve "lost in the middle" context issues. [cite: 60]

---

## 7. Key Constraints & Safety Gates [cite: 61]
* **Anti-Optimization:** The llm components are strictly prohibited from recommending specific financial products. [cite: 62]
* **Deterministic Validation:** No phase transition occurs solely on an AI suggestion; the py_Orchestrator must verify all required fields are present. [cite: 64]
* **Provenance Tracking:** Every extracted fact must be linked to a specific upload_id or user message for auditability. [cite: 65]

---

## 8. Project Roadmap: February - May 2026 [cite: 66]
### February: Foundation & Phase Skills [cite: 67]
* **Goal & Scope Definition:** Formally define the advisor's boundaries and set up Phase 0 and Phase 1. [cite: 69]
* **Phase Skill Authoring:** Write the initial analyzer.md and speaker.md files for basic budgeting and financial foundations. [cite: 70]
* **System Orchestration:** Build the deterministic Orchestrator with "Safety Gates" to block investment advice. [cite: 71]

### March: Multimodal Ingestion & Evidence Registry [cite: 72]
* **Pre-Processing Layer:** Implement Python-based (py_) tools to handle OCR for bank statements and parsing for document uploads. [cite: 75]
* **Phase 3 Development:** Enable the bot to extract "Evidence-Backed Facts" from uploaded files and store them in the Evidence Registry. [cite: 76]
* **Provenance Tracking:** Ensure the system records which specific upload produced each piece of data. [cite: 77]

### April: Plan Builder & Artifact Generation [cite: 79]
* **Phase 4: Plan Builder:** Develop the LLM logic to generate a structured financial plan based on the user's "Primary Goal" selected in Phase 2. [cite: 81]
* **Deterministic Rendering:** Build the Artifact Renderer to output PDF summaries, CSV budget tables, and image-based charts. [cite: 81]
* **Iterative Refinement:** Review where AI can be replaced by simple code (e.g., script for data reformatting) to save costs. [cite: 82]

### May: Evaluation, Testing & Final Delivery [cite: 83]
* **Extraction Accuracy Testing:** Run 30 test cases to ensure the Analyzer correctly identifies required fields. [cite: 86]
* **Phase Transition Stability:** Test "Mixed-order" user behavior to confirm the Orchestrator keeps the flow stable. [cite: 87]
* **Final Reflection & Update:** Use model feedback to identify remaining gaps and finalize the code. [cite: 88]

---

## 9. Success Criteria & Evaluation [cite: 89]
* **Extraction Accuracy:** Correctly identify APR, due dates, and amounts from 30 test inputs. [cite: 91]
* **Phase Stability:** The Orchestrator must keep the flow stable even if goals are changed midstream. [cite: 92]
* **Artifact Integrity:** PDF and CSV outputs must accurately reflect the numbers stored in the state model. [cite: 95]
* **Educational Quality:** Success in explaining financial concepts without providing illegal tax advice. [cite: 96]
* **Edge Case Handling:** Handle users refusing to provide data by providing general education without crashing. [cite: 97]
