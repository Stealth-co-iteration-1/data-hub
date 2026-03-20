import { createSync } from 'nango';
import * as z from 'zod';
import { queryEndpoint, salesforcePaginationConfig } from '../utils.js';
import { sfId, sfDateTime, sfDate, sfNullableString, sfNullableNumber, sfCurrency, sfPercentage } from '../types.js';

// ---------------------------------------------------------------------------
// Nested relationship schemas
// ---------------------------------------------------------------------------

/** Parent Account fields denormalized onto the Opportunity. */
const accountSchema = z.object({
    Name: sfNullableString,
    Industry: sfNullableString,
    AnnualRevenue: sfNullableNumber
});

/** Owner (User) fields denormalized onto the Opportunity. */
const ownerSchema = z.object({
    Name: sfNullableString,
    Email: sfNullableString
});

/** Contact fields for join key resolution via OpportunityContactRole. */
const contactSchema = z.object({
    Email: sfNullableString
});

/** A single row from the OpportunityContactRoles child relationship. */
const opportunityContactRoleSchema = z.object({
    Id: sfId,
    ContactId: sfId,
    Role: sfNullableString,
    IsPrimary: z.boolean(),
    Contact: contactSchema
});

// ---------------------------------------------------------------------------
// Main Opportunity schema (14 spec fields + 3 relationship objects)
// Nango requires a lowercase `id` field on every model (used as record key).
// We include both the canonical Salesforce `Id` and the required Nango `id`.
// ---------------------------------------------------------------------------

const opportunitySchema = z.object({
    // Nango record key (maps from Salesforce Id in exec)
    id: sfId,

    // Core fields (OPPT-01)
    Id: sfId,
    Name: z.string(),
    Amount: sfCurrency,
    StageName: z.string(),
    IsClosed: z.boolean(),
    IsWon: z.boolean(),
    CloseDate: sfDate,
    CreatedDate: sfDateTime,
    LastModifiedDate: sfDateTime,
    ForecastCategoryName: sfNullableString,
    Probability: sfPercentage,
    Type: sfNullableString,
    LeadSource: sfNullableString,
    OwnerId: sfId,

    // Parent Account (OPPT-02) - null when Opportunity has no linked Account
    Account: z.union([accountSchema, z.null()]),

    // Owner lookup (OPPT-03)
    Owner: ownerSchema,

    // Child OpportunityContactRoles subquery (OPPT-04)
    // Salesforce returns null when there are no related records
    OpportunityContactRoles: z.union([
        z.object({ records: z.array(opportunityContactRoleSchema) }),
        z.null()
    ])
});

type Opportunity = z.infer<typeof opportunitySchema>;

// ---------------------------------------------------------------------------
// SOQL field list (custom — buildQuery doesn't support relationship traversal)
// ---------------------------------------------------------------------------

// Note: buildQuery doesn't support relationship fields, so we build SOQL manually
const OPPORTUNITY_SOQL_FIELDS = `
    Id, Name, Amount, StageName, IsClosed, IsWon, CloseDate,
    CreatedDate, LastModifiedDate, ForecastCategoryName, Probability, Type, LeadSource, OwnerId,
    Account.Name, Account.Industry, Account.AnnualRevenue,
    Owner.Name, Owner.Email,
    (SELECT Id, ContactId, Role, IsPrimary, Contact.Email FROM OpportunityContactRoles)
`.replace(/\s+/g, ' ').trim();

// ---------------------------------------------------------------------------
// Incremental SOQL builder (buildQuery doesn't handle relationship fields)
// ---------------------------------------------------------------------------

/**
 * Builds the full SOQL query for Opportunities.
 *
 * When `lastSyncDate` is provided, adds a `WHERE LastModifiedDate > {date}` clause
 * so the sync only fetches records changed since the last run (OPPT-05).
 */
function buildOpportunityQuery(lastSyncDate?: Date): string {
    const base = `SELECT ${OPPORTUNITY_SOQL_FIELDS} FROM Opportunity`;
    if (lastSyncDate !== undefined) {
        return `${base} WHERE LastModifiedDate > ${lastSyncDate.toISOString()}`;
    }
    return base;
}

// ---------------------------------------------------------------------------
// Sync definition
// ---------------------------------------------------------------------------

const sync = createSync({
    description: 'Fetches Salesforce Opportunity records with Account, Owner, and OpportunityContactRoles relationships.',
    version: '1.0.0',
    endpoints: [{ method: 'GET', path: '/salesforce/opportunities', group: 'Opportunities' }],
    frequency: 'every hour',
    autoStart: true,
    syncType: 'incremental',

    metadata: z.void(),
    models: {
        Opportunity: opportunitySchema
    },

    exec: async (nango) => {
        // lastSyncDate is a property (Date | undefined) — no function call needed
        const soql = buildOpportunityQuery(nango.lastSyncDate);

        for await (const batch of nango.paginate({
            endpoint: queryEndpoint(soql),
            paginate: salesforcePaginationConfig,
            retries: 3
        })) {
            // nango.paginate returns the records array from the Salesforce SOQL response.
            // We normalise each record by adding the lowercase `id` key required by Nango.
            const opportunities: Opportunity[] = batch.map((record: unknown) => {
                const raw = record as Record<string, unknown>;
                return opportunitySchema.parse({ ...raw, id: raw['Id'] });
            });

            if (opportunities.length > 0) {
                await nango.batchSave(opportunities, 'Opportunity');
                await nango.log(`Saved ${opportunities.length} opportunities`);
            }
        }
    }
});

export type NangoSyncLocal = Parameters<(typeof sync)['exec']>[0];
export default sync;
