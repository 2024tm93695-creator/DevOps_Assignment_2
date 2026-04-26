#!/bin/bash
# Fix docker socket permissions then start Jenkins as jenkins user
chmod 666 /var/run/docker.sock 2>/dev/null || true
exec su -s /bin/bash jenkins -c "/usr/local/bin/jenkins.sh"
