{{
    config(
        materialized='table'
    )
}}

-- Fact table: stage transitions for opportunities
-- Grain: one row per stage change (from opportunity history)

with history as (
    select * from {{ ref('stg_salesforce__opportunity_history') }}
),

with_previous as (
    select
        salesforce_id,
        connection_id,
        opportunity_id,
        stage_name,
        amount,
        probability,
        created_at,
        close_date,

        -- Get previous stage for this opportunity
        lag(stage_name) over (
            partition by opportunity_id
            order by created_at
        ) as previous_stage,

        -- Get previous timestamp
        lag(created_at) over (
            partition by opportunity_id
            order by created_at
        ) as previous_stage_at,

        -- Stage sequence number
        row_number() over (
            partition by opportunity_id
            order by created_at
        ) as stage_sequence

    from history
),

final as (
    select
        salesforce_id,
        connection_id,
        opportunity_id,

        -- Stage transition
        previous_stage,
        stage_name as current_stage,
        stage_sequence,

        -- Time in previous stage (in days)
        case
            when previous_stage_at is not null
            then extract(epoch from (created_at - previous_stage_at)) / 86400.0
        end as days_in_previous_stage,

        -- Measures at this point
        amount,
        probability,
        close_date,

        -- Timestamps
        previous_stage_at,
        created_at as stage_entered_at,
        current_timestamp as refreshed_at

    from with_previous
)

select * from final
