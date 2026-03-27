FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      software-properties-common ca-certificates curl unzip git gnupg lsb-release \
      supervisor mysql-server \
    && add-apt-repository ppa:ondrej/php -y \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
      php8.3 php8.3-cli php8.3-mysql php8.3-curl php8.3-mbstring php8.3-xml php8.3-zip \
    && curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/demo

COPY demo/docker/entrypoint.sh /usr/local/bin/demo-entrypoint
COPY demo/docker/install-yii.sh /usr/local/bin/install-yii
COPY demo/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY demo/app /opt/demo/app

RUN chmod +x /usr/local/bin/demo-entrypoint /usr/local/bin/install-yii \
    && mkdir -p /var/log/supervisor /var/cache/texto2sql-demo /var/run/mysqld \
    && chown -R mysql:mysql /var/run/mysqld /var/lib/mysql

EXPOSE 8080 3306

ENTRYPOINT ["/usr/local/bin/demo-entrypoint"]
