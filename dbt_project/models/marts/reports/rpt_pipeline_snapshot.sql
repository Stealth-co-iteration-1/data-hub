{{
    config(
        materialized='table'
    )
}}

-- Report: Current pipeline snapshot by stage and time horizon
-- Answers: "What's our pipeline health? What's closing soon?"

with opportunities as (
    select
        salesforce_id,
        stage_name,
        amount,
        close_date,
        days_until_close,
        is_closed,
        probability,
        forecast_category
    from {{ ref('fct_opportunities') }}
    where not is_closed  -- Only open opportunities
),

time_buckets as (
    select
        *,
        case
            when days_until_close < 0 then 'Overdue'
            when days_until_close between 0 and 7 then 'This Week'
            when days_until_close between 8 and 30 then 'This Month'
            when days_until_close between 31 and 90 then 'This Quarter'
            else 'Future'
        end as close_time_bucket
    from opportunities
),

by_stage as (
    select
        stage_name,
        count(*) as opportunity_count,
        sum(amount) as total_amount,
        avg(amount) as avg_amount,
        avg(probability) as avg_probability,
        sum(amount * probability / 100) as weighted_amount
    from opportunities
    group by 1
),

by_time as (
    select
        close_time_bucket,
        count(*) as opportunity_count,
        sum(amount) as total_amount,
        sum(amount * probability / 100) as weighted_amount
    from time_buckets
    group by 1
),

totals as (
    select
        count(*) as total_open_opportunities,
        sum(amount) as total_pipeline,
        sum(amount * probability / 100) as total_weighted_pipeline,
        avg(probability) as avg_probability
    from opportunities
)

-- Stage breakdown
select
    'by_stage' as report_section,
    stage_name as dimension,
    opportunity_count,
    round(total_amount::numeric, 2) as total_amount,
    round(avg_amount::numeric, 2) as avg_amount,
    round(avg_probability::numeric, 1) as avg_probability,
    round(weighted_amount::numeric, 2) as weighted_amount,
    current_timestamp as refreshed_at
from by_stage

union all

-- Time horizon breakdown
select
    'by_close_date' as report_section,
    close_time_bucket as dimension,
    opportunity_count,
    round(total_amount::numeric, 2) as total_amount,
    null as avg_amount,
    null as avg_probability,
    round(weighted_amount::numeric, 2) as weighted_amount,
    current_timestamp as refreshed_at
from by_time

union all

-- Totals
select
    'total' as report_section,
    'All Open Pipeline' as dimension,
    total_open_opportunities as opportunity_count,
    round(total_pipeline::numeric, 2) as total_amount,
    null as avg_amount,
    round(avg_probability::numeric, 1) as avg_probability,
    round(total_weighted_pipeline::numeric, 2) as weighted_amount,
    current_timestamp as refreshed_at
from totals
