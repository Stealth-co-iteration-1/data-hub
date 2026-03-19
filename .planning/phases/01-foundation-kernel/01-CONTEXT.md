# Phase 1: Foundation & Kernel - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Pure business logic establishing domain model, validation rules, and port interfaces. The kernel has zero external dependencies — FastAPI, SQLAlchemy, asyncpg, etc. live in adapters (later phases). This phase delivers testable commands, events, and ports without any infrastructure code.

</domain>

<decisions>
## Implementation Decisions

### Command Payload (AddDataCommand)
- Schema reference is a logical name (e.g., `hubspot_contact`) — not an inline schema definition
- Kernel receives the reference and looks it up via a SchemaRegistry port
- Payload is generic (`Dict[str, Any]` / JSON-serializable) — validation happens against the schema
- Command includes metadata: source_id, table/registry reference, plus the raw payload
- Command supports observability fields (correlation ID, timestamp, etc.)

### Schema Registry
- Kernel defines a SchemaRegistry port (interface)
- Adapters implement it — could be Python code, JSON files, or database-backed
- Schemas are Pydantic models (or similar) for validation
- The kernel doesn't know WHERE schemas come from — only that it can look them up

### Validation Rules
- **Strict validation means:** Type mismatches rejected, missing required fields rejected
- **Extra fields:** Allowed and preserved — flexible for evolving integrations
- Format violations (email, date) handled by schema definition, not kernel logic

### Validation Errors
- Field path included (e.g., `contact.email`)
- Expected vs actual values included
- Errors are structured data, not strings — downstream can process them

### Claude's Discretion
- Exact error class hierarchy
- Whether to use Python Protocols or ABCs for ports
- Internal data structures for validation results

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture
- `.planning/research/ARCHITECTURE.md` — Hexagonal architecture patterns, component boundaries, data flow
- `.planning/research/STACK.md` — Pydantic 2.12.5 for validation, Python Protocols for ports

### Pitfalls
- `.planning/research/PITFALLS.md` — Kernel purity enforcement, Pydantic validator performance (use Annotated constraints)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing application code

### Established Patterns
- None yet — this phase establishes the foundational patterns

### Integration Points
- Phase 2 will implement DataRepository port (PostgreSQL adapter)
- Phase 3 will call kernel commands from FastAPI transport

</code_context>

<specifics>
## Specific Ideas

- Schema reference resolves to different physical locations depending on adapter (PostgreSQL adapter maps to schema.table_name)
- Kernel validation engine is generic — it uses the SchemaRegistry port to fetch schemas, then validates
- The kernel should be fully testable with in-memory mocks of all ports

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation-kernel*
*Context gathered: 2026-03-18*
