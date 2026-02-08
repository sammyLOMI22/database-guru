# Product Manager Feedback: Database Guru Roadmap

**Date**: February 7, 2026
**Reviewer**: Antigravity (Product Manager / Lead Architect)
**Status**: Review Completed

---

## 1. Executive Summary

The current roadmap is comprehensive and ambitious, correctly identifying key pillars of growth: **Data Source Expansion**, **LLM Flexibility**, and **Deep Insight Generation**.

However, there is a divergence between the "Planned" status in the roadmap and the actual codebase state (specifically Phase 13). Additionally, as we move toward "Edit Mode" (Phase 18) and "Enterprise LLMs" (Phase 15), the current "Lower Priority" status of Security/Auth becomes a critical strategic risk.

**Top-Level Recommendation**: Pause new "width" expansion (NoSQL) to focus on "depth" and "safety" (Security, DML Safety, Monitoring) to ensure the platform is enterprise-ready before adding more complexity.

---

## 2. Roadmap Status Corrections

| Phase | Roadmap Status | Actual Status | Recommendation |
|-------|----------------|---------------|----------------|
| **Phase 13: CSV/Excel** | PLANNED | **IMPLEMENTED** | Update Roadmap to ✅ In Review/Complete. Code exists in `src/core/file_source_handler.py`. |
| **Phase 14: NoSQL** | PLANNED | Not Started | Re-evaluate priority vs. Security. |

---

## 3. Strategic Gaps & Recommendations

### A. The "Dangerous Features" Paradox
**Issue**: We are planning **Phase 18 (Edit Mode & DML)** and **Phase 15 (Enterprise LLMs)**, but **Security (Auth, Rate Limiting)** is listed as "Lower Priority" / "Deferred".
**PM Risk Assessment**: 🔴 **CRITICAL**
- You cannot release "Edit Mode" (DELETE/UPDATE capabilities) without robust **Authentication** and **Audit Logging**.
- You cannot integrate expensive "Azure OpenAI" models without **Rate Limiting** and **Cost Controls** (Phase 16/17).

**Recommendation**:
- **Promote "Security & Infrastructure"** to **IMMEDIATE PRIORITY**.
- Merge "Audit Log" from Phase 18 with a global "Security Layer".
- Require Auth before Edit Mode.

### B. From "Single Player" to "Multiplayer"
**Issue**: The roadmap ends at "Collaborative Features" (Priority LOW).
**PM Opportunity**: Data insights are rarely consumed alone.
**Recommendation**:
- **Shared Workspaces**: Allow users to share a "Session" content (read-only) with a URL.
- **Annotated History**: Allow users to comment on Agent outputs for future context.

### C. Proactive vs. Reactive
**Issue**: The current app helps users *ask* questions. It doesn't tell them what they *didn't know to ask*.
**Recommendation**:
- **"Watchdog Agents"**: Allow the agent to run scheduled queries (e.g., "Check 'Order Volume' every hour") and alert the user if anomalies occur. This shifts the value prop from "Tool" to "Teammate".

---

## 4. Feature Enhancements & Ideas

### 🏗️ For "Edit Mode" (Phase 18)
- **"Simulation Mode" (Dry Run)**: Before executing a DELETE/UPDATE, run it in a transaction, count the affected rows, show a "Diff" of the change, and roll it back. Only commit if the user explicitly approves the *Diff*.
- **"Undo Button"**: For databases that support it (or via transaction logs), provide a "Time Travel" rollback for actions taken by the Guru.

### 🧠 For "Data Insights" (Phase 19)
- **"Metric Trees"**: Instead of just "charts", automatically build a dependency tree of metrics (e.g., "Revenue dropped" -> breakdown by "Region" -> breakdown by "Product").
- **"Business Glossary"**: Allow users to define terms like "Churn" or "Active User" so the LLM uses consistent definitions across all queries.

### 🔌 Integration Ecosystem
- **"Guru API"**: Expose the Agent as an API. Allow a Slack bot or external dashboard to "Ask Guru" and get a JSON/Markdown response.
- **"Webhook Sources"**: Instead of just Files/DBs, allow querying a JSON endpoint as a table (DuckDB supports this).

---

## 5. Proposed Priority adjustments

| Current Priority | Proposed Priority | Rationale |
|------------------|-------------------|-----------|
| NoSQL Expansion (Phase 14) | 🟢 Low | SQL + Files (Phase 13) covers 90% of analytic use cases. NoSQL is niche for analytics. |
| Security (Auth/Rate Limit) | 🔴 **Critical** | Prerequisite for DML (Phase 18) and Ent. LLMs (Phase 15). |
| Edit Mode (Phase 18) | 🟡 High | High user value, but blocked by Security. |
| LLM Usage Monitoring (Phase 16) | 🟢 Medium | Good for cost control, but less critical than Auth. |

---

## 6. Conclusion

Refocus the next sprint on **stabilizing the foundation** (Security/Auth) to support the powerful features coming next (Edit Mode, Enterprise LLMs). The "File Support" (Phase 13) win is huge—leverage that to test the waters with "Hybrid Queries" (SQL + CSV) before jumping into NoSQL.
