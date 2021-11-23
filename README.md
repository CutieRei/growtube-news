# GrowTube News

A Discord news bot for GrowTube Production

## How to setup

Clone this repository

```console
$ git clone https://github.com/ReyterYT/growtube-news.git
```

Install dependencies with poetry (you need to have poetry installed)
```console
$ poetry install -E pg
```

If you can't or don't use asyncpg you can install without the `-E pg` flag

Configure `config.json` if the file does not exist, it will use `default-config.json` instead


## How to run

For Windows:

```console
$ python3 main.py
```

Because due to issue with click coloured output on windows

Linux/MacOS:

```console
$ uvicorn server:app
```

## Setup Database

Run this in your database

```sql
CREATE TABLE "channels" (
"guild" BIGINT NOT NULL,
"type" SMALLINT NOT NULL,
"channel" BIGINT NOT NULL,
"webhook" BIGINT NOT NULL,
"token" VARCHAR(68) NOT NULL);
```

postgresql database url example is in `default-config.json`
