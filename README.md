# **DEPRECATED**

This project is replaced with a new more flexible concept that can be found 
[here](https://github.com/Bloodb0ne/twitch_log_renderer)

# Twitch Chatlogs to HTML

Renders twitch chat to an html document, based on the template

When using logs from Twitch chat replay you dont need to download all twitch emotes,
because the logs store emote information

# Usage

*-h*, *--help*
show this help message and exit

*--update_emotes* **CHANNEL_NAME**
Download and cache emotes from ffz/bttv for the selected channel

*--twitch_emotes*
Download the entirety of twitch emotes

*--vod* **VOD_ID**
Download the chat replay from a Twitch VOD, requires a client_id

*--client_id* **CLIENT_ID**
(Required) for downloading from twitch

*--input* **INPUT_FILE**
Input twitch/raw log file

*--output* **OUTPUT_FILE**
HTML file thats generated

## TODO
- [ ] Render / Store badges
- [ ] Add timestamps so we can create a scrolling effect ( maybe some sort of video overlay)
- [ ] Separate the template styles to a external file, additional parameter
- [ ] Improve performance on fetching twitch emotes from database

