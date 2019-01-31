FROM ubuntu:16.04

RUN apt-get update

RUN apt-get -y install build-essential python3 python3-dev python3-pip nginx supervisor cron

WORKDIR /app

COPY . /app

RUN pip3 install --upgrade pip

RUN pip3 install -r configuration/requirements.txt

RUN cd analytics && python3 setup.py install

RUN rm /etc/nginx/sites-enabled/default

RUN useradd --no-create-home nginx

RUN chown -R nginx:nginx web_app

RUN chown -R nginx:nginx logs

COPY configuration/nginx.conf /etc/nginx/

COPY configuration/flask-nginx.conf /etc/nginx/conf.d/

COPY configuration/uwsgi.ini /etc/uwsgi/

COPY configuration/supervisord.conf /etc/

COPY configuration/docker.env web_app/.env

COPY configuration/docker.env analytics/.env

CMD crontab -u nginx configuration/cron.conf && service cron restart && /usr/bin/supervisord
