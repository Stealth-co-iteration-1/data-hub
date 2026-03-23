{{
    config(
        materialized='table'
    )
}}

-- Report: Sales velocity - how long deals spend in each stage
-- Answers: "Where do deals get stuck?"

with stage_times as (
    select
        current_stage,
        previous_stage,
        days_in_previous_stage
    from {{ ref('fct_opportunity_stages') }}
    where previous_stage is not null
      and days_in_previous_stage is not null
),

stage_metrics as (
    select
        previous_stage as stage_name,
        count(*) as transitions_count,
        avg(days_in_previous_stage) as avg_days_in_stage,
        percentile_cont(0.5) within group (order by days_in_previous_stage) as median_days_in_stage,
        min(days_in_previous_stage) as min_days_in_stage,
        max(days_in_previous_stage) as max_days_in_stage,
        stddev(days_in_previous_stage) as stddev_days
    from stage_times
    group by 1
)

select
    stage_name,
    transitions_count,
    round(avg_days_in_stage::numeric, 1) as avg_days_in_stage,
    round(median_days_in_stage::numeric, 1) as median_days_in_stage,
    round(min_days_in_stage::numeric, 1) as min_days_in_stage,
    round(max_days_in_stage::numeric, 1) as max_days_in_stage,
    round(stddev_days::numeric, 1) as stddev_days,

    -- Flag slow stages (above median + 1 stddev)
    case
        when avg_days_in_stage > (
            select avg(avg_days_in_stage) + stddev(avg_days_in_stage)
            from stage_metrics
        ) then true
        else false
    end as is_bottleneck,

    current_timestamp as refreshed_at
from stage_metrics
order by avg_days_in_stage desc
