#!/usr/bin/env bash
set -euo pipefail

cd /opt/demo
if [ -d yii-demo ]; then
  exit 0
fi

composer create-project yiisoft/app yii-demo --prefer-dist --no-interaction || {
  echo "No fue posible crear el esqueleto Yii3 automáticamente. Continuando con demo minimal." >&2
  exit 0
}
