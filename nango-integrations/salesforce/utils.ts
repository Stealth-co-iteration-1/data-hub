/**
 * Salesforce sync utilities: SOQL query builder, pagination config, and API constants.
 *
 * Usage in a sync file:
 *   import { buildQuery, queryEndpoint, salesforcePaginationConfig } from '../utils.js';
 *
 *   const soql = buildQuery('Opportunity', ['Id', 'Name', 'Amount'], lastSyncDate);
 *   for await (const batch of nango.paginate({ endpoint: queryEndpoint(soql), paginate: salesforcePaginationConfig })) {
 *     // batch contains the records array from response.records
 *   }
 */

/** Current Salesforce REST API version used across all syncs. */
export const SALESFORCE_API_VERSION = 'v60.0';

/**
 * Pagination config for use with nango.paginate().
 *
 * Salesforce query responses include a `nextRecordsUrl` field when more records
 * are available. This config tells Nango to follow that link automatically.
 *
 * Example:
 *   for await (const batch of nango.paginate({ endpoint: queryEndpoint(soql), paginate: salesforcePaginationConfig })) { ... }
 */
export const salesforcePaginationConfig = {
    link_path_in_response_body: 'nextRecordsUrl'
};

/**
 * Builds a SOQL SELECT query with an optional incremental filter.
 *
 * @param model - Salesforce object API name (e.g. 'Opportunity', 'Task')
 * @param fields - List of field API names to SELECT
 * @param lastSyncDate - If provided, appends a `WHERE LastModifiedDate > {date}` clause for incremental syncs
 * @returns Full SOQL query string
 *
 * Example:
 *   buildQuery('Opportunity', ['Id', 'Name'], new Date('2024-01-01'))
 *   // => "SELECT Id, Name FROM Opportunity WHERE LastModifiedDate > 2024-01-01T00:00:00.000Z"
 */
export function buildQuery(model: string, fields: string[], lastSyncDate?: Date): string {
    const fieldList = fields.join(', ');
    const base = `SELECT ${fieldList} FROM ${model}`;
    if (lastSyncDate !== undefined) {
        return `${base} WHERE LastModifiedDate > ${lastSyncDate.toISOString()}`;
    }
    return base;
}

/**
 * Builds the Salesforce REST API query endpoint URL for a given SOQL string.
 *
 * @param soql - SOQL query string (will be URL-encoded)
 * @returns Relative endpoint path for use in a Nango proxy config
 *
 * Example:
 *   queryEndpoint("SELECT Id FROM Opportunity")
 *   // => "/services/data/v60.0/query?q=SELECT%20Id%20FROM%20Opportunity"
 */
export function queryEndpoint(soql: string): string {
    return `/services/data/${SALESFORCE_API_VERSION}/query?q=${encodeURIComponent(soql)}`;
}
