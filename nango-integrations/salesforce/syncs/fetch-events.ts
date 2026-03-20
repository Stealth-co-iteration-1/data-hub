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

/** Owner (User) fields denormalized onto the Event for rep attribution. */
const ownerSchema = z.object({
    Name: sfNullableString,
    Email: sfNullableString
});

// ---------------------------------------------------------------------------
// Main Event schema (EVNT-01 fields + Nango-required id)
// ---------------------------------------------------------------------------
// Nango requires a lowercase `id` field on every model (used as record key).
// We include both the canonical Salesforce `Id` and the required Nango `id`.
// ---------------------------------------------------------------------------

const eventSchema = z.object({
    // Nango record key (maps from Salesforce Id in exec)
    id: sfId,

    // Core fields (EVNT-01)
    Id: sfId,
    Subject: sfNullableString,
    StartDateTime: sfDateTime,
    EndDateTime: sfDateTime,
    DurationInMinutes: sfNullableNumber,
    ActivityDate: z.union([sfDate, z.null()]),
    CreatedDate: sfDateTime,

    // Polymorphic lookup IDs (EVNT-03 — preserve raw IDs for downstream join)
    WhoId: z.union([sfId, z.null()]),     // Contact or Lead
    WhatId: z.union([sfId, z.null()]),    // Account, Opportunity, etc.
    OwnerId: sfId,

    // Activity type
    Type: sfNullableString,
    EventSubtype: sfNullableString,

    // Relationship objects
    Who: z.union([whoSchema, z.null()]),  // null when WhoId is null
    Owner: ownerSchema
});

type Event = z.infer<typeof eventSchema>;

// ---------------------------------------------------------------------------
// SOQL field list (custom — buildQuery doesn't support relationship traversal)
// ---------------------------------------------------------------------------

const EVENT_SOQL_FIELDS = `
    Id, Subject, StartDateTime, EndDateTime, DurationInMinutes, ActivityDate, CreatedDate,
    WhoId, WhatId, OwnerId, Type, EventSubtype,
    Who.Email, Owner.Name, Owner.Email
`.replace(/\s+/g, ' ').trim();

// ---------------------------------------------------------------------------
// Incremental SOQL builder (EVNT-02 — StartDateTime filter)
// ---------------------------------------------------------------------------

/**
 * Builds the full SOQL query for Events.
 *
 * When `lastSyncDate` is provided, adds a `WHERE ... AND StartDateTime >= {date}` clause
 * so the sync only fetches events starting at or after the last run (EVNT-02).
 *
 * We use `>=` (not `>`) to include events starting at the exact sync timestamp.
 * StartDateTime is a DateTime type so we use the full ISO 8601 string.
 *
 * @param lastSyncDate - If provided, adds incremental filter on StartDateTime.
 */
function buildEventQuery(lastSyncDate?: Date): string {
    const baseWhere = 'WHERE IsDeleted = false';
    const incrementalClause =
        lastSyncDate !== undefined
            ? ` AND StartDateTime >= ${lastSyncDate.toISOString()}`
            : '';
    return `SELECT ${EVENT_SOQL_FIELDS} FROM Event ${baseWhere}${incrementalClause}`;
}

// ---------------------------------------------------------------------------
// Sync definition
// ---------------------------------------------------------------------------

const sync = createSync({
    description: 'Fetches Salesforce Event records with Who and Owner relationships.',
    version: '1.0.0',
    endpoints: [{ method: 'GET', path: '/salesforce/events', group: 'Events' }],
    frequency: 'every hour',
    autoStart: true,
    syncType: 'incremental',

    metadata: z.void(),
    models: {
        Event: eventSchema
    },

    exec: async (nango) => {
        // lastSyncDate is a property (Date | undefined) — no function call needed
        const soql = buildEventQuery(nango.lastSyncDate);

        for await (const batch of nango.paginate({
            endpoint: queryEndpoint(soql),
            paginate: salesforcePaginationConfig,
            retries: 3
        })) {
            // Normalise each record by adding the lowercase `id` key required by Nango.
            const events: Event[] = batch.map((record: unknown) => {
                const raw = record as Record<string, unknown>;
                return eventSchema.parse({ ...raw, id: raw['Id'] });
            });

            if (events.length > 0) {
                await nango.batchSave(events, 'Event');
                await nango.log(`Saved ${events.length} events`);
            }
        }
    }
});

export type NangoSyncLocal = Parameters<(typeof sync)['exec']>[0];
export default sync;
