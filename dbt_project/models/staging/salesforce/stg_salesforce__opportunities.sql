with source as (
    select * from {{ source('salesforce_raw', 'salesforce_opportunities') }}
),

renamed as (
    select
        salesforce_id,
        connection_id,

        -- Core fields
        data->>'Name' as opportunity_name,
        (data->>'Amount')::numeric as amount,
        data->>'StageName' as stage_name,
        (data->>'CloseDate')::date as close_date,
        (data->>'IsClosed')::boolean as is_closed,
        (data->>'IsWon')::boolean as is_won,
        (data->>'Probability')::numeric as probability,
        data->>'Type' as opportunity_type,
        data->>'LeadSource' as lead_source,
        data->>'ForecastCategoryName' as forecast_category,
        data->>'Description' as description,

        -- Related IDs
        data->>'AccountId' as account_id,
        data->>'OwnerId' as owner_id,
        data->>'CampaignId' as campaign_id,

        -- Denormalized related data (from Nango sync)
        data->'Account'->>'Name' as account_name,
        data->'Account'->>'Industry' as account_industry,
        data->'Owner'->>'Name' as owner_name,

        -- Timestamps
        (data->>'CreatedDate')::timestamp as created_at,
        (data->>'LastModifiedDate')::timestamp as updated_at,
        synced_at

    from source
)

select * from renamed
