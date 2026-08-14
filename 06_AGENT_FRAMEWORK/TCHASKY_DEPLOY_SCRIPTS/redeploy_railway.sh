#!/usr/bin/env bash
set -u
source ~/.railway_credentials
cd <HOME>/<PRIVATE_PROJECT>
export RAILWAY_TOKEN
npx --yes @railway/cli up --service api --environment production --detach --json 2>&1 | tail -20
