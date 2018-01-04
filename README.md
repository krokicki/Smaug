# [Smaug](http://github.com/krokicki/smaug)

Smaug is a chat bot for simultaneous deployment on multiple protocols. He aims to bridge various chat
protocols by providing a unified logging view and tunneling mechanism. There are also various plugins
available to do some useful stuff.

## Features

* Logging chat transcripts to a searchable database, as well as to log files (mIRC format)
* Web application for searching and viewing log transcripts
* User management via Django admin interface
* Currently supports IRC and Discord chat protocols
* Useful plugins which work across all protocols:
    * Create tunnels between protocols, for example so that a user in IRC can talk to a Discord channel
    * Send messages to offline/away users
    * Search with Google
    * Search logs with a bot command
    * Embed YouTube video information when a link is pasted
    * Keep track of URLs pasted into chat, and minify long ones
    * Simple polls
    * Quote database
    * Rock/paper/scissors game

Smaug is designed to be easily extensible with other chat protocols (provided they use asyncio) and new plugins.

## Getting Started

1. Create a conda environment
```
conda create -n discord python=3.5
source activate discord
```

2. Install dependencies
```
python3 -m pip install -U discord.py
pip install django=="1.11"
pip install "mysqlclient>=1.3,<1.4"
pip install "google-api-python-client>=1.6,<1.7"
pip install "beautifulsoup4>=4.6,<5.0"
```

3. Install my fork of irc3
Fixes some issues with the official irc3.
```
git clone https://github.com/krokicki/irc3.git
cd irc3
python setup.py install
```

4. Install MySQL

5. Create an empty MySQL database and grant access

```
create database smaug;
grant all privileges on smaug.* to 'smaug'@'localhost' identified by 'your_password_here';
```

6. Populate the database

```
./manage.py makemigrations
./manage.py migrate
```

7. Customize configuration
```
cp conf/bot_settings_template.py bot_settings.py
cp conf/web_settings_template.py web_settings.py
```
You will need to edit these files to provide your IRC server information, Discord token, etc.

8. Run the web server

```
screen ./run_web.sh
```

5. Import existing data

Open http://<yourhost>/admin/ and log in to create users.

6. Run the protocol bot

```
screen ./run_bot.py
```

## Deploying using WSGI

Configuring Apache is outside the scope of this document. Once you have Apache HTTPD installed and running,
just deploy the code base to somewhere under /var/www, and add a script alias to your httpd.conf:

WSGIScriptAlias / /var/www/smaug/django.wsgi

## Importing IRC logs

Logs must be in mIRC format. This isn't an ideal format, it's just what I had to work with. Feel free to contribute additional log parsers.

Import instructions TBD.

