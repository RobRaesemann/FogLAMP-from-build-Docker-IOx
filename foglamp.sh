#!/bin/bash

service rsyslog start
/usr/local/foglamp/bin/foglamp start
tail -f /var/log/syslog