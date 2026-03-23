{{
    config(
        materialized='table'
    )
}}

-- Extract unique owners from opportunities
with opportunity_owners as (
    select distinct
        owner_id,
        owner_name
    from {{ ref('stg_salesforce__opportunities') }}
    where owner_id is not null
),

-- Could add more owner sources here (tasks, events) if needed
all_owners as (
    select * from opportunity_owners
)

select
    owner_id,
    owner_name,
    current_timestamp as refreshed_at
from all_owners
