# Phase 6: Salesforce Sync Infrastructure - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Shared sync infrastructure for all Salesforce syncs: utilities, Zod schemas, pagination handling, and SOQL query builder. This foundation enables Phases 7-9 (Opportunities, OpportunityHistory, Activities) to focus on their specific data models.

</domain>

<decisions>
## Implementation Decisions

### File organization
- Flat structure in `nango-integrations/salesforce/` root: `utils.ts`, `models.ts`, `types.ts`
- Matches Nango template pattern (no nested modules)
- Each sync is a single self-contained file in `salesforce/syncs/` (schema + mapper + sync logic together)

### Schema design
- Preserve Salesforce field names as-is (PascalCase: `AccountName`, `CloseDate`, `OwnerId`)
- No transformations in sync layer — raw data forwarded to data-hub
- Transformations handled in future downstream work
- Nested arrays for relationships (e.g., `OpportunityContactRoles` as array on Opportunity)
- Permissive nullables using `z.union([z.string(), z.null()])` — preserve null semantics, no coercion

### Pagination & SOQL
- Use Nango built-in `nango.paginate()` with `link_path_in_response_body: 'nextRecordsUrl'`
- Shared `buildQuery(model, fields, lastSyncDate)` helper in `utils.ts` for consistent incremental filter handling
- Standard Salesforce REST API endpoint: `/services/data/v60.0/query`

### Claude's Discretion
- Sync frequency and autoStart defaults
- Error handling and retry configuration
- TypeScript type inference patterns

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Salesforce API Spec
- `docs/Staq Salesforce Revenue Reporting Spec.docx` — SOQL queries, field definitions, join key architecture, pagination patterns

### Nango Patterns
- `nango-integrations/github/syncs/fetch-issues.ts` — Reference createSync implementation with Zod schemas and pagination
- Nango integration templates: https://github.com/NangoHQ/integration-templates/tree/main/integrations/salesforce

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `nango-integrations/github/syncs/fetch-issues.ts`: Example of createSync pattern with Zod validation, pagination, and batchSave

### Established Patterns
- Nango createSync with `exec` function, `models` with Zod schemas
- `nango.paginate()` for automatic pagination
- `nango.batchSave()` for persisting records
- Type export pattern: `export type NangoSyncLocal = Parameters<(typeof sync)['exec']>[0]`

### Integration Points
- `nango-integrations/salesforce/syncs/` directory exists (empty, ready for sync files)
- `nango-integrations/index.ts` will need imports for Salesforce syncs

</code_context>

<specifics>
## Specific Ideas

- Follow Nango template patterns from their official Salesforce integration examples
- Raw data philosophy: get data as-is from Salesforce, transformations happen downstream
- Use API version v60.0 (current stable)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-salesforce-sync-infrastructure*
*Context gathered: 2026-03-20*
