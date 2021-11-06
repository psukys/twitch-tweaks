"""The MIT License (MIT).

Copyright (c) 2013

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import urllib.request
import json
from typing import Dict, Any
import sys
import hexchat

__module_name__ = "Twitch Tweaks"
__module_author__ = "oxguy3"
__module_version__ = "0.1"
__module_description__ = "Do Twitch better. Forked from PDog's twitch-title.py"
# TODO: Figure out why get_current_status() sometimes doesn't print updated status <PDog>

pluginprefix = "twtw_"


class StreamParser:

    def __init__(self, channel):
        self.channel = channel
        self.twitch_chans = []
        self.is_online = False
        self.display_name = channel  # fallback if Twitch API is down
        self.game = ""
        self.title = ""
        # self.context = hexchat.find_context(hexchat.get_info("server"), "#{0}".format(channel))

    def set_topic(self):
        """Set the channel topic (no formatting) and print the topic locally with formatting."""

        status_short = get_pref("bullet_online") if self.is_online else get_pref("bullet_offline")

        if get_pref("modify_topic"):
            msg = f"{status_short}\00318{self.display_name}\00399 | {self.title} | \00318{self.game}\00399"

            # HexChat doesn't support hiding characters in the topic bar (Windows), so strip the formatting until it's fixed
            if sys.platform == "win32":
                msg = hexchat.strip(msg, -1, 3)

            if hexchat.get_info("topic") != msg:
                hexchat.command("RECV :Topic!Topic@twitch.tv TOPIC #{0} :{1}".format(self.channel, msg))

        if get_pref("modify_tab"):
            # Set the tab title to the properly capitalized form of the name
            settabCommand = "SETTAB {0}{1}"\
                .format(status_short, self.display_name)
            hashChannel = "#{0}".format(self.channel)

            cxt = hexchat.find_context(hexchat.get_info("server"), hashChannel)
            if cxt is not None:
                cxt.command(settabCommand)

    def get_twitch_channels(self):
        """Get a list of open TwitchTV channels and store them in self.twitch_chans."""
        self.twitch_chans = []
        for chan in hexchat.get_list("channels"):
            if chan.type == 2 and get_pref("twitch_base_domain") in chan.context.get_info("host"):
                self.twitch_chans.append(chan.channel)

    def update_status(self):
        """Check the status of open channels."""
        for chan in self.twitch_chans:
            self.channel = chan[1:]
            self.get_stream_info()
            self.set_topic()

    def get_stream_info(self):
        """Get the stream information."""
        stream_url = get_pref("twitch_api_root") + "/streams"
        params = {"user_login": self.channel}
        stream_data = get_json(url=stream_url, params=params)

        self.is_online = False
        self.display_name = self.channel
        self.game = ""
        self.title = "\035Stream is offline\017"

        if len(stream_data["data"]) == 1:
            data = stream_data["data"][0]
            self.is_online = True
            self.display_name = data["user_name"]
            self.game = data["game_name"]
            self.title = data["title"]


def get_json(url: str, params: dict[str, str] = None) -> Dict[str, Any]:
    request_url = url
    if params is not None:
        request_url += f"?{urllib.parse.urlencode(params)}"
    request_headers = {
        "Authorization": f"Bearer {get_pref('api_token')}",
        "Client-Id": get_pref('api_client_id')
    }
    request = urllib.request.Request(url=request_url, headers=request_headers)
    print(request_url)
    with urllib.request.urlopen(request) as response:
        data = json.loads(response.read().decode())
    return data


def is_twitch():
    server = hexchat.get_info("host")
    return server and get_pref("twitch_base_domain") in server


def get_current_status(_=None):
    """Update the stream status."""
    parser = StreamParser(channel=None)
    parser.get_twitch_channels()
    parser.update_status()


def join_cb(word, word_eol, userdata):
    """Set the topic immediately after joining a channel."""
    if is_twitch():

        channel = word[1][1:]
        parser = StreamParser(channel=channel)
        parser.get_stream_info()
        parser.set_topic()

    return hexchat.EAT_NONE


PREFERENCE_DEFAULTS = {
    "twitch_api_root": "https://api.twitch.tv/helix",
    "api_token": hexchat.get_info('password').split(":")[1],
    "api_client_id": "q6batx0epp608isickayubi39itsckt",
    "twitch_base_domain": "twitch.tv",
    "bullet_offline": "\u25A1 ",
    "bullet_online": "\u25A0 ",
    "modify_topic": True,
    "modify_tab": True,
    "refresh_rate": 600
}


def init_pref():
    for pref, pref_default in PREFERENCE_DEFAULTS.items():
        # if get_pref(pref) is None:
        set_pref(pref, pref_default)


def get_pref(key):
    return hexchat.get_pluginpref(pluginprefix + key)


def set_pref(key, value):
    return hexchat.set_pluginpref(pluginprefix + key, value)


"""
Command hook callbacks
"""

twtwset_help_text = "Usage: TWTWSET <name> <value...> - Sets/gets the value of a twitch-tweaks configuration variable"
twtwrefresh_help_text = "Usage: TWTWREFRESH - Forces twitch-tweaks to refresh the statuses of all Twitch channels"
twtwlist_help_text = "Usage: TWTWLIST - Lists all preferences set for twitch-tweaks"


def twtwset_cb(word, word_eol, userdata):
    if len(word) < 2:
        print("Incorrect syntax. " + twtwset_help_text)
    else:
        key = word[1]
        if (get_pref(key) is None):
            print("Unknown variable name. Use TWTWLIST to see existing variables")
        else:
            if len(word) > 2:
                set_pref(key, word_eol[2])
            print("{0} = {1}".format(key, get_pref(key)))

    return hexchat.EAT_ALL


def twtwrefresh_cb(word, word_eol, userdata):
    get_current_status()
    print("Refreshed all Twitch channels!")
    return hexchat.EAT_ALL


def twtwlist_cb(word, word_eol, userdata):
    for key in hexchat.list_pluginpref():
        if key.startswith(pluginprefix):
            cleanKey = key[len(pluginprefix):]
            print("{0} = {1}".format(cleanKey, get_pref(cleanKey)))

    return hexchat.EAT_ALL


init_pref()

hexchat.hook_print("You Join", join_cb, hexchat.PRI_LOWEST)
hexchat.hook_command("TWTWSET", twtwset_cb, help=twtwset_help_text)
hexchat.hook_command("TWTWREFRESH", twtwrefresh_cb, help=twtwrefresh_help_text)
hexchat.hook_command("TWTWLIST", twtwlist_cb, help=twtwlist_help_text)
hexchat.hook_timer(get_pref("refresh_rate"), get_current_status)
get_current_status()
hexchat.prnt(__module_name__ + " version " + __module_version__ + " loaded")
