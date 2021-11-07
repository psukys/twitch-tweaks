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
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import hexchat

__module_name__ = "Twitch Tweaks"
__module_author__ = "psukys"
__module_version__ = "1.0"
__module_description__ = "Do Twitch better. Forked from oxguy3"

pluginprefix = "twtw_"


@dataclass
class Stream:
    login_name: str
    display_name: str
    game: str
    title: str

    @property
    def as_topic(self):
        return f"\00318{self.display_name}\00399 | {self.title} | \00318{self.game}\00399"


def update_topic(name: str, stream: Stream = None):
    """Set the channel topic (no formatting) and print the topic locally with formatting."""
    status = get_pref("bullet_online") if stream is not None else get_pref("bullet_offline")

    if get_pref("modify_topic"):
        msg = f"{status}"
        if stream:
            msg += f"{stream.as_topic}"
        else:
            msg += f"\00318{name}\035 Stream is offline\017"

        if hexchat.find_context(channel=f"#{name}").get_info("topic") != msg:
            hexchat.command("RECV :Topic!Topic@twitch.tv TOPIC #{0} :{1}".format(name, msg))

    if get_pref("modify_tab"):
        ctx = hexchat.find_context(hexchat.get_info("server"), f"#{name}")
        if ctx is not None:
            # Set the tab title to the properly capitalized form of the name
            set_tab_command = "SETTAB {0}{1}".format(status, stream.display_name if stream else name)
            ctx.command(set_tab_command)


def get_open_stream_names() -> List[str]:
    """Get a list of open TwitchTV channels and store them in self.twitch_chans."""
    return [chan.channel[1:] for chan in hexchat.get_list("channels") if chan.type == 2 and get_pref("twitch_base_domain") in chan.context.get_info("host")]


def update_streams(stream_names: List[str]):
    for name in stream_names:
        stream = get_stream(user_login=name)
        update_topic(name=name, stream=stream)


def get_stream(user_login: str) -> Optional[Stream]:
    """Get the stream information."""
    stream_url = get_pref("twitch_api_root") + "/streams"
    params = {"user_login": user_login}
    response = get_json(url=stream_url, params=params)
    if response["data"]:
        data = response["data"][0]
        return Stream(
            login_name=data["user_login"],
            display_name=data["user_name"],
            game=data["game_name"],
            title=data["title"]
        )


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


def update_all(_=None):
    names = get_open_stream_names()
    update_streams(stream_names=names)


def is_twitch():
    server = hexchat.get_info("host")
    return server and get_pref("twitch_base_domain") in server


def join_cb(word, word_eol, userdata):
    """Set the topic immediately after joining a channel."""
    if is_twitch():
        user_login = word[1][1:]
        stream = get_stream([user_login])
        update_topic(user_login, stream)

    return hexchat.EAT_NONE


PREFERENCE_DEFAULTS = {
    "twitch_api_root": "https://api.twitch.tv/helix",
    "api_token": hexchat.get_info('password').split(":")[1],
    "api_client_id": "q6batx0epp608isickayubi39itsckt",  # TODO: would be good not to hardcode this...
    "twitch_base_domain": "twitch.tv",
    "bullet_offline": "\u25A1 ",
    "bullet_online": "\u25A0 ",
    "modify_topic": True,
    "modify_tab": True,
    "refresh_rate": 600
}


def init_pref():
    for pref, pref_default in PREFERENCE_DEFAULTS.items():
        if get_pref(pref) is None:
            set_pref(pref, pref_default)


def get_pref(key):
    return hexchat.get_pluginpref(pluginprefix + key)


def set_pref(key, value):
    return hexchat.set_pluginpref(pluginprefix + key, value)


"""
Command hook callbacks
"""

TWTWSET_HELP_TEXT = "Usage: TWTWSET <name> <value...> - Sets/gets the value of a twitch-tweaks configuration variable"
TWTWREFRESH_HELP_TEXT = "Usage: TWTWREFRESH - Forces twitch-tweaks to refresh the statuses of all Twitch channels"
TWTWLIST_HELP_TEXT = "Usage: TWTWLIST - Lists all preferences set for twitch-tweaks"


def twtw_set_cb(word, word_eol, userdata):
    if len(word) < 2:
        print(f"Incorrect syntax. f{TWTWLIST_HELP_TEXT}")
    else:
        key = word[1]
        if (get_pref(key) is None):
            print("Unknown variable name. Use TWTWLIST to see existing variables")
        else:
            if len(word) > 2:
                set_pref(key, word_eol[2])
            print("{0} = {1}".format(key, get_pref(key)))

    return hexchat.EAT_ALL


def twtw_refresh_cb(word, word_eol, userdata):
    update_all()
    print("Refreshed all Twitch channels!")
    return hexchat.EAT_ALL


def twtw_list_cb(word, word_eol, userdata):
    for key in hexchat.list_pluginpref():
        if key.startswith(pluginprefix):
            clean_key = key[len(pluginprefix):]
            print(f"{clean_key} = {get_pref(clean_key)}")

    return hexchat.EAT_ALL


init_pref()

hexchat.hook_print("You Join", join_cb, hexchat.PRI_LOWEST)
hexchat.hook_command("TWTWSET", twtw_set_cb, help=TWTWSET_HELP_TEXT)
hexchat.hook_command("TWTWREFRESH", twtw_refresh_cb, help=TWTWREFRESH_HELP_TEXT)
hexchat.hook_command("TWTWLIST", twtw_list_cb, help=TWTWLIST_HELP_TEXT)
hexchat.hook_timer(get_pref("refresh_rate"), update_all)

hexchat.prnt(__module_name__ + " version " + __module_version__ + " loaded")
