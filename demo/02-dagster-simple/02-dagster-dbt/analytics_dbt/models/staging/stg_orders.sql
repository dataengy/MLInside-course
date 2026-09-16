with source as (

    {#-
    В оригинальном jaffle shop здесь ref('raw_orders') — seed.
    В демо сырьё грузит Dagster, поэтому это source: ключ его ассета указан в _sources.yml.
    #}
    select * from {{ source('jaffle_raw', 'raw_orders') }}

),

renamed as (

    select
        id as order_id,
        user_id as customer_id,
        order_date,
        status

    from source

)

select * from renamed
