# Database — Supabase

Schema + seed data for the Multi-Agent Customer Support System.

## Tables

| Table             | Rows seeded | Purpose                                         |
| ----------------- | ----------- | ----------------------------------------------- |
| `customers`       | 15          | End users of the store                          |
| `orders`          | 15          | One order per customer (FK → `customers`)       |
| `support_tickets` | 15          | One ticket per order (FK → `customers`,`orders`)|

### Relationships

```
customers (1) ──< (many) orders
customers (1) ──< (many) support_tickets
orders    (1) ──< (many) support_tickets   (optional)
```

## How to run in Supabase

1. Open your Supabase project → **SQL Editor** → **New query**.
2. Paste the full contents of `schema.sql`.
3. Click **Run**.
4. Verify counts by uncommenting the verification query at the bottom, or in the **Table Editor** confirm each table shows 15 rows.

> The script begins with `DROP TABLE ... CASCADE` so it's safe to re-run during development. Remove those drops before shipping to production.

## Notes on schema choices

- `orders.total_amount` is a generated column (`quantity * unit_price`) — never out of sync.
- `support_tickets.order_id` is nullable so general-purpose tickets (not tied to an order) are allowed later.
- `CHECK` constraints on `status`, `priority`, `category`, `loyalty_tier` keep the agents' routing logic honest.
- `updated_at` on `support_tickets` is maintained by a trigger (`set_updated_at`).
- Indexes cover the most common agent lookups: by customer, by order, by status.
