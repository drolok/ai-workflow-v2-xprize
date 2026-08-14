#!/usr/bin/env bash
set -u
source ~/.expo_credentials
export EXPO_TOKEN
export EXPO_ASC_API_KEY_PATH=~/AuthKey_ASC.p8
export EXPO_ASC_KEY_ID="$ASC_KEY_ID"
export EXPO_ASC_ISSUER_ID="$ASC_ISSUER_ID"
cd <HOME>/<PRIVATE_PROJECT>/apps/mobile
# Primera vez / si cambió una capability del App ID (ej. se agregó Sign in
# with Apple): correr SIN --refresh-ad-hoc-provisioning-profile y en modo
# INTERACTIVO (sin este wrapper) para que el fundador responda el prompt
# de Apple Team Type una sola vez. Runs posteriores ya no lo piden.
npx eas-cli build --profile development --platform ios --no-wait "$@"
