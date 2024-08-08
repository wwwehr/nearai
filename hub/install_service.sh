#! /bin/sh

# Other deployment actions here. Want to install (or bounce) service last.

if [ -f /etc/systemd/system/nearai-hub.service ]; then
    sudo systemctl stop nearai-hub.service
    sudo systemctl disable nearai-hub.service
fi

sudo cp -f ./service/nearai-hub.service /etc/systemd/system/nearai-hub.service

sudo systemctl daemon-reload
sudo systemctl enable nearai-hub.service
sudo systemctl start nearai-hub.service
