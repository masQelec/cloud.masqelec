#!/bin/bash
#
#Descargarmos cloud.files
wget -P /storage/ https://raw.githubusercontent.com/masQelec/cloud.masqelec/master/storage.tar.gz

rm -f /storage/.config/system.d/rclone_tvshows
rm -f /storage/.config/system.d/rclone_music
rm -f /storage/.config/system.d/rclone_videos

#rm -f /storage/.kodi/userdate/Database/MyMusic72.db
#rm -f /storage/.kodi/userdate/Database/MyVideos116.db
#rm -f /storage/.kodi/userdate/Database/Textures13.db

#rm -rf /storage/.kodi/userdata/Thumbnails/*

tar -xzvf /storage/storage.tar.gz

systemctl daemon-reload

systemctl stop rclone_music
systemctl stop rclone_videos
systemctl stop rclone_tvshows

systemctl disable rclone_music
systemctl disable rclone_videos
systemctl disable rclone_tvshows

systemctl enable rclone_music_1
systemctl enable rclone_music_2
systemctl enable rclone_tvshows_1
systemctl enable rclone_tvshows_2
systemctl enable rclone_videos_1
systemctl enable rclone_videos_2

systemctl start rclone_music_1
systemctl start rclone_music_2
systemctl start rclone_tvshows_1
systemctl start rclone_tvshows_2
systemctl start rclone_videos_1
systemctl start rclone_videos_2
