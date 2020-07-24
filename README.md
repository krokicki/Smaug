# [Smaug](http://github.com/krokicki/smaug)

Smaug is a chat bot for simultaneous deployment on multiple protocols. He aims to bridge various chat protocols by providing a unified logging view and tunneling mechanism. There are also various plugins available to do some useful stuff.

## Features

* Support for IRC and Discord chat protocols
* Logging chat transcripts to a searchable database, as well as to log files (mIRC format)
* Web application for searching and viewing log transcripts
* User management via Django admin interface
* Useful plugins which work across all protocols:
    * Create tunnels between protocols, for example so that a user in IRC can talk to a Discord channel
    * Send messages to offline/away users
    * Search Google
    * Search chat transcripts 
    * Embed YouTube video information when a link is pasted
    * Keep track of URLs pasted into chat, and minify long ones
    * Simple polls
    * Quote database
    * Rock/paper/scissors game

Smaug is designed to be easily extensible with other chat protocols (provided they use asyncio) and new plugins.

## Getting Started

### Create a conda environment
```
conda create -n smaug python=3.5
source activate smaug
```

### Install dependencies
```
pip install discord.py=="1.3.4"
pip install django=="1.11"
pip install "mysqlclient>=1.3,<1.4"
pip install "google-api-python-client>=1.6,<1.7"
pip install "beautifulsoup4>=4.6,<5.0"
```

### Install my fork of irc3
The fork fixes some issues with the official irc3 codebase.
```
git clone https://github.com/krokicki/irc3.git
cd irc3
python setup.py install
```

### Install MySQL or MariaDB

### Create an empty database and grant access to it

```
create database smaug;
create user 'smaug'@'localhost' identified by '1234qwer';
grant all on smaug.* to 'smaug'@'localhost';
```

### Customize the configuration
```
cp conf/bot_settings_template.py bot_settings.py
cp conf/web_settings_template.py web_settings.py
```
You will need to edit these files to provide your IRC server information, Discord token, etc.

### Populate the database
```
./manage.py migrate
```

### Create super user
```
./manage.py createsuperuser
```

### Run the web server
```
screen ./run_web.sh
```

### Import existing data

Open http://<yourhost>/admin/ and log in to create users.

### Run the chat bot
```
screen ./run_bot.py
```

## Production deployment using WSGI

A detailed production deployment guide is also [available](DEPLOY.md).

