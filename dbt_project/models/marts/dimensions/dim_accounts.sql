{{
    config(
        materialized='table'
    )
}}

-- Extract unique accounts from opportunities
with opportunity_accounts as (
    select distinct
        account_id,
        account_name,
        account_industry
    from {{ ref('stg_salesforce__opportunities') }}
    where account_id is not null
)

select
    account_id,
    account_name,
    account_industry,
    current_timestamp as refreshed_at
from opportunity_accounts
