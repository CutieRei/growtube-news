CREATE TABLE channels (
    'guild' bigint NOT NULL,
    'type' smallint NOT NULL,
    'channel' bigint NOT NULL,
    'webhook' bigint NOT NULL,
    'token' VARCHAR(68) NOT NULL
);

CREATE TABLE inventory (
    'item_id' bigint NOT NULL,
    'user_id' bigint NOT NULL,
    'quantity' bigint DEFAULT 1
);

CREATE TABLE items (
    'id' bigint NOT NULL PRIMARY KEY,
    'name' VARCHAR(64) NOT NULL,
    'value' bigint NOT NULL,
    'supply' bigint DEFAULT 0,
    'demand' bigint DEFAULT 0,
    'stock' bigint DEFAULT 0
);

CREATE TABLE users (
    'id' bigint NOT NULL PRIMARY KEY,
    'currency' bigint NOT NULL
);

ALTER TABLE inventory
ADD CONSTRAINT inventory_item_id_items_id FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE;

ALTER TABLE inventory
ADD CONSTRAINT inventory_user_id_users_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;