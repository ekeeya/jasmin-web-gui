#!/bin/bash
set -e

# Run the commands as superuser
su -c 'apt-get update && apt-get install -y vim'

# Start the Jasmin service
exec "$@"