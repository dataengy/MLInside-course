-- feature_mart — ВИТРИНА ПРИЗНАКОВ, стык dbt-мира и ML-мира.
-- Сверху её строит dbt, снизу её читает обучение (ассет training_dataset в Dagster).
--
-- Одна строка = один клиент. Задача игрушечная, но без утечки будущего:
--   · признаки считаются только по заказам ДО даты среза (var cutoff_date);
--   · цель target = 1, если ПОСЛЕ среза клиент сделал ещё хотя бы один заказ.
-- У клиентов без заказов до среза признаки пустые (NULL) — обучающая выборка
-- выбрасывает их через dropna(), ровно как на слайде «Шаг 2».

{% set cutoff = "date '" ~ var('cutoff_date') ~ "'" %}

with customers as (

    select * from {{ ref('customers') }}

),

orders as (

    select * from {{ ref('orders') }}

),

history as (  -- всё, что известно о клиенте на дату среза

    select
        customer_id,
        count(*) as n_orders,
        sum(amount) as total_amount,
        avg(amount) as avg_order_value,
        date_diff('day', max(order_date), {{ cutoff }}) as days_since_last_order,
        avg(case when coupon_amount > 0 then 1 else 0 end) as coupon_share,
        sum(case when status in ('returned', 'return_pending') then 1 else 0 end)::integer as n_returns

    from orders
    where order_date < {{ cutoff }}
    group by customer_id

),

future as (  -- то, что модель должна предсказать

    select distinct customer_id
    from orders
    where order_date >= {{ cutoff }}

),

final as (

    select
        customers.customer_id,
        coalesce(history.n_orders, 0) as n_orders,
        coalesce(history.total_amount, 0) as total_amount,
        history.avg_order_value,
        history.days_since_last_order,
        history.coupon_share,
        coalesce(history.n_returns, 0) as n_returns,
        (future.customer_id is not null)::integer as target,
        -- деление без случайности: каждый пятый клиент уходит в тест
        case when customers.customer_id % 5 = 0 then 'test' else 'train' end as split

    from customers

    left join history
        on customers.customer_id = history.customer_id

    left join future
        on customers.customer_id = future.customer_id

)

select * from final
