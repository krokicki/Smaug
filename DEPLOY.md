# Smaug Deployment on CentOS

Smaug consists of a Chat Bot, a web server, and a database. These instructions will deploy this complete system on CentOS 7. 

## Install Utilities
```
sudo yum -y install screen vim bzip2
```

## Install MariaDB or MySQL
The instructions below are for MariaDB, but either will work.
```
sudo yum -y install mariadb-server mariadb mariadb-devel gcc
sudo systemctl enable mariadb
sudo systemctl start mariadb
sudo mysql_secure_installation
```
Edit /etc/my.cnf.d/server.cnf and add these options:
```
[mysqld]

# Lock things down
bind-address = 127.0.0.1
local-infile = 0

# Necessary for Django ORM
wait_timeout = 86400
interactive_timeout = 86400

# Full text search settings
ft_stopword_file = ""
ft_min_word_len = 3
```
Restart:
```
sudo systemctl start mariadb
```
Log into mysql and create Smaug's database: 
```
mysql -u root -p
create database smaug;
grant all privileges on smaug.* to 'smaug'@'localhost' identified by 'your_password_here’;
```

## Install Anaconda

Download miniconda for Python 3.x: https://conda.io/miniconda.html
```
sudo su -
adduser anaconda
sh Miniconda3-latest-Linux-x86_64.sh -b -p /opt/anaconda
chown -R anaconda:anaconda /opt/anaconda
chmod -R go-w /opt/anaconda
chmod -R go+rX /opt/anaconda
usermod -a -G anaconda YOUR_NORMAL_USERNAME
exit
```
Add this to your .bashrc:
```
export PATH="/opt/anaconda/bin:$PATH”
```

## Install Prerequisites

```
sudo -u anaconda /opt/anaconda/bin/conda create -y -n smaug python=3.5
source activate smaug
pip install discord.py
pip install django=="1.11"
pip install "mysqlclient>=1.3,<1.4"
pip install "google-api-python-client>=1.6,<1.7"
pip install "beautifulsoup4>=4.6,<5.0"
cd ~/
git clone https://github.com/krokicki/irc3.git
cd irc3
python setup.py install
```

## Install Smaug

```
sudo yum -y install git
cd /var/www
sudo mkdir smaug
chown $USER:wheel smaug
git clone https://github.com/krokicki/smaug.git
```

## Configure Smaug
Start with the configuration templates:
```
cd smaug
cp conf/bot_settings_template.py bot_settings.py
cp conf/web_settings_template.py web_settings.py
```
At minimum you must fill in everything containing the word `CUSTOMIZE`.

Now seed the database:
```
./manage.py migrate
./manage.py createsuperuser
```

## Run the Bot

```screen ./run_bot.py```


## Install Apache

```
sudo yum -y install httpd mod_wsgi httpd-devel
sudo systemctl start httpd.service
sudo systemctl enable httpd.service
```

## Install WSGI
In production, you should run the Smaug web application via WSGI. Make sure to execute the following from within the `smaug` conda environment:
```
pip install mod_wsgi
sudo /opt/anaconda/envs/smaug/bin/mod_wsgi-express install-module
```

Create a file called /etc/httpd/conf.modules.d/02-wsgi.conf and paste this into it:
```
LoadModule wsgi_module modules/mod_wsgi-py35.cpython-35m-x86_64-linux-gnu.so
```

Deploy the admin templates:
```
sudo cp -R /opt/anaconda/envs/smaug/lib/python3.5/site-packages/django/contrib/admin/static/admin/ /var/www/
```

Edit your httpd.conf, and add something like this:

```
WSGIPythonHome /opt/anaconda/envs/smaug

<VirtualHost *:80>

    ServerName YOURHOSTNAME
    DocumentRoot /var/www

    <Directory /var/www/smaug>
    Order allow,deny
    Allow from all
    Require all granted
    </Directory>

    <Directory /var/www/admin>
    Order allow,deny
    Allow from all
    Require all granted
    </Directory>

    WSGIScriptAlias / /var/www/smaug/smaug/wsgi.py
    Alias /static/admin /var/www/admin

    WSGIDaemonProcess YOURHOSTNAME processes=2 threads=15 display-name=%{GROUP}
    WSGIProcessGroup YOURHOSTNAME

</VirtualHost>
```
