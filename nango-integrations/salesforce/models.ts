/**
 * Shared Zod schema helpers for common Salesforce field patterns.
 *
 * These are building blocks used to compose per-sync schemas (Opportunity, Task, etc.)
 * in their respective sync files. They preserve Salesforce's raw field conventions:
 *   - PascalCase field names (AccountName, CloseDate, OwnerId)
 *   - Null semantics preserved via z.union — no coercion, no undefined-for-null
 *
 * Usage in a sync file:
 *   import { sfId, sfDateTime, sfNullableString } from '../models.js';
 *   const opportunitySchema = z.object({ Id: sfId, Name: sfNullableString, CloseDate: sfDateTime });
 */

import * as z from 'zod';

// ---------------------------------------------------------------------------
// Nullable field helpers
// ---------------------------------------------------------------------------

/**
 * A Salesforce string field that can be null (e.g. Description, Website).
 * Uses z.union to preserve null semantics without coercion.
 */
export const sfNullableString = z.union([z.string(), z.null()]);

/**
 * A Salesforce numeric field that can be null (e.g. Amount, Probability).
 */
export const sfNullableNumber = z.union([z.number(), z.null()]);

/**
 * A Salesforce boolean field that can be null (e.g. IsWon on some objects).
 */
export const sfNullableBoolean = z.union([z.boolean(), z.null()]);

// ---------------------------------------------------------------------------
// Common field patterns
// ---------------------------------------------------------------------------

/**
 * Salesforce 18-character record ID (case-insensitive unique identifier).
 * All Salesforce objects use this format for their Id field and relationship fields.
 */
export const sfId = z.string().length(18);

/**
 * Salesforce DateTime field in ISO 8601 format.
 * Salesforce returns datetimes like "2024-01-15T10:30:00.000+0000" (with timezone offset)
 * rather than strict "Z" suffix, so we use a regex pattern instead of z.datetime().
 * Used for fields like CreatedDate, LastModifiedDate.
 */
export const sfDateTime = z.string().regex(
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{4})$/,
    'Invalid Salesforce datetime format'
);

/**
 * Salesforce Date field in YYYY-MM-DD format (e.g. "2024-01-15").
 * Used for fields like CloseDate on Opportunity.
 */
export const sfDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);

/**
 * Currency amount field — can be null when no value is set.
 * Alias of sfNullableNumber for semantic clarity in schemas.
 */
export const sfCurrency = sfNullableNumber;

/**
 * Percentage field (0–100 range, can be null).
 * Alias of sfNullableNumber for semantic clarity in schemas.
 */
export const sfPercentage = sfNullableNumber;
