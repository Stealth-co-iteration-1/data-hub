with source as (
    select * from {{ source('salesforce_raw', 'salesforce_events') }}
),

renamed as (
    select
        salesforce_id,
        connection_id,

        -- Core fields
        data->>'Subject' as subject,
        data->>'Description' as description,
        data->>'Location' as location,
        (data->>'IsAllDayEvent')::boolean as is_all_day,

        -- Timing
        (data->>'StartDateTime')::timestamp as starts_at,
        (data->>'EndDateTime')::timestamp as ends_at,
        (data->>'DurationInMinutes')::int as duration_minutes,

        -- Related IDs
        data->>'WhoId' as who_id,
        data->>'WhatId' as what_id,
        data->>'OwnerId' as owner_id,
        data->>'AccountId' as account_id,

        -- Timestamps
        (data->>'CreatedDate')::timestamp as created_at,
        (data->>'LastModifiedDate')::timestamp as updated_at,
        synced_at

    from source
)

select * from renamed
