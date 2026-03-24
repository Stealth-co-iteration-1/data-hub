with source as (
    select * from {{ source('salesforce_raw', 'salesforce_accounts') }}
),

renamed as (
    select
        salesforce_id,
        connection_id,

        -- Core fields
        data->>'Name' as account_name,
        data->>'Type' as account_type,
        data->>'Industry' as industry,
        data->>'Description' as description,
        data->>'Website' as website,
        data->>'Phone' as phone,

        -- Financial fields
        (data->>'AnnualRevenue')::numeric as annual_revenue,
        (data->>'NumberOfEmployees')::integer as number_of_employees,

        -- Related IDs
        data->>'OwnerId' as owner_id,
        data->>'ParentId' as parent_account_id,

        -- Address fields
        data->>'BillingCity' as billing_city,
        data->>'BillingState' as billing_state,
        data->>'BillingCountry' as billing_country,

        -- Rating
        data->>'Rating' as rating,

        -- Denormalized related data
        data->'Owner'->>'Name' as owner_name,
        data->'Owner'->>'Email' as owner_email,
        data->'Parent'->>'Name' as parent_account_name,

        -- Timestamps
        (data->>'CreatedDate')::timestamp as created_at,
        (data->>'LastModifiedDate')::timestamp as updated_at,
        synced_at

    from source
)

select * from renamed
