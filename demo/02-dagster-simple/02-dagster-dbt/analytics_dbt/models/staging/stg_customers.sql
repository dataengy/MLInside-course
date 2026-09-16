with source as (

    {#-
    В оригинальном jaffle shop здесь ref('raw_customers') — seed.
    В демо сырьё грузит Dagster, поэтому это source: ключ его ассета указан в _sources.yml.
    #}
    select * from {{ source('jaffle_raw', 'raw_customers') }}

),

renamed as (

    select
        id as customer_id,
        first_name,
        last_name

    from source

)

select * from renamed
