"""Feed Recommend module — rule-based restaurant discovery.

Owns:
- Restaurant dataset loading from ``data/restaurants.json`` (in-memory cache).
- Scoring (distance + quality + price fit + taste match against the user's
  existing food profile).
- Per-user persistence (saved / seen / location).
- The ``/api/v1/feed`` HTTP surface.

This module deliberately has no concept of "Restaurants" as a database table
— the dataset is read-only product data and lives in JSON so a content edit
+ restart is all that's needed to ship new rows. Per-user state references
restaurants by integer ``source_id``; the service validates every reference
against the in-memory cache.
"""
