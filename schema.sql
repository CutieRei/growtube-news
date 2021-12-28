CREATE TABLE "channels" (
"guild" BIGINT NOT NULL,
"type" SMALLINT NOT NULL,
"channel" BIGINT NOT NULL,
"webhook" BIGINT NOT NULL,
"token" VARCHAR(68) NOT NULL);

CREATE TABLE "items" (
"id" BIGINT NOT NULL UNIQUE PRIMARY KEY,
"name" VARCHAR(64) NOT NULL,
"value" BIGINT NOT NULL,
"demand" BIGINT NOT NULL,
"supply" BIGINT NOT NULL,
"stock" BIGINT NOT NULL);

CREATE TABLE "inventory" (
"item_id" BIGINT NOT NULL,
"user_id" BIGINT NOT NULL,
"quantity" BIGINT NOT NULL);

CREATE TABLE "users" (
"id" BIGINT NOT NULL UNIQUE PRIMARY KEY,
"currency" BIGINT NOT NULL,
"career" BIGINT,
"time_remaining" BIGINT,
"position" BIGINT);

CREATE TABLE "careers" (
"id" BIGINT NOT NULL PRIMARY KEY,
"name" TEXT NOT NULL);

CREATE TABLE "positions" (
"career" BIGINT NOT NULL,
"privilege" BIGINT NOT NULL,
"pay" BIGINT NOT NULL,
"name" TEXT NOT NULL,
"id" BIGINT NOT NULL PRIMARY KEY,
"duration" BIGINT NOT NULL);

ALTER TABLE "inventory" ADD CONSTRAINT "inventory_item_id_items_id" FOREIGN KEY ("item_id") REFERENCES "items"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

ALTER TABLE "inventory" ADD CONSTRAINT "inventory_user_id_users_id" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

ALTER TABLE "users" ADD CONSTRAINT "users_career_careers_id" FOREIGN KEY ("career") REFERENCES "careers"("id") ON DELETE SET DEFAULT ON UPDATE NO ACTION;

ALTER TABLE "users" ADD CONSTRAINT "users_position_positions_id" FOREIGN KEY ("position") REFERENCES "positions"("id") ON DELETE SET DEFAULT ON UPDATE NO ACTION;

ALTER TABLE "positions" ADD CONSTRAINT "positions_career_careers_id" FOREIGN KEY ("career") REFERENCES "careers"("id") ON DELETE CASCADE ON UPDATE NO ACTION;