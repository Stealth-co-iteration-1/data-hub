{{
    config(
        materialized='table'
    )
}}

-- Generate a date spine from 2020 to 2030
with date_spine as (
    select
        generate_series(
            '2020-01-01'::date,
            '2030-12-31'::date,
            '1 day'::interval
        )::date as date_day
),

enriched as (
    select
        date_day,

        -- Date parts
        extract(year from date_day)::int as year,
        extract(quarter from date_day)::int as quarter,
        extract(month from date_day)::int as month,
        extract(week from date_day)::int as week_of_year,
        extract(day from date_day)::int as day_of_month,
        extract(dow from date_day)::int as day_of_week,
        extract(doy from date_day)::int as day_of_year,

        -- Formatted strings
        to_char(date_day, 'YYYY-MM') as year_month,
        to_char(date_day, 'YYYY-"Q"Q') as year_quarter,
        to_char(date_day, 'Month') as month_name,
        to_char(date_day, 'Mon') as month_name_short,
        to_char(date_day, 'Day') as day_name,
        to_char(date_day, 'Dy') as day_name_short,

        -- Fiscal year (assuming Jan start - adjust if different)
        extract(year from date_day)::int as fiscal_year,
        extract(quarter from date_day)::int as fiscal_quarter,

        -- Flags
        case when extract(dow from date_day) in (0, 6) then true else false end as is_weekend,
        case when extract(dow from date_day) between 1 and 5 then true else false end as is_weekday,

        -- Period boundaries
        date_trunc('week', date_day)::date as week_start_date,
        (date_trunc('week', date_day) + interval '6 days')::date as week_end_date,
        date_trunc('month', date_day)::date as month_start_date,
        (date_trunc('month', date_day) + interval '1 month' - interval '1 day')::date as month_end_date,
        date_trunc('quarter', date_day)::date as quarter_start_date,
        (date_trunc('quarter', date_day) + interval '3 months' - interval '1 day')::date as quarter_end_date,
        date_trunc('year', date_day)::date as year_start_date,
        (date_trunc('year', date_day) + interval '1 year' - interval '1 day')::date as year_end_date,

        -- Relative flags (calculated at query time via current_date)
        case when date_day = current_date then true else false end as is_today,
        case when date_day = current_date - interval '1 day' then true else false end as is_yesterday,
        case when date_day >= date_trunc('week', current_date)
             and date_day < date_trunc('week', current_date) + interval '1 week'
             then true else false end as is_current_week,
        case when date_day >= date_trunc('month', current_date)
             and date_day < date_trunc('month', current_date) + interval '1 month'
             then true else false end as is_current_month,
        case when date_day >= date_trunc('quarter', current_date)
             and date_day < date_trunc('quarter', current_date) + interval '3 months'
             then true else false end as is_current_quarter,
        case when date_day >= date_trunc('year', current_date)
             and date_day < date_trunc('year', current_date) + interval '1 year'
             then true else false end as is_current_year

    from date_spine
)

select * from enriched
