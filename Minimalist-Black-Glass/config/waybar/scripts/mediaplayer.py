import argparse
import logging
import sys
import signal
import gi
gi.require_version('Playerctl', '2.0')
from gi.repository import Playerctl, GLib

logger = logging.getLogger(__name__)

manager = Playerctl.PlayerManager()

def on_play_pause(player, status, manager):
    update()

def on_metadata(player, metadata, manager):
    update()

def on_player_appeared(manager, name):
    init_player(name)

def on_player_vanished(manager, name):
    update()

def init_player(name):
    player = Playerctl.Player.new_from_name(name)
    player.connect('playback-status', on_play_pause, manager)
    player.connect('metadata', on_metadata, manager)
    manager.manage_player(player)

def get_text(player):
    metadata = player.props.metadata
    if not metadata:
        return ""
    
    # GLib.Variant handling
    artist = ""
    title = ""
    
    try:
        artist_variant = metadata.lookup_value('xesam:artist', GLib.VariantType('as'))
        if artist_variant:
            artist_list = artist_variant.unpack()
            if artist_list:
                artist = artist_list[0]
    except:
        pass
    
    try:
        title_variant = metadata.lookup_value('xesam:title', GLib.VariantType('s'))
        if title_variant:
            title = title_variant.unpack()
    except:
        pass
    
    if not artist:
        artist = "Unknown"
    if not title:
        title = "Unknown"
        
    status = player.props.playback_status
    icon = "󰐊" if status == Playerctl.PlaybackStatus.PLAYING else "󰏤"
    
    return f"{icon} {title} - {artist}"

def update():
    players = manager.props.players
    if not players:
        print("")
        sys.stdout.flush()
        return

    player = players[0]
    text = get_text(player)
    
    import json
    output = {
        "text": text,
        "class": "custom-media",
        "alt": player.props.player_name
    }
    
    print(json.dumps(output))
    sys.stdout.flush()

def signal_handler(sig, frame):
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    manager.connect('name-appeared', on_player_appeared)
    manager.connect('player-vanished', on_player_vanished)

    for name in manager.props.player_names:
        init_player(name)

    update()  # Initial update
    
    loop = GLib.MainLoop()
    loop.run()