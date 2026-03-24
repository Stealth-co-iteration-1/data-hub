import { createSync } from 'nango';
import * as z from 'zod';
import { queryEndpoint, salesforcePaginationConfig } from '../utils.js';
import { sfId, sfDateTime, sfNullableString, sfNullableNumber } from '../types.js';

// ---------------------------------------------------------------------------
// Nested relationship schemas
// ---------------------------------------------------------------------------

/** Owner (User) fields denormalized onto the Account. */
const ownerSchema = z.object({
    Name: sfNullableString,
    Email: sfNullableString
});

/** Parent Account for account hierarchies. */
const parentAccountSchema = z.object({
    Name: sfNullableString
});

// ---------------------------------------------------------------------------
// Main Account schema (ACCOUNT-01 fields + Nango-required id)
// ---------------------------------------------------------------------------

const accountSchema = z.object({
    // Nango record key (maps from Salesforce Id in exec)
    id: sfId,

    // Core fields
    Id: sfId,
    Name: z.string(),
    Type: sfNullableString,             // Customer, Partner, Prospect, etc.
    Industry: sfNullableString,
    Description: sfNullableString,
    Website: sfNullableString,
    Phone: sfNullableString,

    // Financial fields
    AnnualRevenue: sfNullableNumber,
    NumberOfEmployees: sfNullableNumber,

    // Related IDs
    OwnerId: sfId,
    ParentId: z.union([sfId, z.null()]),

    // Billing address
    BillingCity: sfNullableString,
    BillingState: sfNullableString,
    BillingCountry: sfNullableString,

    // Account rating/status
    Rating: sfNullableString,           // Hot, Warm, Cold

    // Timestamps
    CreatedDate: sfDateTime,
    LastModifiedDate: sfDateTime,

    // Relationship objects
    Owner: ownerSchema,
    Parent: z.union([parentAccountSchema, z.null()])
});

type Account = z.infer<typeof accountSchema>;

// ---------------------------------------------------------------------------
// SOQL field list (custom — buildQuery doesn't support relationship traversal)
// ---------------------------------------------------------------------------

const ACCOUNT_SOQL_FIELDS = `
    Id, Name, Type, Industry, Description, Website, Phone,
    AnnualRevenue, NumberOfEmployees,
    OwnerId, ParentId,
    BillingCity, BillingState, BillingCountry,
    Rating, CreatedDate, LastModifiedDate,
    Owner.Name, Owner.Email,
    Parent.Name
`.replace(/\s+/g, ' ').trim();

// ---------------------------------------------------------------------------
// Incremental SOQL builder
// ---------------------------------------------------------------------------

/**
 * Builds the full SOQL query for Accounts.
 *
 * When `lastSyncDate` is provided, adds a `WHERE LastModifiedDate > {date}` clause
 * so the sync only fetches records changed since the last run.
 */
function buildAccountQuery(lastSyncDate?: Date): string {
    const base = `SELECT ${ACCOUNT_SOQL_FIELDS} FROM Account`;
    if (lastSyncDate !== undefined) {
        return `${base} WHERE LastModifiedDate > ${lastSyncDate.toISOString()}`;
    }
    return base;
}

// ---------------------------------------------------------------------------
// Sync definition
// ---------------------------------------------------------------------------

const sync = createSync({
    description: 'Fetches Salesforce Account records with Owner and Parent relationships.',
    version: '1.0.0',
    endpoints: [{ method: 'GET', path: '/salesforce/accounts', group: 'Accounts' }],
    frequency: 'every hour',
    autoStart: true,
    syncType: 'incremental',

    metadata: z.void(),
    models: {
        Account: accountSchema
    },

    exec: async (nango) => {
        const soql = buildAccountQuery(nango.lastSyncDate);

        for await (const batch of nango.paginate({
            endpoint: queryEndpoint(soql),
            paginate: salesforcePaginationConfig,
            retries: 3
        })) {
            const accounts: Account[] = batch.map((record: unknown) => {
                const raw = record as Record<string, unknown>;
                return accountSchema.parse({ ...raw, id: raw['Id'] });
            });

            if (accounts.length > 0) {
                await nango.batchSave(accounts, 'Account');
                await nango.log(`Saved ${accounts.length} accounts`);
            }
        }
    }
});

export type NangoSyncLocal = Parameters<(typeof sync)['exec']>[0];
export default sync;
