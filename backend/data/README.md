# Seller mock data

These files are **synthetic demonstration records** for SellerPulse AI. They are not Snapdeal seller extracts, and product-level figures must not be described as marketplace data.

Each file in `sellers/` is one seller context. The API looks sellers up by `seller.seller_id`, not by the file name. The conventional file name is `<seller_id>.json`.

## Records

| File | Seller | What it is for |
| --- | --- | --- |
| `sellers/demo-seller.json` | MetroHome Living, Jaipur | A decline: fewer completed orders, more cancellations, and stock at or below the reorder threshold. |
| `sellers/stable-seller.json` | Northstar Stationery, Pune | A steady seller: similar monthly orders, low cancellations, and stock above the reorder threshold. |

Both sellers are `active`, have at least three products, six months of history (`2026-05` through `2026-10`), and product performance that adds up to the seller snapshot for that month.

Monthly revenue is `selling_price * units_sold` for each product. Cancellation rate and average selling price are not stored. Later calculation steps should derive them from these counts.

## JSON shape

```json
{
  "seller": {
    "seller_id": "demo-seller",
    "business_name": "MetroHome Living",
    "owner_name": "Ananya Sharma",
    "category": "Home & Kitchen",
    "city": "Jaipur",
    "joined_at": "2023-04-18",
    "seller_status": "active"
  },
  "products": [],
  "inventory": [],
  "sales_snapshots": [],
  "product_performance": []
}
```

`seller_status` is `active` or `inactive`. Prices, quantities, order counts, and revenue must be zero or greater. `joined_at` is `YYYY-MM-DD` or omitted. Reporting periods are `YYYY-MM`.

Relationships checked when a file is loaded:

- Every product `seller_id` matches the seller.
- Product ids are unique for that seller.
- Every inventory row and product-performance row uses one of those product ids.

Unknown fields are rejected. A malformed or invalid file stops loading; it is not skipped.

## Add a seller

1. Copy `sellers/stable-seller.json` to `sellers/<new-seller-id>.json`.
2. Change `seller.seller_id` to a new id and update the profile fields.
3. Give every product that same `seller_id` and a unique `product_id`.
4. Point inventory and product performance at those product ids.
5. Keep monthly product revenue and units equal to the seller snapshot for the same `period`.
6. Restart the API. The directory is read once per process and then cached.

Set `SELLER_DATA_DIR` to load this shape from another directory. A relative path is resolved from the process working directory. When the variable is unset, the default is this `sellers/` folder, found from the backend package rather than the shell's current directory.
