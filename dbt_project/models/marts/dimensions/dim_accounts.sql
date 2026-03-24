{{
    config(
        materialized='table'
    )
}}

-- Account dimension from the dedicated accounts staging model
with accounts as (
    select * from {{ ref('stg_salesforce__accounts') }}
)

select
    salesforce_id as account_id,
    account_name,
    account_type,
    industry,
    website,
    phone,
    annual_revenue,
    number_of_employees,
    rating,
    billing_city,
    billing_state,
    billing_country,
    parent_account_id,
    parent_account_name,
    owner_id,
    owner_name,
    created_at,
    updated_at,
    current_timestamp as refreshed_at
from accounts
