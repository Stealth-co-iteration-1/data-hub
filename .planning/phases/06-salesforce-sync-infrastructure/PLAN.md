---
phase: 06-salesforce-sync-infrastructure
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - nango-integrations/salesforce/utils.ts
  - nango-integrations/salesforce/models.ts
  - nango-integrations/salesforce/types.ts
autonomous: true
requirements:
  - INFR-01
  - INFR-02
  - INFR-03

must_haves:
  truths:
    - "Salesforce syncs can import shared Zod schemas for field validation"
    - "Salesforce syncs can use buildQuery helper to generate SOQL with incremental filters"
    - "Salesforce pagination config works with nango.paginate() using nextRecordsUrl"
    - "TypeScript types are inferred from Zod schemas for type safety"
  artifacts:
    - path: "nango-integrations/salesforce/utils.ts"
      provides: "buildQuery helper, pagination config, API constants"
      exports: ["buildQuery", "salesforcePaginationConfig", "SALESFORCE_API_VERSION"]
    - path: "nango-integrations/salesforce/models.ts"
      provides: "Shared Zod schemas for common Salesforce field patterns"
      exports: ["sfNullableString", "sfNullableNumber", "sfNullableBoolean", "sfId", "sfDateTime"]
    - path: "nango-integrations/salesforce/types.ts"
      provides: "TypeScript types inferred from Zod schemas"
      exports: ["SalesforceId", "SalesforceDateTime"]
  key_links:
    - from: "nango-integrations/salesforce/types.ts"
      to: "nango-integrations/salesforce/models.ts"
      via: "z.infer imports"
      pattern: "z\\.infer<typeof"
---

<objective>
Create shared sync infrastructure for all Salesforce syncs: utilities for SOQL query building, pagination configuration, and Zod schemas for common field patterns.

Purpose: Foundation enabling Phases 7-9 to focus on their specific data models without reimplementing common patterns. Establishes the raw data philosophy (preserve Salesforce field names as-is, no transformations).

Output: Three shared modules (`utils.ts`, `models.ts`, `types.ts`) in `nango-integrations/salesforce/` root.
</objective>

<execution_context>
@/Users/renanfonseca/.claude/get-shit-done/workflows/execute-plan.md
@/Users/renanfonseca/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/06-salesforce-sync-infrastructure/06-CONTEXT.md

Reference implementation:
@nango-integrations/github/syncs/fetch-issues.ts
</context>

<interfaces>
<!-- Key patterns from existing codebase that executor should follow -->

From nango-integrations/github/syncs/fetch-issues.ts:
```typescript
import { createSync } from 'nango';
import * as z from 'zod';

// Zod schema pattern
const issueSchema = z.object({
    id: z.string(),
    // ... fields
});
type GithubIssue = z.infer<typeof issueSchema>;

// Pagination pattern
const proxyConfig = {
    endpoint: `/repos/${repo.owner.login}/${repo.name}/issues`,
    paginate: {
        limit: LIMIT
    }
};
for await (const batch of nango.paginate(proxyConfig)) {
    // process batch
}
```

Salesforce REST API pagination (from spec):
- Endpoint: `/services/data/v60.0/query?q={SOQL}`
- Response includes `nextRecordsUrl` for pagination
- Use `link_path_in_response_body: 'nextRecordsUrl'` in paginate config
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Create utils.ts with buildQuery and pagination config</name>
  <files>nango-integrations/salesforce/utils.ts</files>
  <action>
Create `nango-integrations/salesforce/utils.ts` with:

1. **API version constant:**
   ```typescript
   export const SALESFORCE_API_VERSION = 'v60.0';
   ```

2. **Pagination config helper** for use with `nango.paginate()`:
   ```typescript
   export const salesforcePaginationConfig = {
       link_path_in_response_body: 'nextRecordsUrl'
   };
   ```

3. **buildQuery helper** that generates SOQL queries with optional incremental filter:
   ```typescript
   export function buildQuery(
       model: string,
       fields: string[],
       lastSyncDate?: Date
   ): string
   ```
   - Joins fields with comma
   - Appends `WHERE LastModifiedDate > {ISO8601 date}` if lastSyncDate provided
   - Returns full SOQL string: `SELECT {fields} FROM {model} [WHERE ...]`

4. **Query endpoint helper:**
   ```typescript
   export function queryEndpoint(soql: string): string {
       return `/services/data/${SALESFORCE_API_VERSION}/query?q=${encodeURIComponent(soql)}`;
   }
   ```

Include JSDoc comments explaining usage patterns. Follow the flat file structure per CONTEXT.md decisions.
  </action>
  <verify>
    <automated>cd /Users/renanfonseca/Workspace/defensepoint/staq/data-hub/nango-integrations && npx tsc --noEmit salesforce/utils.ts</automated>
  </verify>
  <done>
    - utils.ts exports buildQuery, salesforcePaginationConfig, queryEndpoint, SALESFORCE_API_VERSION
    - buildQuery generates valid SOQL with optional LastModifiedDate filter
    - TypeScript compiles without errors
  </done>
</task>

<task type="auto">
  <name>Task 2: Create models.ts with shared Zod schema helpers</name>
  <files>nango-integrations/salesforce/models.ts</files>
  <action>
Create `nango-integrations/salesforce/models.ts` with Zod schema helpers for common Salesforce field patterns:

1. **Nullable field helpers** (per CONTEXT.md decision: permissive nullables with `z.union`):
   ```typescript
   // Preserves null semantics, no coercion
   export const sfNullableString = z.union([z.string(), z.null()]);
   export const sfNullableNumber = z.union([z.number(), z.null()]);
   export const sfNullableBoolean = z.union([z.boolean(), z.null()]);
   ```

2. **Common field patterns:**
   ```typescript
   // Salesforce 18-character ID
   export const sfId = z.string().length(18);

   // Salesforce DateTime (ISO8601 format)
   export const sfDateTime = z.string().datetime();

   // Salesforce Date (YYYY-MM-DD)
   export const sfDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);

   // Currency amounts (can be null)
   export const sfCurrency = sfNullableNumber;

   // Percentage (0-100, can be null)
   export const sfPercentage = sfNullableNumber;
   ```

3. **Import zod:**
   ```typescript
   import * as z from 'zod';
   ```

Preserve Salesforce PascalCase field naming convention. These are building blocks; actual model schemas (Opportunity, Task, etc.) will be defined in their respective sync files per CONTEXT.md pattern "each sync is a single self-contained file."
  </action>
  <verify>
    <automated>cd /Users/renanfonseca/Workspace/defensepoint/staq/data-hub/nango-integrations && npx tsc --noEmit salesforce/models.ts</automated>
  </verify>
  <done>
    - models.ts exports sfNullableString, sfNullableNumber, sfNullableBoolean, sfId, sfDateTime, sfDate, sfCurrency, sfPercentage
    - All schemas use z.union pattern for nullable fields (not z.optional or z.nullable)
    - TypeScript compiles without errors
  </done>
</task>

<task type="auto">
  <name>Task 3: Create types.ts with TypeScript type exports</name>
  <files>nango-integrations/salesforce/types.ts</files>
  <action>
Create `nango-integrations/salesforce/types.ts` with TypeScript types inferred from Zod schemas:

```typescript
import * as z from 'zod';
import { sfId, sfDateTime, sfDate, sfNullableString, sfNullableNumber, sfNullableBoolean, sfCurrency, sfPercentage } from './models.js';

// Inferred types from Zod schemas
export type SalesforceId = z.infer<typeof sfId>;
export type SalesforceDateTime = z.infer<typeof sfDateTime>;
export type SalesforceDate = z.infer<typeof sfDate>;
export type NullableString = z.infer<typeof sfNullableString>;
export type NullableNumber = z.infer<typeof sfNullableNumber>;
export type NullableBoolean = z.infer<typeof sfNullableBoolean>;
export type Currency = z.infer<typeof sfCurrency>;
export type Percentage = z.infer<typeof sfPercentage>;

// Re-export Zod schemas for convenience
export * from './models.js';
```

Use `.js` extension in imports per Nango TypeScript conventions (ESM output).

This enables downstream syncs to:
- Import types: `import type { SalesforceId } from '../types.js'`
- Import schemas: `import { sfId, sfDateTime } from '../types.js'`
  </action>
  <verify>
    <automated>cd /Users/renanfonseca/Workspace/defensepoint/staq/data-hub/nango-integrations && npx tsc --noEmit salesforce/types.ts</automated>
  </verify>
  <done>
    - types.ts exports SalesforceId, SalesforceDateTime, SalesforceDate, NullableString, NullableNumber, NullableBoolean
    - types.ts re-exports all schemas from models.ts
    - Import path uses .js extension for ESM compatibility
    - TypeScript compiles without errors
  </done>
</task>

</tasks>

<verification>
After all tasks complete:

1. **TypeScript compilation:**
   ```bash
   cd nango-integrations && npx tsc --noEmit salesforce/*.ts
   ```

2. **Export verification:**
   ```bash
   grep -E "^export" nango-integrations/salesforce/*.ts
   ```
   Should show exports from all three files.

3. **Directory structure:**
   ```bash
   ls -la nango-integrations/salesforce/
   ```
   Should show: utils.ts, models.ts, types.ts, syncs/
</verification>

<success_criteria>
1. `nango-integrations/salesforce/utils.ts` exists with buildQuery, salesforcePaginationConfig, queryEndpoint exports
2. `nango-integrations/salesforce/models.ts` exists with nullable helpers and common field schemas
3. `nango-integrations/salesforce/types.ts` exists with inferred TypeScript types
4. All three files compile without TypeScript errors
5. `nango-integrations/salesforce/syncs/` directory ready for sync implementations (already exists)
</success_criteria>

<output>
After completion, create `.planning/phases/06-salesforce-sync-infrastructure/06-01-SUMMARY.md`
</output>
