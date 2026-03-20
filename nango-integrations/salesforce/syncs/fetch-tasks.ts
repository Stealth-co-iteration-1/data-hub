import { createSync } from 'nango';
import * as z from 'zod';
import { queryEndpoint, salesforcePaginationConfig } from '../utils.js';
import { sfId, sfDateTime, sfDate, sfNullableString, sfNullableNumber } from '../types.js';

// ---------------------------------------------------------------------------
// Nested relationship schemas
// ---------------------------------------------------------------------------

/** Who (Contact or Lead) fields for join key resolution. */
const whoSchema = z.object({
    Email: sfNullableString
});

/** Owner (User) fields for rep attribution. */
const ownerSchema = z.object({
    Name: sfNullableString,
    Email: sfNullableString
});

// ---------------------------------------------------------------------------
// Main Task schema (TASK-01 fields + Nango-required id)
// ---------------------------------------------------------------------------
// Nango requires a lowercase `id` field on every model (used as record key).
// We include both the canonical Salesforce `Id` and the required Nango `id`.
// ---------------------------------------------------------------------------

const taskSchema = z.object({
    // Nango record key (maps from Salesforce Id in exec)
    id: sfId,

    // Core fields (TASK-01)
    Id: sfId,
    Subject: sfNullableString,
    Status: sfNullableString,
    ActivityDate: z.union([sfDate, z.null()]),  // DATE type (YYYY-MM-DD), nullable
    CreatedDate: sfDateTime,

    // Polymorphic lookup IDs (TASK-03 — preserved for downstream join)
    WhoId: z.union([sfId, z.null()]),   // Contact or Lead
    WhatId: z.union([sfId, z.null()]),  // Account, Opportunity, etc.
    OwnerId: sfId,

    // Activity type
    Type: sfNullableString,
    TaskSubtype: sfNullableString,

    // Call tracking fields (TASK-01)
    CallType: sfNullableString,             // Inbound, Outbound, Internal
    CallDurationInSeconds: sfNullableNumber,
    CallDisposition: sfNullableString,

    // Relationship objects
    Who: z.union([whoSchema, z.null()]),   // null when WhoId is null
    Owner: ownerSchema
});

type Task = z.infer<typeof taskSchema>;

// ---------------------------------------------------------------------------
// SOQL field list (custom — buildQuery doesn't support relationship traversal)
// ---------------------------------------------------------------------------

// Note: buildQuery doesn't support relationship fields, so we build SOQL manually
const TASK_SOQL_FIELDS = `
    Id, Subject, Status, ActivityDate, CreatedDate,
    WhoId, WhatId, OwnerId, Type, TaskSubtype,
    CallType, CallDurationInSeconds, CallDisposition,
    Who.Email, Owner.Name, Owner.Email
`.replace(/\s+/g, ' ').trim();

// ---------------------------------------------------------------------------
// Incremental SOQL builder (TASK-02 - ActivityDate filter)
// ---------------------------------------------------------------------------

/**
 * Builds the full SOQL query for Tasks.
 *
 * When `lastSyncDate` is provided, adds an `AND ActivityDate >= {date}` clause
 * so the sync only fetches records on or after the last sync date (TASK-02).
 *
 * ActivityDate is a DATE type (YYYY-MM-DD), so we extract just the date portion
 * from lastSyncDate. We use `>=` (not `>`) to include tasks on the same day.
 *
 * @param lastSyncDate - If provided, adds ActivityDate >= filter for incremental syncs.
 */
function buildTaskQuery(lastSyncDate?: Date): string {
    const baseWhere = 'WHERE IsDeleted = false';
    const incrementalClause =
        lastSyncDate !== undefined
            ? ` AND ActivityDate >= ${lastSyncDate.toISOString().split('T')[0]}`
            : '';
    return `SELECT ${TASK_SOQL_FIELDS} FROM Task ${baseWhere}${incrementalClause}`;
}

// ---------------------------------------------------------------------------
// Sync definition
// ---------------------------------------------------------------------------

const sync = createSync({
    description: 'Fetches Salesforce Task records with Who and Owner relationships.',
    version: '1.0.0',
    endpoints: [{ method: 'GET', path: '/salesforce/tasks', group: 'Tasks' }],
    frequency: 'every hour',
    autoStart: true,
    syncType: 'incremental',

    metadata: z.void(),
    models: {
        Task: taskSchema
    },

    exec: async (nango) => {
        // lastSyncDate is a property (Date | undefined) — no function call needed
        const soql = buildTaskQuery(nango.lastSyncDate);

        for await (const batch of nango.paginate({
            endpoint: queryEndpoint(soql),
            paginate: salesforcePaginationConfig,
            retries: 3
        })) {
            // Normalise each record by adding the lowercase `id` key required by Nango.
            const tasks: Task[] = batch.map((record: unknown) => {
                const raw = record as Record<string, unknown>;
                return taskSchema.parse({ ...raw, id: raw['Id'] });
            });

            if (tasks.length > 0) {
                await nango.batchSave(tasks, 'Task');
                await nango.log(`Saved ${tasks.length} tasks`);
            }
        }
    }
});

export type NangoSyncLocal = Parameters<(typeof sync)['exec']>[0];
export default sync;
