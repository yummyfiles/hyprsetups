#!/bin/bash
# Audio visualizer + idle fade. The kitty cava window renders the live bars;
# on idle we hide the kitty window and fade the frozen bars away line-by-line
# from both edges (no covering background), then grow them back on resume.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

set -e

PIDFILE=/tmp/cava-fade.pid
if [ -f "$PIDFILE" ]; then
    OLD=$(cat "$PIDFILE" 2>/dev/null)
    if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null; then
        kill "$OLD" 2>/dev/null
        rm -f "$PIDFILE"
        exit 0
    fi
    rm -f "$PIDFILE"
fi

# Cava raw-config: outputs the per-bar spectrum on stdout (16-bit LE, raw_format 0)
RAWC=/tmp/cava-raw.conf
cat > "$RAWC" <<'EOF'
[general]
bars = 52
framerate = 60
autosens = 1
mono_opt = right
input_delay = 2

[output]
method = raw
raw_format = 0
channels = mono
mono_option = right
lower_cutoff_freq = 60
higher_cutoff_freq = 16000
EOF

GTK_SCRIPT="
#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, GLib, GtkLayerShell, Gdk
import subprocess, threading, os, json

POLL_MS = 350
STEP_MS = 16
WIDTH, HEIGHT = 1440, 120
NBARS = 52
BAR_W = 18
PITCH = WIDTH // NBARS
X0 = (WIDTH - (NBARS - 1) * PITCH - BAR_W) // 2
RAWC = '/tmp/cava-raw.conf'
FADE_STEPS = 24           # ~390ms full sweep
SWEEP = 0.62              # fraction before the LAST (center) bar starts shrinking
DUR = 0.30                # per-bar shrink duration (fraction of sweep)
CAVA_CLASS = 'cava-bar'
CAVA_HIDDEN_WS = 'special:cava'

def audio_active():
    try:
        r = subprocess.run(['playerctl', '-p', 'spotify', 'status'], capture_output=True, text=True, timeout=1.5)
        if r.returncode == 0 and r.stdout.strip() == 'Playing':
            return True
    except Exception:
        pass
    try:
        r = subprocess.run(['playerctl', '-a', 'status'], capture_output=True, text=True, timeout=1.5)
        for line in r.stdout.splitlines():
            if line.split()[-1] == 'Playing':
                return True
    except Exception:
        pass
    return False

def hypr_dispatch(lua):
    try:
        subprocess.run(['hyprctl', 'dispatch', lua], capture_output=True, text=True, timeout=2)
    except Exception:
        pass

def cava_window_addr():
    try:
        out = subprocess.run(['hyprctl', 'clients', '-j'], capture_output=True, text=True, timeout=2).stdout
        for w in json.loads(out):
            if w.get('class') == CAVA_CLASS:
                return w.get('address')
    except Exception:
        pass
    return None

def active_ws():
    try:
        out = subprocess.run(['hyprctl', 'activeworkspace', '-j'], capture_output=True, text=True, timeout=2).stdout
        return json.loads(out).get('id', 1)
    except Exception:
        return 1

def hide_kitty():
    a = cava_window_addr()
    if a:
        hypr_dispatch('hl.dsp.window.move({ workspace = \"%s\", window = \"address:%s\", follow = false })' % (CAVA_HIDDEN_WS, a))

def kitty_hidden():
    try:
        out = subprocess.run(['hyprctl', 'clients', '-j'], capture_output=True, text=True, timeout=2).stdout
        for w in json.loads(out):
            if w.get('class') == CAVA_CLASS:
                return (w.get('workspace') or {}).get('name') == CAVA_HIDDEN_WS
    except Exception:
        pass
    return False

def show_kitty():
    a = cava_window_addr()
    if not a:
        return
    hypr_dispatch('hl.dsp.window.move({ workspace = %d, window = \"address:%s\", follow = false })' % (active_ws(), a))
    hypr_dispatch('hl.dsp.window.alter_zorder({ mode = \"bottom\", window = \"address:%s\" })' % a)

def kill_kitty():
    subprocess.run(['pkill', '-f', 'app-id cava-bar'], capture_output=True)

def start_kitty():
    cava_sh = os.path.expanduser('~/.config/waybar/scripts/cava.sh')
    subprocess.Popen(['sh', cava_sh], start_new_session=True)

class BarOverlay(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_resizable(False)
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.BOTTOM)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_exclusive_zone(self, -1)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        screen = self.get_screen()
        if screen.is_composited():
            self.set_visual(screen.get_rgba_visual())
        self.set_app_paintable(True)
        self.set_size_request(WIDTH, HEIGHT)

        self.da = Gtk.DrawingArea()
        self.da.set_size_request(WIDTH, HEIGHT)
        self.da.connect('draw', self.on_draw)
        self.add(self.da)

        self.live = [0.0] * NBARS
        self.height = [0.0] * NBARS      # currently drawn heights
        self.base = [0.0] * NBARS        # frozen frame for fade
        self.mode = 'idle'               # 'idle' | 'playing' | 'fade' | 'rise'
        self.dir = 0
        self.step = 0
        self.lock = threading.Lock()
        self._reader_stop = False
        self._kitty_killed = False
        self.show_all()
        self._start_reader()
        GLib.timeout_add(STEP_MS, self.tick)
        if audio_active():
            self.mode = 'playing'        # kitty cava window renders the live bars
            show_kitty()                 # reconcile if a previous idle hid it
        else:
            hide_kitty()
            GLib.timeout_add(2000, lambda: (self._kill_idle(), False)[1] if not audio_active() else True)

    # -- cava raw reader -------------------------------------------------
    def _start_reader(self):
        def run():
            self._cava_proc = None
            try:
                p = subprocess.Popen(['cava', '-p', RAWC], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                self._cava_proc = p
            except Exception:
                return
            buf = b''
            NB = NBARS * 2  # 16-bit little-endian, 2 bytes per bar
            self.sens = 1.0
            try:
                while not self._reader_stop:
                    chunk = p.stdout.read(4096)
                    if not chunk:
                        break
                    buf += chunk
                    n = len(buf) // NB
                    if n:
                        raw = buf[:n * NB]
                        buf = buf[n * NB:]
                        frames = [list(raw[i * NB:(i + 1) * NB]) for i in range(n)]
                        last = frames[-1]
                        vals = [last[2 * i] + 256 * last[2 * i + 1] for i in range(NBARS)]
                        peak = max(vals)
                        if peak > 0:
                            self.sens = max(self.sens * 0.995, peak)  # autosens-ish
                        with self.lock:
                            s = self.sens
                            self.live = [min(1.0, v / s) * (HEIGHT - 4) for v in vals]
            except Exception:
                pass
            finally:
                try:
                    p.terminate()
                except Exception:
                    pass
        threading.Thread(target=run, daemon=True).start()

    def _stop_reader(self):
        self._reader_stop = True
        if getattr(self, '_cava_proc', None):
            try:
                self._cava_proc.terminate()
            except Exception:
                pass
        self._cava_proc = None

    def _kill_idle(self):
        self._kitty_killed = True
        kill_kitty()
        self._stop_reader()

    def _revive(self):
        start_kitty()
        if not self._cava_proc:
            self._reader_stop = False
            self._start_reader()
        self._kitty_killed = False

        def _bring():
            if self.mode == 'playing':
                show_kitty()
            return False
        GLib.timeout_add(1500, _bring)

    # -- timeline --------------------------------------------------------
    def edge_factor(self, i):
        # 0 for outermost bars, 1 for center bars -> outer bars act first
        d = min(i, NBARS - 1 - i)
        return d / ((NBARS - 1) // 2)

    def tick(self):
        with self.lock:
            live = list(self.live)
        if self.mode == 'playing':
            self.height = [0.0] * NBARS   # kitty renders the live bars
        elif self.mode == 'idle':
            self.height = [0.0] * NBARS   # nothing visible while idle
        elif self.mode in ('fade', 'rise'):
            self.step += 1
            proj = self.step / FADE_STEPS
            finished = True
            heights = []
            for i in range(NBARS):
                delay = SWEEP * self.edge_factor(i)
                seg = max(0.0, min(1.0, (proj - delay) / DUR))
                if self.dir > 0:      # rising: grow toward live heights
                    f = seg
                    h = live[i]
                else:                 # fading: shrink the frozen frame to 0
                    f = 1.0 - seg
                    h = self.base[i]
                heights.append(max(0.0, h * f))
                if seg < 1.0:
                    finished = False
            self.height = heights
            if finished:
                if self.dir > 0:
                    self.mode = 'playing'
                    show_kitty()       # hand rendering back to kitty
                else:
                    self.mode = 'idle'
                    self._kill_idle()
        self.da.queue_draw()
        return GLib.SOURCE_CONTINUE

    def animate(self, direction, base=None):
        # direction: +1 rise, -1 fade (bars from the frozen frame)
        self.mode = 'fade' if direction < 0 else 'rise'
        self.dir = direction
        self.step = 0
        if base is not None:
            with self.lock:
                self.base = list(base)

    def on_draw(self, da, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_source_rgb(0.866, 0.866, 0.866)
        for i in range(NBARS):
            h = self.height[i]
            if h <= 0.5:
                continue
            x = X0 + i * PITCH
            cr.rectangle(x, HEIGHT - h, BAR_W, h)
        cr.fill()
        return False

def main():
    overlay = BarOverlay()
    idle_count = 0

    def quit(*_):
        Gtk.main_quit()
        return False
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, 15, quit)  # SIGTERM
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, 2, quit)   # SIGINT

    def poll():
        nonlocal idle_count
        active = audio_active()
        if active:
            if overlay._kitty_killed or not (subprocess.run(['pgrep','-f','app-id cava-bar'],capture_output=True).stdout.strip()):
                overlay._revive()
            idle_count = 0
            if overlay.mode in ('idle', 'fade'):
                overlay.animate(1)      # bars grow back line-by-line from edges
            elif overlay.mode == 'playing' and kitty_hidden():
                show_kitty()            # recovery: a previous show move may have failed
        else:
            idle_count += 1
            if idle_count >= 2 and overlay.mode in ('playing', 'rise'):
                with overlay.lock:
                    base = list(overlay.live)
                hide_kitty()            # stop kitty from showing idle dots
                overlay.animate(-1, base)  # fade bars away line-by-line from edges
            elif overlay.mode == 'idle' and not kitty_hidden():
                hide_kitty()            # kitty may have registered after startup
        return GLib.SOURCE_CONTINUE

    GLib.timeout_add(POLL_MS, poll)
    Gtk.main()

main()
"

echo "$GTK_SCRIPT" | python3 - &
VPID=$!
echo "$VPID" > "$PIDFILE"
wait "$VPID" 2>/dev/null
rm -f "$PIDFILE"