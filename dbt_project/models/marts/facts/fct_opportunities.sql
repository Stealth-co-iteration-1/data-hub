{{
    config(
        materialized='table'
    )
}}

-- Fact table: one row per opportunity
-- Grain: opportunity (salesforce_id + connection_id)

with opportunities as (
    select * from {{ ref('stg_salesforce__opportunities') }}
),

activities as (
    -- Count activities per opportunity
    select
        what_id as opportunity_id,
        count(*) filter (where true) as total_activities,
        count(*) filter (where subject is not null) as events_count
    from {{ ref('stg_salesforce__events') }}
    where what_id is not null
    group by 1
),

tasks as (
    select
        what_id as opportunity_id,
        count(*) as tasks_count,
        count(*) filter (where is_closed) as completed_tasks_count
    from {{ ref('stg_salesforce__tasks') }}
    where what_id is not null
    group by 1
),

final as (
    select
        -- Keys
        o.salesforce_id,
        o.connection_id,

        -- Dimensions (foreign keys)
        o.account_id,
        o.owner_id,
        o.close_date,

        -- Opportunity attributes
        o.opportunity_name,
        o.opportunity_type,
        o.lead_source,
        o.stage_name,
        o.forecast_category,
        o.probability,
        o.is_closed,
        o.is_won,

        -- Measures
        o.amount,

        -- Calculated fields
        case
            when o.is_won then 'Won'
            when o.is_closed and not o.is_won then 'Lost'
            else 'Open'
        end as opportunity_status,

        -- Days calculations
        case
            when o.close_date is not null and o.created_at is not null
            then o.close_date - o.created_at::date
        end as days_to_close,

        case
            when not o.is_closed and o.created_at is not null
            then current_date - o.created_at::date
        end as days_open,

        case
            when not o.is_closed and o.close_date is not null
            then o.close_date - current_date
        end as days_until_close,

        -- Activity metrics
        coalesce(a.total_activities, 0) + coalesce(t.tasks_count, 0) as total_activities,
        coalesce(a.events_count, 0) as events_count,
        coalesce(t.tasks_count, 0) as tasks_count,
        coalesce(t.completed_tasks_count, 0) as completed_tasks_count,

        -- Timestamps
        o.created_at,
        o.updated_at,
        o.synced_at,
        current_timestamp as refreshed_at

    from opportunities o
    left join activities a on o.salesforce_id = a.opportunity_id
    left join tasks t on o.salesforce_id = t.opportunity_id
)

select * from final
