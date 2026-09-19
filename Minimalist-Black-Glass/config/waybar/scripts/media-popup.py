#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

set -e

PIDFILE=/tmp/media-popup.pid
if [ -f "$PIDFILE" ]; then
    OLD=$(cat "$PIDFILE" 2>/dev/null)
    if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null; then
        kill "$OLD" 2>/dev/null
        rm -f "$PIDFILE"
        exit 0
    fi
    rm -f "$PIDFILE"
fi

GTK_SCRIPT="
#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, GLib, GtkLayerShell, Gdk, GdkPixbuf
import subprocess
import os
import re
import urllib.request

SLIDE_STEPS = 18
SLIDE_MS = 16

CSS = '''
window {
    background-color: #000000;
    color: #FFFFFF;
    border: 2px solid #FFFFFF;
    border-radius: 0;
}
label {
    color: #FFFFFF;
}
button,
.button {
    background-color: #000000;
    background-image: none;
    color: #FFFFFF;
    border: 1px solid #FFFFFF;
    border-radius: 0;
    box-shadow: none;
    font-family: \"JetBrainsMono Nerd Font\", monospace;
    font-size: 15px;
    padding: 4px 8px;
}
button label,
.button label {
    color: #FFFFFF;
}
button:hover,
.button:hover,
button:active,
.button:active {
    background-color: #FFFFFF;
    color: #000000;
    border: 1px solid #FFFFFF;
}
button:hover label,
.button:hover label,
button:active label,
.button:active label {
    color: #000000;
}
'''

def apply_theme():
    screen = Gdk.Screen.get_default()
    if not screen:
        return
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS.encode())
    Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

def playerctl(args, player=None):
    cmd = ['playerctl']
    if player:
        cmd += ['--player', player]
    cmd += args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return None

def choose_player():
    plist = players()
    if not plist:
        return None
    for p in plist:
        if playerctl(['status'], player=p) == 'Playing':
            return p
    for p in plist:
        if p == 'spotify':
            return p
    return plist[0]

def get_meta(player=None):
    return {
        'title': playerctl(['metadata', '--format', '{{title}}'], player),
        'artist': playerctl(['metadata', '--format', '{{artist}}'], player),
        'art': playerctl(['metadata', '--format', '{{mpris:artUrl}}'], player),
        'status': playerctl(['status'], player),
        'loop': playerctl(['loop'], player),
        'pid': playerctl(['metadata', '--format', '{{mpris:pid}}'], player),
        'player': player or '',
    }

def players():
    r = subprocess.run(['playerctl', '-l'], capture_output=True, text=True)
    if r.returncode == 0:
        return r.stdout.splitlines()
    return []

def load_cover(art_url, size):
    try:
        path = None
        if art_url:
            if art_url.startswith('file://'):
                path = art_url[len('file://'):]
            elif art_url.startswith('http://') or art_url.startswith('https://'):
                cache = '/tmp/media-cover.img'
                urllib.request.urlretrieve(art_url, cache)
                path = cache
        if path and os.path.exists(path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
            return pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
    except Exception:
        pass
    pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, size, size)
    pixbuf.fill(0x1E1E1EFF)
    return pixbuf

class MediaPopup(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)
        apply_theme()
        self.set_title('Media')
        self.set_resizable(False)

        display = Gdk.Display.get_default()
        monitor = display.get_monitor(0)
        geo = monitor.get_geometry()
        self.screen_w = geo.width
        self.screen_h = geo.height

        self.bar_height = 30
        self.player = choose_player()
        self.meta = get_meta(self.player)
        self.cover_size = 120

        self.popup_width = 420
        self.left_margin = max(8, (self.screen_w - self.popup_width) // 2)

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_exclusive_zone(self, -1)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, self.left_margin)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, -400)

        self.set_size_request(self.popup_width, -1)

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        container.set_margin_top(16)
        container.set_margin_bottom(16)
        container.set_margin_start(16)
        container.set_margin_end(16)

        cover = load_cover(self.meta['art'], self.cover_size)
        img = Gtk.Image.new_from_pixbuf(cover)
        self.img = img

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        title = self.meta['title'] or 'Nothing playing'
        artist = self.meta['artist'] or ''
        title_label = Gtk.Label()
        title_label.set_markup('<span weight=\"bold\" size=\"13000\">{}</span>'.format(GLib.markup_escape_text(title)))
        title_label.set_xalign(0)
        title_label.set_line_wrap(True)
        title_label.set_max_width_chars(int(self.popup_width * 0.42))
        self.title_label = title_label
        artist_label = Gtk.Label()
        artist_label.set_markup('<span size=\"11000\">{}</span>'.format(GLib.markup_escape_text(artist)))
        artist_label.set_xalign(0)
        artist_label.set_line_wrap(True)
        artist_label.set_max_width_chars(int(self.popup_width * 0.42))
        self.artist_label = artist_label
        self.last_art = self.meta['art']
        text_box.pack_start(title_label, False, False, 0)
        text_box.pack_start(artist_label, False, False, 0)

        info_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        info_row.pack_start(img, False, False, 0)
        info_row.pack_start(text_box, True, True, 0)
        container.add(info_row)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        controls.set_margin_top(8)

        self.btn_prev = Gtk.Button(label='󰁈')
        self.btn_prev.set_tooltip_text('Previous')
        self.btn_prev.connect('clicked', self.on_prev)
        controls.pack_start(self.btn_prev, False, False, 0)

        playing = self.meta['status'] == 'Playing'
        self.btn_play = Gtk.Button(label='󰁌' if playing else '󰁋')
        self.btn_play.set_tooltip_text('Play / Pause')
        self.btn_play.connect('clicked', self.on_play)
        controls.pack_start(self.btn_play, False, False, 0)

        self.btn_next = Gtk.Button(label='󰁑')
        self.btn_next.set_tooltip_text('Next')
        self.btn_next.connect('clicked', self.on_next)
        controls.pack_start(self.btn_next, False, False, 0)

        loop_state = (self.meta['loop'] or '').lower()
        self.btn_repeat = Gtk.Button(label='󰕆' if loop_state in ('track', 'once') else '󰕇')
        self.btn_repeat.set_tooltip_text('Loop: ' + (self.meta['loop'] or 'Off'))
        self.btn_repeat.connect('clicked', self.on_repeat)
        controls.pack_start(self.btn_repeat, False, False, 0)

        self.btn_prev.set_size_request(64, 40)
        self.btn_play.set_size_request(64, 40)
        self.btn_next.set_size_request(64, 40)
        self.btn_repeat.set_size_request(64, 40)

        spacer = Gtk.Label()
        controls.pack_start(spacer, True, True, 0)

        self.btn_hide = Gtk.Button(label='󰗐')
        self.btn_hide.set_tooltip_text('Hide / show media app window')
        self.btn_hide.set_size_request(64, 40)
        self.btn_hide.connect('clicked', self.on_hide)
        controls.pack_start(self.btn_hide, False, False, 0)

        container.add(controls)

        if not players():
            for b in (self.btn_prev, self.btn_play, self.btn_next, self.btn_repeat, self.btn_hide):
                b.set_sensitive(False)
        elif not self.player:
            for b in (self.btn_prev, self.btn_play, self.btn_next, self.btn_repeat, self.btn_hide):
                b.set_sensitive(False)

        self.add(container)
        self.show_all()

        self._cancel_slide()
        self._slide_to(self.bar_height + 4)
        self._start_timer()
        self._refresh_id = GLib.timeout_add(800, self._poll_updates)

    def _cancel_slide(self):
        if getattr(self, '_slide_id', None) is not None:
            GLib.source_remove(self._slide_id)
            self._slide_id = None

    def _slide_to(self, target):
        self._cancel_slide()
        current = GtkLayerShell.get_margin(self, GtkLayerShell.Edge.TOP)
        start = current
        steps = SLIDE_STEPS
        step = (target - current) / float(steps)
        count = [0]

        def tick():
            count[0] += 1
            if count[0] >= steps:
                GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, int(target))
                self._slide_id = None
                if target < 0:
                    self.destroy()
                    Gtk.main_quit()
                return GLib.SOURCE_REMOVE
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, int(start + step * count[0]))
            return GLib.SOURCE_CONTINUE

        self._slide_id = GLib.timeout_add(SLIDE_MS, tick)

    def _start_timer(self):
        self._reset_timer = None
        self.reset_timer()

    def reset_timer(self, *args):
        if getattr(self, '_hide_id', None) is not None:
            GLib.source_remove(self._hide_id)
        self._hide_id = GLib.timeout_add_seconds(6, self._close_after_idle)

    def _close_after_idle(self):
        self._hide_id = None
        self._slide_to(-self.get_allocated_height() - 10)
        return False

    def close_now(self):
        self._slide_to(-self.get_allocated_height() - 10)

    def refresh_buttons(self):
        self.player = choose_player() or self.player
        self.meta = get_meta(self.player)
        status = self.meta['status']
        self.btn_play.set_label('󰁌' if status == 'Playing' else '󰁋')
        loop = self.meta['loop'] or ''
        self.btn_repeat.set_label('󰕆' if loop.lower() in ('track', 'once') else '󰕇')
        self.btn_repeat.set_tooltip_text('Loop: ' + (loop or 'Off'))
        title = self.meta['title'] or 'Nothing playing'
        artist = self.meta['artist'] or ''
        self.title_label.set_markup('<span weight=\"bold\" size=\"13000\">{}</span>'.format(GLib.markup_escape_text(title)))
        if artist:
            self.artist_label.set_markup('<span size=\"11000\">{}</span>'.format(GLib.markup_escape_text(artist)))
            self.artist_label.show()
        else:
            self.artist_label.set_markup('')
            self.artist_label.hide()
        if status and self.meta['art'] != self.last_art:
            self.last_art = self.meta['art']
            self.img.set_from_pixbuf(load_cover(self.meta['art'], self.cover_size))
        count = len(players())
        for b in (self.btn_prev, self.btn_play, self.btn_next, self.btn_repeat, self.btn_hide):
            b.set_sensitive(count > 0)

    def _poll_updates(self):
        self.refresh_buttons()
        return GLib.SOURCE_CONTINUE

    def on_play(self, button):
        subprocess.run(['playerctl', '--player', self.player, 'play-pause'])
        self.refresh_buttons()
        self.reset_timer()

    def on_next(self, button):
        subprocess.run(['playerctl', '--player', self.player, 'next'])
        self.refresh_buttons()
        self.reset_timer()

    def on_prev(self, button):
        subprocess.run(['playerctl', '--player', self.player, 'previous'])
        self.refresh_buttons()
        self.reset_timer()

    def on_repeat(self, button):
        loop = (playerctl(['loop'], self.player) or 'None').lower()
        order = {'none': 'Playlist', 'playlist': 'Track', 'all': 'Track', 'once': 'None', 'track': 'None'}
        nxt = order.get(loop, 'Playlist')
        subprocess.run(['playerctl', '--player', self.player, 'loop', nxt])
        self.btn_repeat.set_label('󰕆' if nxt.lower() in ('track', 'once') else '󰕇')
        self.btn_repeat.set_tooltip_text('Loop: ' + nxt)
        self.reset_timer()

    def find_window(self):
        addr = None
        pids = []
        if self.meta['pid'] and re.match(r'^\d+$', self.meta['pid']):
            pids.append(self.meta['pid'])
        r = subprocess.run(['hyprctl', 'clients', '-j'], capture_output=True, text=True)
        windows = []
        if r.returncode == 0:
            try:
                import json
                windows = json.loads(r.stdout)
            except Exception:
                pass
        for w in windows:
            if any(str(w.get('pid', '')).startswith(p) for p in pids):
                addr = w.get('address')
                break
        if not addr:
            pname = (self.player or '').lower()
            for w in windows:
                cls = (w.get('class') or '').lower()
                title = (w.get('title') or '').lower()
                if pname and pname in cls:
                    addr = w.get('address')
                    break
                if pname and re.sub(r'[^a-z]', '', pname) in cls:
                    addr = w.get('address')
                    break
        return addr

    def window_workspace(self, addr):
        r = subprocess.run(['hyprctl', 'clients', '-j'], capture_output=True, text=True)
        if r.returncode != 0:
            return None
        try:
            import json
            for w in json.loads(r.stdout):
                if w.get('address') == addr:
                    ws = w.get('workspace') or {}
                    return ws.get('name') or str(ws.get('id', ''))
        except Exception:
            pass
        return None

    def on_hide(self, button):
        addr = self.find_window()
        if not addr:
            self.reset_timer()
            return
        ws = self.window_workspace(addr) or ''
        if ws.startswith('special'):
            ar = subprocess.run(['hyprctl', 'activeworkspace', '-j'], capture_output=True, text=True)
            wid = 1
            if ar.returncode == 0:
                try:
                    import json
                    wid = json.loads(ar.stdout).get('id', 1)
                except Exception:
                    pass
            subprocess.run(['hyprctl', 'dispatch', 'hl.dsp.window.move({ workspace = %d, window = \"address:%s\", follow = false })' % (wid, addr)])
        else:
            subprocess.run(['hyprctl', 'dispatch', 'hl.dsp.window.move({ workspace = \"special:media\", window = \"address:%s\", follow = false })' % addr])
            self.destroy()
            Gtk.main_quit()
        self.btn_hide.set_label('󰗐' if not ws.startswith('special') else '󰝝')
        self.reset_timer()

window = MediaPopup()
window.connect('delete-event', Gtk.main_quit)
Gtk.main()
"

# Launch the popup (single instance, tracked by pidfile)
echo "$GTK_SCRIPT" | python3 - &
VPID=$!
echo "$VPID" > "$PIDFILE"
wait "$VPID" 2>/dev/null
rm -f "$PIDFILE"