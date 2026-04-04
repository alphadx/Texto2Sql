#!/usr/bin/env bash
set -euo pipefail

MYSQL_DEMO_USER="${MYSQL_DEMO_USER:-demo}"
MYSQL_DEMO_PASSWORD="${MYSQL_DEMO_PASSWORD:-demo1234}"
MYSQL_DEMO_DB="${MYSQL_DEMO_DB:-sakila}"
DEMO_MYSQL_WAIT_TIMEOUT_SECONDS="${DEMO_MYSQL_WAIT_TIMEOUT_SECONDS:-900}"
DEMO_MYSQL_INTERACTIVE_TIMEOUT_SECONDS="${DEMO_MYSQL_INTERACTIVE_TIMEOUT_SECONDS:-900}"
DEMO_MYSQL_MAX_EXECUTION_TIME_MS="${DEMO_MYSQL_MAX_EXECUTION_TIME_MS:-900000}"

MYSQL_CMD=(mysql -uroot)
MYSQLADMIN_CMD=(mysqladmin -uroot)
if [ -f /etc/mysql/debian.cnf ]; then
  MYSQL_CMD=(mysql --defaults-extra-file=/etc/mysql/debian.cnf)
  MYSQLADMIN_CMD=(mysqladmin --defaults-extra-file=/etc/mysql/debian.cnf)
fi

if [ ! -d "/var/lib/mysql/mysql" ]; then
  echo "[entrypoint] Initializing MySQL data directory..."
  if ! mysqld --initialize-insecure --user=mysql --datadir=/var/lib/mysql; then
    echo "[entrypoint] --initialize-insecure failed, trying mysql_install_db fallback..."
    mysql_install_db --user=mysql --datadir=/var/lib/mysql
  fi
fi

echo "[entrypoint] Bootstrapping temporary MySQL for schema/user init..."
mysqld_safe --datadir=/var/lib/mysql &

for i in {1..90}; do
  if "${MYSQLADMIN_CMD[@]}" ping --silent; then
    break
  fi
  sleep 1
done

if ! "${MYSQLADMIN_CMD[@]}" ping --silent; then
  echo "[entrypoint] Temporary MySQL bootstrap failed to start." >&2
  exit 1
fi

"${MYSQL_CMD[@]}" <<SQL
CREATE DATABASE IF NOT EXISTS ${MYSQL_DEMO_DB};
CREATE USER IF NOT EXISTS '${MYSQL_DEMO_USER}'@'%' IDENTIFIED BY '${MYSQL_DEMO_PASSWORD}';
GRANT SELECT, SHOW VIEW ON ${MYSQL_DEMO_DB}.* TO '${MYSQL_DEMO_USER}'@'%';
SET GLOBAL wait_timeout = ${DEMO_MYSQL_WAIT_TIMEOUT_SECONDS};
SET GLOBAL interactive_timeout = ${DEMO_MYSQL_INTERACTIVE_TIMEOUT_SECONDS};
SET GLOBAL max_execution_time = ${DEMO_MYSQL_MAX_EXECUTION_TIME_MS};
FLUSH PRIVILEGES;
SQL

if [ ! -f /var/lib/mysql/.sakila_loaded ]; then
  echo "[entrypoint] Loading Sakila sample data..."
  curl -fsSL https://downloads.mysql.com/docs/sakila-db.tar.gz -o /tmp/sakila-db.tar.gz
  tar -xzf /tmp/sakila-db.tar.gz -C /tmp
  "${MYSQL_CMD[@]}" < /tmp/sakila-db/sakila-schema.sql
  "${MYSQL_CMD[@]}" < /tmp/sakila-db/sakila-data.sql
  touch /var/lib/mysql/.sakila_loaded
fi

if [ "${INSTALL_YII_ON_BOOT:-false}" = "true" ] && [ ! -d /opt/demo/yii-demo ]; then
  /usr/local/bin/install-yii || true
fi

"${MYSQLADMIN_CMD[@]}" shutdown

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
