#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GLib', '2.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell

import dbus
import dbus.service
import dbus.mainloop.glib
import time
import socket
import os
import shutil
import atexit

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

# Single instance: a newer copy retires any previous daemon we find.
PIDFILE = '/tmp/notify-daemon.pid'
try:
    with open(PIDFILE) as f:
        _old = int(f.read().strip())
except (OSError, ValueError):
    _old = None
if _old and _old != os.getpid():
    try:
        os.kill(_old, 15)
        time.sleep(0.3)
    except (ProcessLookupError, PermissionError):
        pass
with open(PIDFILE, 'w') as f:
    f.write(str(os.getpid()))
def _cleanup_pidfile():
    if os.path.exists(PIDFILE):
        try:
            with open(PIDFILE) as f:
                if f.read().strip() == str(os.getpid()):
                    os.unlink(PIDFILE)
        except OSError:
            pass
atexit.register(_cleanup_pidfile)

SOCK_PATH = '/tmp/notify-sidebar.sock'
NOTIF_BUS = dbus.service.BusName('org.freedesktop.Notifications', bus=dbus.SessionBus())

APP_ICONS = {
    'firefox': '\ue921',
    'Firefox': '\uf269',
    'chromium': '\ue898',
    'Spotify': '\uf1bc',
    'Telegram': '\uf2c6',
    'Discord': '\uf499',
    'kitty': '\uf489',
    'Alacritty': '\uf489',
    'Code': '\uf121',
    'Slack': '\uf198',
    'YouTube': '\uf167',
    'WhatsApp': '\uf232',
    'Signal': '\uf12e',
    'Thunderbird': '\uf2b6',
    'battery': '\uf240',
    'update': '\uf0aa',
    'nm-applet': '\uf1eb',
    'libnotify': '\uf0f3',
}
DEFAULT_ICON = '\uf0f3'

# group-state per app: True = expanded
expanded_apps = set()


class LineSwitch(Gtk.EventBox):
    def __init__(self, active=False, on_change=None):
        super().__init__()
        self._active = active
        self._on_change = on_change
        self.set_size_request(56, 26)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("button-press-event", self._on_click)
        self._area = Gtk.DrawingArea()
        self.add(self._area)
        self._area.connect("draw", self._draw)
        self.show_all()

    def set_active(self, v):
        self._active = bool(v)
        self._area.queue_draw()

    def get_active(self):
        return self._active

    def _on_click(self, w, e):
        self._active = not self._active
        self._area.queue_draw()
        if self._on_change:
            self._on_change(self._active)
        return True

    def _draw(self, da, cr):
        w = da.get_allocated_width()
        h = da.get_allocated_height()
        m = 2.0          # outer margin so the border isn't clipped
        bw = 2.0         # border width
        inset = 4.0      # thumb inset from the track edge
        # track
        cr.set_line_width(bw)
        if self._active:
            cr.set_source_rgb(1, 1, 1)
            cr.rectangle(m, m, w - 2 * m, h - 2 * m)
            cr.fill()
        else:
            cr.set_source_rgb(0, 0, 0)
            cr.rectangle(m, m, w - 2 * m, h - 2 * m)
            cr.fill()
            cr.set_source_rgb(1, 1, 1)
            cr.rectangle(m + bw / 2.0, m + bw / 2.0,
                         w - 2 * m - bw, h - 2 * m - bw)
            cr.stroke()
        # thumb
        ts = h - 2 * inset
        tx = (w - inset - ts) if self._active else inset
        if self._active:
            cr.set_source_rgb(0, 0, 0)
        else:
            cr.set_source_rgb(1, 1, 1)
        cr.rectangle(tx, inset, ts, ts)
        cr.fill()
        return False


class NotifyDaemon(dbus.service.Object):
    def __init__(self):
        dbus.service.Object.__init__(
            self, NOTIF_BUS, '/org/freedesktop/Notifications')
        self.notifications = []
        self.window = None
        self.notif_box = None
        self.visible = False
        self.sidebar_width = 400
        self.hide_timer = None
        self.dnd = False
        self.setup_socket()

    def send_to_eww(self, command):
        """Send command to eww with proper window ordering"""
        import subprocess
        subprocess.run(["eww", "update", command], check=False)

    def setup_socket(self):
        try:
            os.unlink(SOCK_PATH)
        except OSError:
            pass
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.bind(SOCK_PATH)
        self.sock.setblocking(False)
        GLib.io_add_watch(self.sock.fileno(), GLib.IO_IN, self.on_socket_data)

    def on_socket_data(self, fd, condition):
        try:
            self.sock.recv(1024)
        except Exception:
            pass
        self.toggle()
        return True

    def toggle(self):
        self.ensure_window()
        if self.visible:
            self.window.hide()
            self.visible = False
            self.cancel_hide_timer()
        else:
            self.render()
            self.window.show_all()
            self.visible = True
            self.schedule_hide(6.0)

    # ---------- D-Bus methods ----------
    @dbus.service.method('org.freedesktop.Notifications',
                         in_signature='', out_signature='as')
    def GetCapabilities(self):
        return ['body', 'actions']

    @dbus.service.method('org.freedesktop.Notifications',
                         in_signature='', out_signature='ssss')
    def GetServerInformation(self):
        return ('yummyfiles-desk', 'YummyDev', '1.0', '1.2')

    @dbus.service.method('org.freedesktop.Notifications',
                         in_signature='susssasa{sv}i', out_signature='u')
    def Notify(self, app_name, replaces_id, app_icon, summary, body,
               actions, hints, expire_timeout):
        nid = int(time.time() * 1000) % 100000000
        self.notifications.append({
            'id': nid,
            'app': app_name if app_name else 'Unknown',
            'icon': app_icon or '',
            'summary': summary or '',
            'body': body or '',
            'ts': time.time(),
        })
        self.notifications = self.notifications[-15:]
        self.ensure_window()
        self.render()
        if self.dnd:
            return nid
        self.window.show_all()
        self.visible = True
        self.schedule_hide(6.0)
        return nid

    @dbus.service.method('org.freedesktop.Notifications',
                         in_signature='u', out_signature='')
    def CloseNotification(self, notification_id):
        self.notifications = [n for n in self.notifications
                              if n['id'] != notification_id]
        if self.window is not None:
            self.render()
        self.notif_closed(notification_id, 3)

    @dbus.service.signal('org.freedesktop.Notifications', signature='uu')
    def notif_closed(self, nid, reason):
        pass

    @dbus.service.signal('org.freedesktop.Notifications', signature='us')
    def action_invoked(self, nid, action_key):
        pass

    # ---------- Helpers ----------
    @staticmethod
    def rel_time(ts):
        age = int(time.time() - ts)
        if age < 60:
            return f"{age}s"
        if age < 3600:
            return f"{age // 60}m"
        return f"{age // 3600}h"

    def ensure_window(self):
        if self.window is None:
            self.build_window()

    def app_icon_label(self, app, size_px=32):
        name = APP_ICONS.get(app, DEFAULT_ICON)
        lbl = Gtk.Label(label=name)
        lbl.set_size_request(size_px, size_px)
        ctx = lbl.get_style_context()
        ctx.add_class("appicon")
        return lbl

    def build_window(self):
        win = Gtk.Window()
        win.set_title("yummyfiles-notifications")
        win.set_type_hint(Gdk.WindowTypeHint.DOCK)

        GtkLayerShell.init_for_window(win)
        GtkLayerShell.set_layer(win, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_keyboard_mode(win, GtkLayerShell.KeyboardMode.ON_DEMAND)
        GtkLayerShell.set_exclusive_zone(win, -1)
        GtkLayerShell.set_margin(win, GtkLayerShell.Edge.TOP, 32)
        GtkLayerShell.set_margin(win, GtkLayerShell.Edge.RIGHT, 8)

        display = Gdk.Display.get_default()
        monitor = display.get_monitor(0)
        geo = monitor.get_geometry()
        self.screen_height = geo.height

        win.set_default_size(self.sidebar_width, self.screen_height)
        win.set_size_request(self.sidebar_width, -1)

        # Make the sidebar transparent to clicks outside, but keep internal widgets clickable
        win.set_app_paintable(True)
        win.set_visual(Gdk.Screen.get_default().get_rgba_visual())

        # Opaque black backdrop: without this, the rgba visual + transparent CSS
        # composites the whole panel see-through.
        def paint_black(widget, cr):
            cr.set_source_rgb(0, 0, 0)
            cr.paint()
            return False
        win.connect("draw", paint_black)
        if hasattr(win, "set_cursor"):
            win.set_cursor(Gdk.Cursor.new_for_display(
                Gdk.Display.get_default(), Gdk.CursorType.LEFT_PTR))

        css = b"""
        * {
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 13px;
            color: #FFFFFF;
            background-color: transparent;
        }
        window {
            background-color: #000000;
            border-left: 2px solid #FFFFFF;
        }
        window, scrolledwindow, viewport, box, eventbox, label {
            background-color: #000000;
        }
        .header {
            padding: 12px 16px;
            border-bottom: 2px solid #FFFFFF;
        }
        .header-title {
            font-weight: bold;
            font-size: 15px;
        }
        .header-title iconb {
            font-size: 16px;
        }
        .close-btn {
            font-size: 18px;
            padding: 4px 10px;
            color: #FFFFFF;
        }
        .close-btn:hover {
            color: #000000;
            background: #FFFFFF;
        }
        .dnd-row {
            padding: 10px 16px;
            border-bottom: 1px solid #FFFFFF;
            background: #000000;
        }
        .dnd-row-label {
            font-size: 12px;
            font-weight: bold;
            letter-spacing: 1px;
        }
        .empty-box {
            padding: 60px 20px;
        }
        .empty-icon {
            font-size: 40px;
            opacity: 0.35;
        }
        .empty-text {
            font-size: 13px;
            font-weight: bold;
            opacity: 0.35;
            letter-spacing: 1px;
        }
        .group-item {
            border-bottom: 1px solid #FFFFFF;
        }
        .group-item:hover {
            background-color: #FFFFFF;
        }
        .group-item:hover * {
            color: #000000;
            opacity: 1;
        }
        .group-pad {
            padding: 10px 14px;
        }
        .group-app {
            font-weight: bold;
            font-size: 13px;
        }
        .group-count {
            font-size: 11px;
            padding: 1px 8px;
            border-radius: 0px;
        }
        .group-preview {
            font-size: 12px;
            opacity: 0.6;
        }
        .group-chevron {
            font-size: 16px;
        }
        .appicon {
            font-size: 18px;
            min-width: 34px;
        }
        .notif-item {
            border-bottom: 1px solid #FFFFFF;
        }
        .notif-item:hover {
            background-color: #FFFFFF;
        }
        .notif-item:hover * {
            color: #000000;
        }
        .notif-pad {
            padding: 8px 12px;
            background-color: transparent;
        }
        .notif-app {
            font-weight: bold;
            font-size: 11px;
            opacity: 0.7;
        }
        .notif-summary {
            font-weight: bold;
            font-size: 12px;
        }
        .notif-body {
            font-size: 12px;
            opacity: 0.65;
        }
        .notif-time {
            font-size: 10px;
            opacity: 0.4;
            font-weight: bold;
        }
        .footer {
            padding: 8px 0;
            border-top: 2px solid #FFFFFF;
        }
        .footer-btn {
            font-size: 13px;
            padding: 6px 8px;
        }
        .footer-btn:hover {
            background: #FFFFFF;
            color: #000000;
        }
        .footer-btn-on {
            background: #FFFFFF;
            color: #000000;
        }
        .footer-btn-on:hover {
            background: #000000;
            color: #FFFFFF;
        }
        .sep {
            background-color: rgba(255,255,255,0.25);
            min-height: 1px;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        win.add(root)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header.get_style_context().add_class("header")
        title = Gtk.Label()
        title.set_markup("\uf0f3  <span weight='bold'>NOTIFICATIONS</span>")
        title.get_style_context().add_class("header-title")
        title.set_halign(Gtk.Align.START)
        header.pack_start(title, True, True, 0)

        close_btn = Gtk.Button(label="\uf00d")
        close_btn.get_style_context().add_class("close-btn")
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.connect("clicked", lambda b: self.toggle())

        header.pack_end(close_btn, False, False, 0)
        root.pack_start(header, False, False, 0)

        # Do Not Disturb row (its own row below the header, above the list)
        dnd_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        dnd_row.get_style_context().add_class("dnd-row")
        dnd_label = Gtk.Label(label="Do Not Disturb")
        dnd_label.get_style_context().add_class("dnd-row-label")
        dnd_label.set_halign(Gtk.Align.START)
        dnd_row.pack_start(dnd_label, True, True, 0)
        self.dnd_switch = LineSwitch(active=self.dnd, on_change=self.on_dnd_switch)
        dnd_row.pack_end(self.dnd_switch, False, False, 0)
        root.pack_start(dnd_row, False, False, 0)

        # Scroll
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        root.pack_start(scrolled, True, True, 0)
        self.notif_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.notif_box.set_vexpand(False)
        self.notif_box.set_valign(Gtk.Align.START)
        self.notif_box.set_hexpand(True)
        scrolled.add(self.notif_box)

        # Footer
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        footer.get_style_context().add_class("footer")
        footer.set_margin_start(8)
        footer.set_margin_end(8)

        clear_btn = Gtk.Button(label="\uf2d3  Clear All")
        clear_btn.get_style_context().add_class("footer-btn")
        clear_btn.set_relief(Gtk.ReliefStyle.NONE)
        clear_btn.connect("clicked", lambda b: self.clear_all())

        footer.pack_start(clear_btn, True, True, 0)
        root.pack_start(footer, False, False, 0)

        win.connect("leave-notify-event", lambda w, e: self.schedule_hide(6.0))
        win.connect("enter-notify-event", lambda w, e: self.cancel_hide_timer())
        win.connect("key-press-event", self.on_key)
        win.show_all()
        win.hide()
        self.window = win

    def on_key(self, widget, event):
        if event.keyval == 0xFF1B:  # Escape
            self.toggle()
            return True
        return False

    def cancel_hide_timer(self):
        if self.hide_timer is not None:
            GLib.source_remove(self.hide_timer)
            self.hide_timer = None

    def schedule_hide(self, seconds):
        self.cancel_hide_timer()
        self.hide_timer = GLib.timeout_add_seconds(int(seconds), self.do_hide)

    def do_hide(self):
        self.hide_timer = None
        if self.visible:
            self.window.hide()
            self.visible = False
        return False

    def clear_all(self):
        self.notifications.clear()
        expanded_apps.clear()
        self.render()
        self.window.hide()
        self.visible = False

    def toggle_dnd(self):
        self.dnd = not self.dnd
        if hasattr(self, 'dnd_switch') and self.dnd_switch.get_active() != self.dnd:
            self.dnd_switch.set_active(self.dnd)
        self.update_dnd_btn()
        if not self.dnd:
            self.window.show_all()
            self.visible = True
            self.schedule_hide(6.0)

    def on_dnd_switch(self, active):
        self.dnd = active
        self.update_dnd_btn()
        if not self.dnd and getattr(self, 'window', None) is not None:
            self.window.show_all()
            self.visible = True
            self.schedule_hide(6.0)

    def update_dnd_btn(self):
        if not hasattr(self, 'dnd_switch'):
            return
        self.dnd_switch.set_active(self.dnd)

    # ---------- Grouping ----------
    def grouped(self):
        order = {}
        for n in self.notifications:
            order.setdefault(n['app'], []).append(n)
        # sort groups by most-recent ts, newest first
        return sorted(order.items(),
                      key=lambda kv: max(n['ts'] for n in kv[1]),
                      reverse=True)

    def render(self):
        for child in self.notif_box.get_children():
            self.notif_box.remove(child)

        groups = self.grouped()
        if not groups:
            self.notif_box.set_vexpand(True)
            self.notif_box.set_valign(Gtk.Align.FILL)
            self.render_empty()
        else:
            self.notif_box.set_vexpand(False)
            self.notif_box.set_valign(Gtk.Align.START)
            for app, items in groups:
                if app in expanded_apps:
                    self.render_expanded(app, items)
                else:
                    self.render_group(app, items)
            # cleanup: drop expanded state for apps that vanished
            apps = {app for app, _ in groups}
            for app in list(expanded_apps):
                if app not in apps:
                    expanded_apps.discard(app)
        self.notif_box.show_all()

    def render_empty(self):
        eb = Gtk.EventBox()
        eb.get_style_context().add_class("empty-box")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        box.set_vexpand(True)
        icon = Gtk.Label(label="\uf0f3")
        icon.get_style_context().add_class("empty-icon")
        text = Gtk.Label(label="NO NOTIFICATIONS")
        text.get_style_context().add_class("empty-text")
        box.pack_start(icon, False, False, 0)
        box.pack_start(text, False, False, 0)
        eb.add(box)
        self.notif_box.pack_start(eb, True, True, 0)

    def render_group(self, app, items):
        eb = Gtk.EventBox()
        eb.get_style_context().add_class("group-item")
        eb.set_vexpand(False)
        pad = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        pad.get_style_context().add_class("group-pad")
        eb.add(pad)

        pad.pack_start(self.app_icon_label(app), False, False, 0)

        mid = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        app_lbl = Gtk.Label(label=app, xalign=0)
        app_lbl.get_style_context().add_class("group-app")
        n = len(items)
        cnt = Gtk.Label(label=str(n))
        cnt.get_style_context().add_class("group-count")
        if n > 1:
            cnt.set_markup(f"<b>{n}</b>")
        top.pack_start(app_lbl, True, True, 0)
        top.pack_end(cnt, False, False, 0)
        mid.pack_start(top, False, False, 0)

        # preview = latest summary/body
        latest = max(items, key=lambda x: x['ts'])
        preview_text = latest['summary'] or latest['body'] or ''
        preview = Gtk.Label(label=preview_text, xalign=0, ellipsize=True)
        preview.get_style_context().add_class("group-preview")
        preview.set_max_width_chars(24)
        preview.set_line_wrap(True)
        mid.pack_start(preview, False, False, 0)
        pad.pack_start(mid, True, True, 0)

        chev = Gtk.Label(label="\uf054", xalign=1)
        chev.get_style_context().add_class("group-chevron")
        chev.set_valign(Gtk.Align.CENTER)
        pad.pack_end(chev, False, False, 0)

        eb.connect("button-press-event", lambda w, e, a=app: self.expand(a))
        self.notif_box.pack_start(eb, False, False, 0)

    def render_expanded(self, app, items):
        eb = Gtk.EventBox()
        eb.get_style_context().add_class("group-item")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        eb.add(box)

        # header (click to collapse)
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        head.get_style_context().add_class("group-pad")
        head.pack_start(self.app_icon_label(app), False, False, 0)
        hmid = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        htop = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        app_lbl = Gtk.Label(label=app, xalign=0)
        app_lbl.get_style_context().add_class("group-app")
        cnt = Gtk.Label(label=str(len(items)))
        cnt.get_style_context().add_class("group-count")
        htop.pack_start(app_lbl, True, True, 0)
        htop.pack_end(cnt, False, False, 0)
        hmid.pack_start(htop, False, False, 0)
        tsum = Gtk.Label(label="Expanded", xalign=0)
        tsum.get_style_context().add_class("group-preview")
        hmid.pack_start(tsum, False, False, 0)
        head.pack_start(hmid, True, True, 0)
        chev = Gtk.Label(label="\uf078", xalign=1)
        chev.get_style_context().add_class("group-chevron")
        chev.set_valign(Gtk.Align.CENTER)
        head.pack_end(chev, False, False, 0)
        head.connect("button-press-event",
                     lambda w, e, a=app: self.collapse(a))
        box.pack_start(head, False, False, 0)

        sep = Gtk.Box()
        sep.get_style_context().add_class("sep")
        sep.set_size_request(-1, 1)
        box.pack_start(sep, False, False, 0)

        for notif in sorted(items, key=lambda x: x['ts'], reverse=True):
            self.render_notif(box, notif)

        self.notif_box.pack_start(eb, False, False, 0)

    def render_notif(self, parent, notif):
        eb = Gtk.EventBox()
        eb.get_style_context().add_class("notif-item")
        eb.set_vexpand(False)
        pad = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        pad.get_style_context().add_class("notif-pad")
        eb.add(pad)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        app = Gtk.Label(label=notif['app'], xalign=0)
        app.get_style_context().add_class("notif-app")
        t = Gtk.Label(label=self.rel_time(notif['ts']), xalign=1)
        t.get_style_context().add_class("notif-time")
        top.pack_start(app, True, True, 0)
        top.pack_end(t, False, False, 0)
        pad.pack_start(top, False, False, 0)

        if notif['summary']:
            s = Gtk.Label(label=notif['summary'], xalign=0)
            s.get_style_context().add_class("notif-summary")
            s.set_line_wrap(True)
            pad.pack_start(s, False, False, 0)
        if notif['body']:
            b = Gtk.Label(label=notif['body'], xalign=0)
            b.get_style_context().add_class("notif-body")
            b.set_line_wrap(True)
            pad.pack_start(b, False, False, 0)

        eb.connect("button-press-event",
                   lambda w, e, n=notif: self.dismiss(n))
        parent.pack_start(eb, False, False, 0)

    # ---------- Actions ----------
    def expand(self, app):
        expanded_apps.add(app)
        self.render()
        self.window.show_all()

    def collapse(self, app):
        expanded_apps.discard(app)
        self.render()
        self.window.show_all()

    def dismiss(self, notif):
        if notif in self.notifications:
            self.notifications.remove(notif)
        self.render()
        self.window.show_all()


def main():
    daemon = NotifyDaemon()
    print("notify-daemon: registered org.freedesktop.Notifications", flush=True)
    Gtk.main()


if __name__ == "__main__":
    main()