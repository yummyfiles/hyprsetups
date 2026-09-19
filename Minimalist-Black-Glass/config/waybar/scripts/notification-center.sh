#!/bin/bash

# Toggle the custom notification sidebar (slid from right by notify-daemon)
python3 -c "
import socket
s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
try:
    s.sendto(b'toggle', '/tmp/notify-sidebar.sock')
except Exception:
    pass
"