#!/usr/bin/env bash
set -euo pipefail

MYSQL_DEMO_USER="${MYSQL_DEMO_USER:-demo}"
MYSQL_DEMO_PASSWORD="${MYSQL_DEMO_PASSWORD:-demo1234}"
MYSQL_DEMO_DB="${MYSQL_DEMO_DB:-sakila}"

if [ ! -d "/var/lib/mysql/mysql" ]; then
  mysqld --initialize-insecure --user=mysql --datadir=/var/lib/mysql
fi

mysqld_safe --datadir=/var/lib/mysql &

for i in {1..40}; do
  if mysqladmin ping --silent; then
    break
  fi
  sleep 1
done

mysql -uroot <<SQL
CREATE DATABASE IF NOT EXISTS ${MYSQL_DEMO_DB};
CREATE USER IF NOT EXISTS '${MYSQL_DEMO_USER}'@'%' IDENTIFIED BY '${MYSQL_DEMO_PASSWORD}';
GRANT SELECT, SHOW VIEW ON ${MYSQL_DEMO_DB}.* TO '${MYSQL_DEMO_USER}'@'%';
FLUSH PRIVILEGES;
SQL

if [ ! -f /var/lib/mysql/.sakila_loaded ]; then
  curl -fsSL https://downloads.mysql.com/docs/sakila-db.tar.gz -o /tmp/sakila-db.tar.gz
  tar -xzf /tmp/sakila-db.tar.gz -C /tmp
  mysql -uroot < /tmp/sakila-db/sakila-schema.sql
  mysql -uroot < /tmp/sakila-db/sakila-data.sql
  touch /var/lib/mysql/.sakila_loaded
fi

if [ "${INSTALL_YII_ON_BOOT:-false}" = "true" ] && [ ! -d /opt/demo/yii-demo ]; then
  /usr/local/bin/install-yii || true
fi

mysqladmin -uroot shutdown

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
