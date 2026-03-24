import { createSync } from 'nango';
import * as z from 'zod';
import { queryEndpoint, salesforcePaginationConfig } from '../utils.js';
import { sfId, sfDateTime, sfNullableString } from '../types.js';

// ---------------------------------------------------------------------------
// Nested relationship schemas
// ---------------------------------------------------------------------------

/** Manager (User) fields for reporting hierarchy. */
const managerSchema = z.object({
    Name: sfNullableString,
    Email: sfNullableString
});

/** Profile fields for role/permission context. */
const profileSchema = z.object({
    Name: sfNullableString
});

// ---------------------------------------------------------------------------
// Main User schema (USER-01 fields + Nango-required id)
// ---------------------------------------------------------------------------
// User records are essential for rep attribution and owner lookups.
// Owner.Email on Opportunity/Task/Event joins back to User.Email.
// ---------------------------------------------------------------------------

const userSchema = z.object({
    // Nango record key (maps from Salesforce Id in exec)
    id: sfId,

    // Core fields
    Id: sfId,
    Name: z.string(),
    FirstName: sfNullableString,
    LastName: z.string(),
    Email: z.string(),                  // *** JOIN KEY for rep identity across tools ***
    Username: z.string(),
    Alias: sfNullableString,
    Title: sfNullableString,
    Department: sfNullableString,
    Division: sfNullableString,
    CompanyName: sfNullableString,

    // Status fields
    IsActive: z.boolean(),

    // Related IDs
    ManagerId: z.union([sfId, z.null()]),
    ProfileId: sfId,
    UserRoleId: z.union([sfId, z.null()]),

    // Timestamps
    CreatedDate: sfDateTime,
    LastModifiedDate: sfDateTime,
    LastLoginDate: z.union([sfDateTime, z.null()]),

    // Relationship objects
    Manager: z.union([managerSchema, z.null()]),
    Profile: z.union([profileSchema, z.null()])
});

type User = z.infer<typeof userSchema>;

// ---------------------------------------------------------------------------
// SOQL field list (custom — buildQuery doesn't support relationship traversal)
// ---------------------------------------------------------------------------

const USER_SOQL_FIELDS = `
    Id, Name, FirstName, LastName, Email, Username, Alias, Title,
    Department, Division, CompanyName, IsActive,
    ManagerId, ProfileId, UserRoleId,
    CreatedDate, LastModifiedDate, LastLoginDate,
    Manager.Name, Manager.Email,
    Profile.Name
`.replace(/\s+/g, ' ').trim();

// ---------------------------------------------------------------------------
// Incremental SOQL builder
// ---------------------------------------------------------------------------

/**
 * Builds the full SOQL query for Users.
 *
 * When `lastSyncDate` is provided, adds a `WHERE LastModifiedDate > {date}` clause
 * so the sync only fetches records changed since the last run.
 */
function buildUserQuery(lastSyncDate?: Date): string {
    const base = `SELECT ${USER_SOQL_FIELDS} FROM User`;
    if (lastSyncDate !== undefined) {
        return `${base} WHERE LastModifiedDate > ${lastSyncDate.toISOString()}`;
    }
    return base;
}

// ---------------------------------------------------------------------------
// Sync definition
// ---------------------------------------------------------------------------

const sync = createSync({
    description: 'Fetches Salesforce User records with Manager and Profile relationships. User.Email is the join key for rep identity across tools.',
    version: '1.0.0',
    endpoints: [{ method: 'GET', path: '/salesforce/users', group: 'Users' }],
    frequency: 'every day',             // Users change less frequently
    autoStart: true,
    syncType: 'incremental',

    metadata: z.void(),
    models: {
        User: userSchema
    },

    exec: async (nango) => {
        const soql = buildUserQuery(nango.lastSyncDate);

        for await (const batch of nango.paginate({
            endpoint: queryEndpoint(soql),
            paginate: salesforcePaginationConfig,
            retries: 3
        })) {
            const users: User[] = batch.map((record: unknown) => {
                const raw = record as Record<string, unknown>;
                return userSchema.parse({ ...raw, id: raw['Id'] });
            });

            if (users.length > 0) {
                await nango.batchSave(users, 'User');
                await nango.log(`Saved ${users.length} users`);
            }
        }
    }
});

export type NangoSyncLocal = Parameters<(typeof sync)['exec']>[0];
export default sync;
