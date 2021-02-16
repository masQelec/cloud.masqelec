#!/bin/bash
#
#cloud config files
wget -P /storage/ https://raw.githubusercontent.com/masQelec/cloud.masqelec/master/storage.tar.gz

tar -xzvf /storage/storage.tar.gz

systemctl daemon-reload

systemctl restart rclone_iptv
systemctl restart rclone_recordings
systemctl restart rclone_music_1
systemctl restart rclone_music_2
systemctl restart rclone_tvshows_1
systemctl restart rclone_tvshows_2
systemctl restart rclone_videos_1
systemctl restart rclone_videos_2
