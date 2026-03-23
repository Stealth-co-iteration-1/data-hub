{{
    config(
        materialized='table'
    )
}}

with opportunities as (
    select * from {{ ref('stg_salesforce__opportunities') }}
),

pipeline_summary as (
    select
        connection_id,
        stage_name,
        is_closed,
        is_won,
        count(*) as opportunity_count,
        sum(amount) as total_amount,
        avg(amount) as avg_amount,
        min(close_date) as earliest_close_date,
        max(close_date) as latest_close_date
    from opportunities
    group by 1, 2, 3, 4
)

select
    connection_id,
    stage_name,
    is_closed,
    is_won,
    opportunity_count,
    total_amount,
    avg_amount,
    earliest_close_date,
    latest_close_date,
    current_timestamp as refreshed_at
from pipeline_summary
