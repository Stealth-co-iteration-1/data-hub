with source as (
    select * from {{ source('salesforce_raw', 'salesforce_opportunity_history') }}
),

renamed as (
    select
        salesforce_id,
        connection_id,

        -- Core fields
        data->>'OpportunityId' as opportunity_id,
        data->>'StageName' as stage_name,
        (data->>'Amount')::numeric as amount,
        (data->>'Probability')::numeric as probability,
        data->>'ForecastCategory' as forecast_category,

        -- Timestamps
        (data->>'CreatedDate')::timestamp as created_at,
        (data->>'CloseDate')::date as close_date,
        synced_at

    from source
)

select * from renamed
