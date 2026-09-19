#!/bin/bash
# Volume slider popup - slides down from under the volume module in waybar

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

set -e

# Only one popup at a time: close any existing instance when reopening
PIDFILE=/tmp/volume-popup.pid
if [ -f "$PIDFILE" ]; then
    OLD=$(cat "$PIDFILE" 2>/dev/null)
    if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null; then
        kill "$OLD" 2>/dev/null
    fi
    rm -f "$PIDFILE"
fi

GTK_SCRIPT="
#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, GLib, GtkLayerShell, Gdk
import subprocess
import os

SLIDE_STEPS = 18
SLIDE_MS = 16

class VolumeSliderWindow(Gtk.Window):
    def __init__(self, initial_volume):
        Gtk.Window.__init__(self)
        self.set_title('Volume')
        self.set_resizable(False)

        display = Gdk.Display.get_default()
        monitor = display.get_monitor(0)
        geo = monitor.get_geometry()
        self.screen_w = geo.width
        self.screen_h = geo.height

        # Position under the waybar volume module (measured: module right edge x=1216)
        self.bar_height = 30
        self.vol_right_edge = 1216 if self.screen_w == 1440 else self.screen_w - 224
        self.target_top = self.bar_height + 4
        self.right_margin = max(0, self.screen_w - self.vol_right_edge)

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_exclusive_zone(self, -1)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, self.right_margin)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, -400)

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        container.set_margin_top(20)
        container.set_margin_bottom(20)
        container.set_margin_start(20)
        container.set_margin_end(20)

        header = Gtk.Label()
        header.set_markup('<span weight=\"bold\">Volume</span>')
        header.set_xalign(0)
        container.add(header)

        slider_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.volume_label = Gtk.Label(label=f'{int(initial_volume * 100)}%')
        top_box.pack_start(self.volume_label, False, False, 0)

        self.slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.slider.set_value(initial_volume * 100)
        self.slider.set_size_request(300, 32)
        self.slider.connect('value-changed', self.on_slider_changed)
        self.slider.connect('button-release-event', self.reset_timer)
        top_box.pack_start(self.slider, True, True, 0)

        slider_box.pack_start(top_box, False, False, 0)

        mute_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.mute_button = Gtk.Button(label='󰝟')
        self.mute_button.set_tooltip_text('Toggle Mute')
        self.mute_button.connect('clicked', self.on_mute_clicked)
        mute_box.pack_start(self.mute_button, False, False, 0)

        mute_label = Gtk.Label(label='Mute')
        mute_label.set_xalign(0)
        mute_box.pack_start(mute_label, False, False, 0)

        slider_box.pack_start(mute_box, False, False, 0)

        container.add(slider_box)

        footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        footer_box.set_margin_top(10)

        presets = [('0%', '0'), ('25%', '25'), ('50%', '50'), ('75%', '75'), ('100%', '100')]
        for label_text, value in presets:
            btn = Gtk.Button(label=label_text)
            btn.set_size_request(60, 28)
            btn.connect('clicked', self.on_preset_clicked, value)
            footer_box.pack_start(btn, False, False, 0)

        container.add(footer_box)

        self.add(container)
        self.show_all()

        self._cancel_slide()
        self._slide_to(self.target_top)
        self._start_timer()

    # ---------- slide in / out ----------
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

    # ---------- idle auto-hide ----------
    def _start_timer(self):
        self._reset_timer = None
        self.reset_timer()

    def reset_timer(self, *args):
        if getattr(self, '_hide_id', None) is not None:
            GLib.source_remove(self._hide_id)
        self._hide_id = GLib.timeout_add_seconds(5, self._close_after_idle)

    def _close_after_idle(self):
        self._hide_id = None
        self._slide_to(-self.get_allocated_height() - 10)
        return False

    # ---------- actions ----------
    def on_slider_changed(self, scale):
        value = scale.get_value()
        self.volume_label.set_text(f'{int(value)}%')
        subprocess.run(['wpctl', 'set-volume', '@DEFAULT_AUDIO_SINK@', f'{value}%'])

    def on_mute_clicked(self, button):
        subprocess.run(['wpctl', 'set-mute', '@DEFAULT_AUDIO_SINK@', 'toggle'])
        self.reset_timer()
        subprocess.run(['sh', '-c', 'wpctl get-volume @DEFAULT_AUDIO_SINK@ | grep -q \"MUTED\" && echo \"󰝟\" || echo \"󰕾\"'],
                      stdout=lambda x: button.set_label(x.decode().strip().splitlines()[-1]))

    def on_preset_clicked(self, button, value):
        self.slider.set_value(float(value))
        self.reset_timer()

result = subprocess.run(['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@'],
                       capture_output=True, text=True)
text = result.stdout.strip()
if 'MUTED' in text:
    volume = 0.0
else:
    volume = float(text.split()[1].replace('%', '')) / 100

window = VolumeSliderWindow(volume)
window.connect('delete-event', Gtk.main_quit)
Gtk.main()
"

# Launch the popup (single instance, tracked by pidfile)
echo "$GTK_SCRIPT" | python3 - &
VPID=$!
echo "$VPID" > "$PIDFILE"
wait "$VPID" 2>/dev/null
rm -f "$PIDFILE"