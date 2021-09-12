# GrowTube News

A Discord news bot for GrowTube Production

## How to setup

Clone this repository

```bash
git clone https://github.com/ReyterYT/growtube-news.git
```

Install dependencies with poetry

```bash
poetry install
```

If you're having trouble with installing `discord.py` you should install it manually

```bash
pip install git+https://github.com/Rapptz/discord.py
```

Configure `config.json` if the file does not exist, it will use `default-config.json` instead

**Important**: If you are running outside of replit environment or does not have the replit database url you should change `bot.py` line 25 with `DB()` or any other async storage in `storage.py`, you can even make your own storage class

## How to run

For Windows:

```bat
python3 main.py
```

Because due to issue with click coloured output on windows

For any other OS:

```bash
uvicorn server:app
```
