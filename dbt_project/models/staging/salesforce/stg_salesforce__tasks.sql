with source as (
    select * from {{ source('salesforce_raw', 'salesforce_tasks') }}
),

renamed as (
    select
        salesforce_id,
        connection_id,

        -- Core fields
        data->>'Subject' as subject,
        data->>'Description' as description,
        data->>'Status' as status,
        data->>'Priority' as priority,
        data->>'TaskSubtype' as task_subtype,

        -- Timing
        (data->>'ActivityDate')::date as activity_date,
        (data->>'ReminderDateTime')::timestamp as reminder_at,
        (data->>'IsHighPriority')::boolean as is_high_priority,
        (data->>'IsClosed')::boolean as is_closed,

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
