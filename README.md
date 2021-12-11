# GrowTube News

A Discord news bot for GrowTube Production

## How to setup

Install poetry

```console
pip3 install poetry
```

Clone this repository

```console
git clone https://github.com/ReyterYT/growtube-news.git
```

Create venv and activate it(Optional but recommended)

```console
python3 -m virtualenv venv
```

Linux

```console
. venv/bin/activate
```

or

```console
source venv/bin/activate
```

Windows Powershell

```console
venv\Scripts\activate.ps1
```

Install dependencies with poetry

```console
poetry install -E pg
```

If you can't or don't use asyncpg you can install without the `-E pg` flag

Configure `config.json`, if the file does not exist it will use `default-config.json` instead

> config.json format are the same as default-config.json

## How to run

```console
python run.py
```

## Setup Database

SQL schema is in `schema.sql`

postgresql database url example is in `default-config.json`
