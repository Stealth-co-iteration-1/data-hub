/**
 * TypeScript types inferred from Salesforce Zod schemas, plus re-exports of all schemas.
 *
 * Downstream syncs can use a single import point for both types and schemas:
 *
 *   // Import types only:
 *   import type { SalesforceId, SalesforceDateTime } from '../types.js';
 *
 *   // Import schemas for runtime validation:
 *   import { sfId, sfDateTime, sfNullableString } from '../types.js';
 *
 *   // Import both in one statement:
 *   import { sfId, type SalesforceId } from '../types.js';
 */

import * as z from 'zod';
import {
    sfId,
    sfDateTime,
    sfDate,
    sfNullableString,
    sfNullableNumber,
    sfNullableBoolean,
    sfCurrency,
    sfPercentage
} from './models.js';

// ---------------------------------------------------------------------------
// Inferred TypeScript types from Zod schemas
// ---------------------------------------------------------------------------

/** TypeScript type for a Salesforce 18-character record ID. */
export type SalesforceId = z.infer<typeof sfId>;

/** TypeScript type for a Salesforce DateTime field (ISO 8601 string). */
export type SalesforceDateTime = z.infer<typeof sfDateTime>;

/** TypeScript type for a Salesforce Date field (YYYY-MM-DD string). */
export type SalesforceDate = z.infer<typeof sfDate>;

/** TypeScript type for a nullable Salesforce string field (string | null). */
export type NullableString = z.infer<typeof sfNullableString>;

/** TypeScript type for a nullable Salesforce number field (number | null). */
export type NullableNumber = z.infer<typeof sfNullableNumber>;

/** TypeScript type for a nullable Salesforce boolean field (boolean | null). */
export type NullableBoolean = z.infer<typeof sfNullableBoolean>;

/** TypeScript type for a Salesforce currency field (number | null). */
export type Currency = z.infer<typeof sfCurrency>;

/** TypeScript type for a Salesforce percentage field (number | null). */
export type Percentage = z.infer<typeof sfPercentage>;

// ---------------------------------------------------------------------------
// Re-export all schemas for convenience (single import point)
// ---------------------------------------------------------------------------

export * from './models.js';
