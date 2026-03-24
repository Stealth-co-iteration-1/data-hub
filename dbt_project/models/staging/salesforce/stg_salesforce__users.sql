with source as (
    select * from {{ source('salesforce_raw', 'salesforce_users') }}
),

renamed as (
    select
        salesforce_id,
        connection_id,

        -- Core fields
        data->>'Name' as full_name,
        data->>'FirstName' as first_name,
        data->>'LastName' as last_name,
        data->>'Email' as email,  -- *** JOIN KEY for rep identity across tools ***
        data->>'Username' as username,
        data->>'Alias' as alias,
        data->>'Title' as title,
        data->>'Department' as department,
        data->>'Division' as division,
        data->>'CompanyName' as company_name,

        -- Status
        (data->>'IsActive')::boolean as is_active,

        -- Related IDs
        data->>'ManagerId' as manager_id,
        data->>'ProfileId' as profile_id,
        data->>'UserRoleId' as user_role_id,

        -- Denormalized related data
        data->'Manager'->>'Name' as manager_name,
        data->'Manager'->>'Email' as manager_email,
        data->'Profile'->>'Name' as profile_name,

        -- Timestamps
        (data->>'CreatedDate')::timestamp as created_at,
        (data->>'LastModifiedDate')::timestamp as updated_at,
        (data->>'LastLoginDate')::timestamp as last_login_at,
        synced_at

    from source
)

select * from renamed
