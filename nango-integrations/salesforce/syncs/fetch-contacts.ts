import { createSync } from 'nango';
import * as z from 'zod';
import { queryEndpoint, salesforcePaginationConfig } from '../utils.js';
import { sfId, sfDateTime, sfNullableString } from '../types.js';

// ---------------------------------------------------------------------------
// Nested relationship schemas
// ---------------------------------------------------------------------------

/** Account fields denormalized onto the Contact. */
const accountSchema = z.object({
    Name: sfNullableString,
    Industry: sfNullableString
});

/** Owner (User) fields denormalized onto the Contact. */
const ownerSchema = z.object({
    Name: sfNullableString,
    Email: sfNullableString
});

// ---------------------------------------------------------------------------
// Main Contact schema (CONTACT-01 fields + Nango-required id)
// ---------------------------------------------------------------------------
// Contact.Email is the universal join key for activity attribution per spec.
// ---------------------------------------------------------------------------

const contactSchema = z.object({
    // Nango record key (maps from Salesforce Id in exec)
    id: sfId,

    // Core fields
    Id: sfId,
    FirstName: sfNullableString,
    LastName: z.string(),               // Required in Salesforce
    Email: sfNullableString,            // *** PRIMARY JOIN KEY for attribution ***
    Phone: sfNullableString,
    MobilePhone: sfNullableString,
    Title: sfNullableString,
    Department: sfNullableString,

    // Related IDs
    AccountId: z.union([sfId, z.null()]),
    OwnerId: sfId,

    // Mailing address fields
    MailingCity: sfNullableString,
    MailingState: sfNullableString,
    MailingCountry: sfNullableString,

    // Lead source tracking
    LeadSource: sfNullableString,

    // Timestamps
    CreatedDate: sfDateTime,
    LastModifiedDate: sfDateTime,

    // Relationship objects
    Account: z.union([accountSchema, z.null()]),
    Owner: ownerSchema
});

type Contact = z.infer<typeof contactSchema>;

// ---------------------------------------------------------------------------
// SOQL field list (custom — buildQuery doesn't support relationship traversal)
// ---------------------------------------------------------------------------

const CONTACT_SOQL_FIELDS = `
    Id, FirstName, LastName, Email, Phone, MobilePhone, Title, Department,
    AccountId, OwnerId, MailingCity, MailingState, MailingCountry, LeadSource,
    CreatedDate, LastModifiedDate,
    Account.Name, Account.Industry,
    Owner.Name, Owner.Email
`.replace(/\s+/g, ' ').trim();

// ---------------------------------------------------------------------------
// Incremental SOQL builder
// ---------------------------------------------------------------------------

/**
 * Builds the full SOQL query for Contacts.
 *
 * When `lastSyncDate` is provided, adds a `WHERE LastModifiedDate > {date}` clause
 * so the sync only fetches records changed since the last run.
 */
function buildContactQuery(lastSyncDate?: Date): string {
    const base = `SELECT ${CONTACT_SOQL_FIELDS} FROM Contact`;
    if (lastSyncDate !== undefined) {
        return `${base} WHERE LastModifiedDate > ${lastSyncDate.toISOString()}`;
    }
    return base;
}

// ---------------------------------------------------------------------------
// Sync definition
// ---------------------------------------------------------------------------

const sync = createSync({
    description: 'Fetches Salesforce Contact records with Account and Owner relationships. Contact.Email is the universal join key for activity attribution.',
    version: '1.0.0',
    endpoints: [{ method: 'GET', path: '/salesforce/contacts', group: 'Contacts' }],
    frequency: 'every hour',
    autoStart: true,
    syncType: 'incremental',

    metadata: z.void(),
    models: {
        Contact: contactSchema
    },

    exec: async (nango) => {
        const soql = buildContactQuery(nango.lastSyncDate);

        for await (const batch of nango.paginate({
            endpoint: queryEndpoint(soql),
            paginate: salesforcePaginationConfig,
            retries: 3
        })) {
            const contacts: Contact[] = batch.map((record: unknown) => {
                const raw = record as Record<string, unknown>;
                return contactSchema.parse({ ...raw, id: raw['Id'] });
            });

            if (contacts.length > 0) {
                await nango.batchSave(contacts, 'Contact');
                await nango.log(`Saved ${contacts.length} contacts`);
            }
        }
    }
});

export type NangoSyncLocal = Parameters<(typeof sync)['exec']>[0];
export default sync;
