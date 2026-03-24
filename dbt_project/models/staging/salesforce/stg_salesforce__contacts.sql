with source as (
    select * from {{ source('salesforce_raw', 'salesforce_contacts') }}
),

renamed as (
    select
        salesforce_id,
        connection_id,

        -- Core fields
        data->>'FirstName' as first_name,
        data->>'LastName' as last_name,
        data->>'Email' as email,  -- *** PRIMARY JOIN KEY for attribution ***
        data->>'Phone' as phone,
        data->>'MobilePhone' as mobile_phone,
        data->>'Title' as title,
        data->>'Department' as department,

        -- Related IDs
        data->>'AccountId' as account_id,
        data->>'OwnerId' as owner_id,

        -- Address fields
        data->>'MailingCity' as mailing_city,
        data->>'MailingState' as mailing_state,
        data->>'MailingCountry' as mailing_country,

        -- Lead source
        data->>'LeadSource' as lead_source,

        -- Denormalized related data
        data->'Account'->>'Name' as account_name,
        data->'Owner'->>'Name' as owner_name,
        data->'Owner'->>'Email' as owner_email,

        -- Timestamps
        (data->>'CreatedDate')::timestamp as created_at,
        (data->>'LastModifiedDate')::timestamp as updated_at,
        synced_at

    from source
)

select * from renamed
