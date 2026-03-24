{{
    config(
        materialized='table'
    )
}}

-- Owner/Rep dimension from the dedicated users staging model
with users as (
    select * from {{ ref('stg_salesforce__users') }}
)

select
    salesforce_id as owner_id,
    full_name as owner_name,
    first_name,
    last_name,
    email,
    username,
    title,
    department,
    division,
    is_active,
    manager_id,
    manager_name,
    manager_email,
    profile_name,
    last_login_at,
    created_at,
    updated_at,
    current_timestamp as refreshed_at
from users
