{{
    config(
        materialized='table'
    )
}}

-- Fact table: all sales activities (events + tasks unified)
-- Grain: one row per activity

with events as (
    select
        salesforce_id,
        connection_id,
        'event' as activity_type,
        subject,
        description,
        who_id,
        what_id,
        owner_id,
        account_id,
        starts_at as activity_at,
        duration_minutes,
        is_all_day,
        null::boolean as is_completed,
        null::text as status,
        null::text as priority,
        created_at,
        updated_at,
        synced_at
    from {{ ref('stg_salesforce__events') }}
),

tasks as (
    select
        salesforce_id,
        connection_id,
        'task' as activity_type,
        subject,
        description,
        who_id,
        what_id,
        owner_id,
        account_id,
        activity_date::timestamp as activity_at,
        null::int as duration_minutes,
        false as is_all_day,
        is_closed as is_completed,
        status,
        priority,
        created_at,
        updated_at,
        synced_at
    from {{ ref('stg_salesforce__tasks') }}
),

unioned as (
    select * from events
    union all
    select * from tasks
),

final as (
    select
        salesforce_id,
        connection_id,
        activity_type,
        subject,
        description,

        -- Related entities
        who_id,
        what_id,
        owner_id,
        account_id,

        -- Activity details
        activity_at,
        activity_at::date as activity_date,
        duration_minutes,
        is_all_day,
        is_completed,
        status,
        priority,

        -- Timestamps
        created_at,
        updated_at,
        synced_at,
        current_timestamp as refreshed_at

    from unioned
)

select * from final
