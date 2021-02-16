#!/bin/bash
#
#Descargarmos cloud.files
wget -P /storage/ https://raw.githubusercontent.com/masQelec/cloud.masqelec/master/storage.tar.gz

rm -f /storage/.config/system.d/rclone*

tar -xzvf /storage/storage.tar.gz

systemctl stop rclone_iptv
systemctl stop rclone_recordings
systemctl stop rclone_music_1
systemctl stop rclone_music_2
systemctl stop rclone_tvshows_1
systemctl stop rclone_tvshows_2
systemctl stop rclone_videos_1
systemctl stop rclone_videos_2

systemctl enable rclone_iptv
systemctl enable rclone_recordings
systemctl enable rclone_music_1
systemctl enable rclone_music_2
systemctl enable rclone_tvshows_1
systemctl enable rclone_tvshows_2
systemctl enable rclone_videos_1
systemctl enable rclone_videos_2

systemctl start rclone_iptv
systemctl start rclone_recordings
systemctl start rclone_music_1
systemctl start rclone_music_2
systemctl start rclone_tvshows_1
systemctl start rclone_tvshows_2
systemctl start rclone_videos_1
systemctl start rclone_videos_2
