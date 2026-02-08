# Future Feature Brainstorming

**Status**: DRAFT
**Purpose**: Innovation & Value Expansion

---

## 1. Performance Guru (Deep Explain Analysis)

**The Gap**: Current "Pattern Intelligence" finds simple regex-based issues (e.g., "Leading Wildcard"). It does **not** understand the database's actual execution plan cost model.

**The Solution**:
*   **Explain Analyzer**: Run `EXPLAIN (FORMAT JSON) ANALYZE ...` for slow queries.
*   **LLM Interpretation**: Parse the JSON plan. Identify:
    *   "Sequential Scan on Table X (10GB) -> Cost 50,000"
    *   "Hash Join spilling to disk"
*   **Actionable Advice**: "Create INDEX ON users(email) to change this Seq Scan to an Index Scan."

**Why Guru?**: Reading raw Explain plans is hard. interpreting them requires deep expertise. The LLM is perfect for this translation layer.

---

## 2. Synthetic Data Generator ("Smart Seeding")

**The Gap**: Users often lack realistic test data for development/staging.

**The Solution**:
*   **Schema Analysis**: Read Foreign Keys and Data Types.
*   **Distribution Matching**: (Optional) Read stats from Prod to understand "User status is 80% 'Active', 20% 'Churned'".
*   **Generation**: Create a Python/SQL script to insert 10,000 valid rows.
    *   *Constraint Aware*: Inserts Users before Orders.
    *   *Semantic*: Generates real-looking names, emails, addresses (using `faker`).

**Why Guru?**: Manual seeding is tedious. "Fill this empty database with life" is a magical user experience.

---

## 3. "API-ify" (Query to Endpoint)

**The Gap**: Analysts find an insight (e.g., "Churned Users List") and want to share it with a frontend app or a partner.

**The Solution**:
*   **One-Click API**: User clicks "Deploy as API".
*   **Output**:
    *   Generates a `FastAPI` route snippet.
    *   OR (Advanced) Spins up a temporary endpoint: `GET /api/dynamic/churned_users?min_spend=500`
*   **Docs**: Auto-generates Swagger/OpenAPI docs for the new endpoint.

**Why Guru?**: Closes the loop from "Analysis" to "Product".

---

## 4. Database Documentation Site (Auto-Docs)

**The Gap**: Database schemas are often undocumented. "What does `status_id = 7` mean?"

**The Solution**:
*   **Static Site Gen**: Generate a `Docusaurus` or `MkDocs` site.
*   **Content**:
    *   ER Diagrams (from Phase 7).
    *   Column descriptions (AI-generated based on name/data).
    *   Sample queries (from Query History).
*   **Lineage**: Embed the Lineage graphs (Phase 11).

**Why Guru?**: Documentation is the first thing to rot. Automated documentation stays fresh.
