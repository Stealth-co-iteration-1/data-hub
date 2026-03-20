import { createSync } from 'nango';
import * as z from 'zod';
import { buildQuery, queryEndpoint, salesforcePaginationConfig } from '../utils.js';
import { sfId, sfDateTime, sfDate, sfNullableString, sfNullableNumber, sfNullableBoolean, sfCurrency, sfPercentage } from '../types.js';

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
// ---------------------------------------------------------------------------

const opportunitySchema = z.object({
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
