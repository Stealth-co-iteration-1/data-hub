{{
    config(
        materialized='table'
    )
}}

-- Report: Activity coverage per opportunity
-- Answers: "Do more activities correlate with higher win rates?"

with opportunity_activities as (
    select
        salesforce_id,
        opportunity_name,
        stage_name,
        amount,
        is_closed,
        is_won,
        opportunity_status,
        total_activities,
        events_count,
        tasks_count,
        days_open,
        owner_id
    from {{ ref('fct_opportunities') }}
),

activity_buckets as (
    select
        *,
        case
            when total_activities = 0 then '0 - No activities'
            when total_activities between 1 and 3 then '1-3 Low'
            when total_activities between 4 and 10 then '4-10 Medium'
            else '11+ High'
        end as activity_bucket
    from opportunity_activities
),

bucket_metrics as (
    select
        activity_bucket,
        count(*) as opportunity_count,
        count(*) filter (where is_closed) as closed_count,
        count(*) filter (where is_won) as won_count,
        sum(amount) as total_pipeline,
        sum(amount) filter (where is_won) as won_revenue,
        avg(amount) as avg_deal_size,
        avg(total_activities) as avg_activities

    from activity_buckets
    group by 1
)

select
    activity_bucket,
    opportunity_count,
    closed_count,
    won_count,
    case
        when closed_count > 0
        then round(100.0 * won_count / closed_count, 1)
        else 0
    end as win_rate_pct,
    round(total_pipeline::numeric, 2) as total_pipeline,
    round(won_revenue::numeric, 2) as won_revenue,
    round(avg_deal_size::numeric, 2) as avg_deal_size,
    round(avg_activities::numeric, 1) as avg_activities,
    current_timestamp as refreshed_at
from bucket_metrics
order by
    case activity_bucket
        when '0 - No activities' then 1
        when '1-3 Low' then 2
        when '4-10 Medium' then 3
        when '11+ High' then 4
    end
