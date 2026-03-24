{{
    config(
        materialized='table'
    )
}}

-- Contact dimension - Email is the universal join key for activity attribution
with contacts as (
    select * from {{ ref('stg_salesforce__contacts') }}
)

select
    salesforce_id as contact_id,
    first_name,
    last_name,
    first_name || ' ' || last_name as full_name,
    email,  -- *** PRIMARY JOIN KEY for attribution ***
    phone,
    mobile_phone,
    title,
    department,
    account_id,
    account_name,
    lead_source,
    mailing_city,
    mailing_state,
    mailing_country,
    owner_id,
    owner_name,
    created_at,
    updated_at,
    current_timestamp as refreshed_at
from contacts
