#!/usr/bin/env bash
set -u
source ~/.vercel_credentials
cd <HOME>/<PRIVATE_PROJECT>
export VERCEL_TOKEN
npx --yes vercel --prod --token "$VERCEL_TOKEN" --yes 2>&1 | tail -30
