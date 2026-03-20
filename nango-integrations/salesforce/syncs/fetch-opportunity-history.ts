import { createSync } from 'nango';
import * as z from 'zod';
import { queryEndpoint, salesforcePaginationConfig } from '../utils.js';
import { sfId, sfDateTime, sfDate, sfNullableString, sfCurrency, sfPercentage } from '../types.js';

// ---------------------------------------------------------------------------
// OpportunityHistory schema (9 spec fields from HIST-01 + Nango-required id)
// ---------------------------------------------------------------------------
// Nango requires a lowercase `id` field on every model (used as record key).
// We include both the canonical Salesforce `Id` and the required Nango `id`.
// ---------------------------------------------------------------------------

const opportunityHistorySchema = z.object({
    // Nango record key (maps from Salesforce Id in exec)
    id: sfId,

    // Core fields (HIST-01)
    // Note: ForecastCategoryName is NOT available on OpportunityHistory (only on Opportunity)
    Id: sfId,
    OpportunityId: sfId,
    StageName: sfNullableString,         // nullable — null when only Amount changed
    Amount: sfCurrency,                  // nullable number
    CloseDate: sfDate,                   // YYYY-MM-DD
    Probability: sfPercentage,           // nullable number 0-100
    CreatedDate: sfDateTime,             // when the change occurred
    CreatedById: sfId                    // user who made the change
});

type OpportunityHistory = z.infer<typeof opportunityHistorySchema>;

// ---------------------------------------------------------------------------
// SOQL field list (flat table — no nested relationships)
// ---------------------------------------------------------------------------

// Note: ForecastCategoryName is NOT available on OpportunityHistory — only on Opportunity
const OPPORTUNITY_HISTORY_SOQL_FIELDS =
    'Id, OpportunityId, StageName, Amount, CloseDate, Probability, CreatedDate, CreatedById';

// ---------------------------------------------------------------------------
// Incremental SOQL builder
// ---------------------------------------------------------------------------

/**
 * Builds the full SOQL query for OpportunityHistory.
 *
 * History records are immutable — they have no LastModifiedDate changes after
 * creation. Therefore we filter by CreatedDate for incremental syncs (HIST-02).
 *
 * ORDER BY is required for stage velocity derivation (HIST-03): downstream
 * analysis depends on records being in chronological order per opportunity.
 *
 * @param lastSyncDate - If provided, adds `AND CreatedDate > {date}` to filter
 *                       only records created since the last sync run.
 */
function buildOpportunityHistoryQuery(lastSyncDate?: Date): string {
    const baseWhere = 'WHERE IsDeleted = false';
    const incrementalClause =
        lastSyncDate !== undefined
            ? ` AND CreatedDate > ${lastSyncDate.toISOString()}`
            : '';
    const orderBy = 'ORDER BY OpportunityId, CreatedDate ASC';

    return `SELECT ${OPPORTUNITY_HISTORY_SOQL_FIELDS} FROM OpportunityHistory ${baseWhere}${incrementalClause} ${orderBy}`;
}

// ---------------------------------------------------------------------------
// Sync definition
// ---------------------------------------------------------------------------

const sync = createSync({
    description: 'Fetches Salesforce OpportunityHistory records for stage velocity analysis.',
    version: '1.0.0',
    endpoints: [{ method: 'GET', path: '/salesforce/opportunity-history', group: 'OpportunityHistory' }],
    frequency: 'every hour',
    autoStart: true,
    syncType: 'incremental',

    metadata: z.void(),
    models: {
        OpportunityHistory: opportunityHistorySchema
    },

    exec: async (nango) => {
        // lastSyncDate is a property (Date | undefined) — no function call needed
        const soql = buildOpportunityHistoryQuery(nango.lastSyncDate);

        for await (const batch of nango.paginate({
            endpoint: queryEndpoint(soql),
            paginate: salesforcePaginationConfig,
            retries: 3
        })) {
            // Normalise each record by adding the lowercase `id` key required by Nango.
            const records: OpportunityHistory[] = batch.map((record: unknown) => {
                const raw = record as Record<string, unknown>;
                return opportunityHistorySchema.parse({ ...raw, id: raw['Id'] });
            });

            if (records.length > 0) {
                await nango.batchSave(records, 'OpportunityHistory');
                await nango.log(`Saved ${records.length} opportunity history records`);
            }
        }
    }
});

export type NangoSyncLocal = Parameters<(typeof sync)['exec']>[0];
export default sync;
