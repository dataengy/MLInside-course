with source as (

    {#-
    В оригинальном jaffle shop здесь ref('raw_payments') — seed.
    В демо сырьё грузит Dagster, поэтому это source: ключ его ассета указан в _sources.yml.
    #}
    select * from {{ source('jaffle_raw', 'raw_payments') }}

),

renamed as (

    select
        id as payment_id,
        order_id,
        payment_method,

        -- `amount` is currently stored in cents, so we convert it to dollars
        amount / 100 as amount

    from source

)

select * from renamed
