{{
    config(
        materialized='table'
    )
}}

-- Report: Win rates by sales rep
-- Answers: "Who are top performers? Who needs coaching?"

with owner_metrics as (
    select
        owner_id,
        count(*) as total_opportunities,
        count(*) filter (where is_closed) as closed_opportunities,
        count(*) filter (where is_won) as won_opportunities,
        count(*) filter (where is_closed and not is_won) as lost_opportunities,
        count(*) filter (where not is_closed) as open_opportunities,

        sum(amount) as total_pipeline,
        sum(amount) filter (where not is_closed) as open_pipeline,
        sum(amount) filter (where is_won) as won_revenue,
        sum(amount) filter (where is_closed and not is_won) as lost_revenue,

        avg(amount) filter (where is_won) as avg_won_deal_size,
        avg(days_to_close) filter (where is_closed) as avg_days_to_close

    from {{ ref('fct_opportunities') }}
    where owner_id is not null
    group by 1
),

with_rates as (
    select
        om.*,
        o.owner_name,

        -- Win rate calculation
        case
            when closed_opportunities > 0
            then round(100.0 * won_opportunities / closed_opportunities, 1)
            else 0
        end as win_rate_pct,

        -- Conversion rate (won / total)
        case
            when total_opportunities > 0
            then round(100.0 * won_opportunities / total_opportunities, 1)
            else 0
        end as conversion_rate_pct

    from owner_metrics om
    left join {{ ref('dim_owners') }} o using (owner_id)
)

select
    owner_id,
    owner_name,
    total_opportunities,
    open_opportunities,
    won_opportunities,
    lost_opportunities,
    win_rate_pct,
    conversion_rate_pct,
    round(open_pipeline::numeric, 2) as open_pipeline,
    round(won_revenue::numeric, 2) as won_revenue,
    round(avg_won_deal_size::numeric, 2) as avg_won_deal_size,
    round(avg_days_to_close::numeric, 1) as avg_days_to_close,

    -- Performance tier
    case
        when win_rate_pct >= 40 then 'High Performer'
        when win_rate_pct >= 25 then 'Average'
        when win_rate_pct > 0 then 'Needs Coaching'
        else 'No Closed Deals'
    end as performance_tier,

    current_timestamp as refreshed_at
from with_rates
order by won_revenue desc nulls last
