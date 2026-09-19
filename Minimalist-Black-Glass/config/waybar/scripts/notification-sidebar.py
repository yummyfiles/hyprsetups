#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GLib', '2.0')
gi.require_version('GtkLayerShell', '0.1')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Gdk, GLib, Gio, Pango, GtkLayerShell
import json
import subprocess
import os
import sys
import fcntl
import socket

SOCKET_PATH = "/tmp/notification-sidebar.sock"

class AngularCard(Gtk.Overlay):
    def __init__(self, title, body="", icon="󰂚", height=90):
        super().__init__()
        self.slant = max(14, int(height * 0.28))
        self.da = Gtk.DrawingArea()
        self.da.set_size_request(392, height)
        self.da.connect("draw", self._on_draw)
        self.add(self.da)

        inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        inner.set_margin_start(28)
        inner.set_margin_end(16)
        inner.set_margin_top(0)
        inner.set_margin_bottom(0)
        inner.set_valign(Gtk.Align.CENTER)

        self.icon = Gtk.Label(label=icon)
        self.icon.get_style_context().add_class("notif-icon")
        self.icon.set_valign(Gtk.Align.CENTER)
        inner.pack_start(self.icon, False, False, 0)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_valign(Gtk.Align.CENTER)
        text_box.set_hexpand(True)
        title_label = Gtk.Label(label=title)
        title_label.set_halign(Gtk.Align.START)
        title_label.set_xalign(0)
        title_label.set_ellipsize(Pango.EllipsizeMode.END)
        title_label.get_style_context().add_class("notif-title")
        text_box.pack_start(title_label, False, False, 0)
        if body:
            body_label = Gtk.Label(label=body)
            body_label.set_halign(Gtk.Align.START)
            body_label.set_xalign(0)
            body_label.set_ellipsize(Pango.EllipsizeMode.END)
            body_label.get_style_context().add_class("notif-body")
            text_box.pack_start(body_label, False, False, 0)
        inner.pack_start(text_box, True, True, 0)

        self.add_overlay(inner)
        inner.show_all()
        self.da.show()

    def _on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        s = float(self.slant)
        cr.move_to(s, 0.5)
        cr.line_to(w - 0.5, 0.5)
        cr.line_to(w - 0.5, h - 0.5)
        cr.line_to(s, h - 0.5)
        cr.line_to(0.5, h - s)
        cr.line_to(0.5, s)
        cr.close_path()
        cr.set_source_rgb(0, 0, 0)
        cr.fill_preserve()
        cr.set_source_rgb(1, 1, 1)
        cr.set_line_width(1.0)
        cr.stroke()

class NotificationSidebar(Gtk.Window):
    def __init__(self):
        super().__init__()
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, True)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_name("notification-sidebar")

        display = Gdk.Display.get_default()
        monitor = display.get_monitor(0)
        geometry = monitor.get_geometry()
        self.screen_width = geometry.width
        self.screen_height = geometry.height
        self.sidebar_width = 420

        self.set_size_request(self.sidebar_width, self.screen_height)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, -self.sidebar_width)

        self.setup_css()
        self.build_ui()
        self.setup_socket()

        self.anim_id = None
        self.visible = False

        self.notifications = []
        self.dnd = False
        self.load_notifications()
        self.connect("key-press-event", self.on_key_press)
        self.add_events(Gdk.EventMask.KEY_PRESS_MASK)

    def setup_css(self):
        css = b"""
        * {
            font-family: "JetBrainsMono Nerd Font", monospace;
            color: #FFFFFF;
            background-color: #000000;
            border-radius: 0;
            border-width: 0;
            box-shadow: none;
            outline: none;
            text-shadow: none;
            -gtk-icon-shadow: none;
        }

        window#notification-sidebar {
            background-color: #000000;
            border: 1px solid #FFFFFF;
        }

        .header-title {
            font-size: 29px;
            font-weight: bold;
            color: #FFFFFF;
        }

        .header-rule {
            background-color: #FFFFFF;
        }

        .dnd-label {
            font-family: sans-serif;
            font-size: 26px;
            color: #FFFFFF;
        }

        .dnd-toggle {
            background-image: none;
            background-color: #000000;
            border: 2px solid #FFFFFF;
            border-radius: 0;
            padding: 0;
            margin: 0;
            min-width: 0;
            min-height: 0;
        }
        .dnd-toggle:hover {
            background-color: #000000;
            border: 2px solid #FFFFFF;
        }
        .dnd-toggle.dnd-on {
            background-color: #FFFFFF;
            border: 2px solid #FFFFFF;
        }
        .dnd-knob {
            background-color: #FFFFFF;
            border: none;
            border-radius: 0;
            min-width: 26px;
            min-height: 26px;
            margin: 6px;
        }
        .dnd-toggle.dnd-on .dnd-knob {
            background-color: #000000;
        }

        .empty-bell {
            font-size: 90px;
            color: #777777;
        }
        .empty-label {
            font-size: 27px;
            color: #777777;
        }

        .notif-icon {
            font-size: 26px;
            color: #FFFFFF;
        }
        .notif-title {
            font-size: 16px;
            font-weight: bold;
            color: #FFFFFF;
        }
        .notif-body {
            font-size: 13px;
            color: #AAAAAA;
        }

        scrollbar {
            background: #000000;
            border: none;
        }
        scrollbar trough {
            background: #000000;
            border: none;
            border-radius: 0;
        }
        scrollbar slider {
            background: #FFFFFF;
            border: none;
            border-radius: 0;
            min-width: 3px;
            min-height: 3px;
            margin: 0;
        }
        scrollbar.vertical slider {
            min-width: 3px;
        }
        scrollbar button {
            background: #000000;
            border: none;
            min-width: 0;
            min-height: 0;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def build_ui(self):
        self.set_title("Notifications")
        self.set_decorated(False)
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.box.set_name("notification-sidebar")
        self.add(self.box)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        header.set_margin_top(40)
        title = Gtk.Label(label="NOTIFICATIONS")
        title.get_style_context().add_class("header-title")
        title.set_halign(Gtk.Align.CENTER)
        header.pack_start(title, False, False, 0)

        rule = Gtk.Box()
        rule.set_size_request(378, 3)
        rule.get_style_context().add_class("header-rule")
        rule.set_halign(Gtk.Align.CENTER)
        rule.set_margin_top(22)
        header.pack_start(rule, False, False, 0)
        self.box.pack_start(header, False, False, 0)

        dnd_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        dnd_row.set_margin_top(45)
        dnd_row.set_margin_start(34)
        dnd_row.set_margin_end(40)
        dnd_label = Gtk.Label(label="Do Not Disturb")
        dnd_label.get_style_context().add_class("dnd-label")
        dnd_label.set_halign(Gtk.Align.START)
        dnd_label.set_valign(Gtk.Align.CENTER)
        dnd_row.pack_start(dnd_label, True, True, 0)

        self.dnd_btn = Gtk.Button()
        self.dnd_btn.set_size_request(76, 38)
        self.dnd_btn.get_style_context().add_class("dnd-toggle")
        self.dnd_btn.set_can_focus(False)
        self.dnd_btn.set_relief(Gtk.ReliefStyle.NONE)
        self.dnd_knob = Gtk.Box()
        self.dnd_knob.set_size_request(26, 26)
        self.dnd_knob.get_style_context().add_class("dnd-knob")
        self.dnd_knob.set_halign(Gtk.Align.START)
        self.dnd_knob.set_valign(Gtk.Align.CENTER)
        self.dnd_btn.add(self.dnd_knob)
        self.dnd_btn.connect("clicked", self.toggle_dnd)
        dnd_row.pack_end(self.dnd_btn, False, False, 0)
        self.box.pack_start(dnd_row, False, False, 0)

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_overlay_scrolling(False)
        self.scroll.set_shadow_type(Gtk.ShadowType.NONE)
        self.notif_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.notif_box.set_margin_top(12)
        self.scroll.add(self.notif_box)
        self.box.pack_start(self.scroll, True, True, 0)

    def toggle_dnd(self, widget=None):
        self.dnd = not self.dnd
        ctx = self.dnd_btn.get_style_context()
        if self.dnd:
            ctx.add_class("dnd-on")
            self.dnd_knob.set_halign(Gtk.Align.END)
        else:
            ctx.remove_class("dnd-on")
            self.dnd_knob.set_halign(Gtk.Align.START)
        self.update_notification_list()

    def load_notifications(self):
        self.notifications = []
        self.update_notification_list()

    def show_empty_state(self):
        for child in self.notif_box.get_children():
            self.notif_box.remove(child)
        wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        wrapper.set_valign(Gtk.Align.CENTER)
        wrapper.set_halign(Gtk.Align.CENTER)
        bell = Gtk.Label(label="󰂚")
        bell.get_style_context().add_class("empty-bell")
        bell.set_halign(Gtk.Align.CENTER)
        wrapper.pack_start(bell, False, False, 0)
        empty = Gtk.Label(label="No Notifications")
        empty.get_style_context().add_class("empty-label")
        empty.set_halign(Gtk.Align.CENTER)
        empty.set_margin_top(45)
        wrapper.pack_start(empty, False, False, 0)
        self.notif_box.pack_start(wrapper, True, True, 0)
        self.notif_box.show_all()

    def update_notification_list(self):
        if self.dnd or not self.notifications:
            self.show_empty_state()
            return
        for child in self.notif_box.get_children():
            self.notif_box.remove(child)
        for notif in self.notifications:
            title = str(notif.get("title", ""))
            body = str(notif.get("body", ""))
            icon = str(notif.get("icon", "󰂚")) or "󰂚"
            has_body = 1 if body else 0
            card = AngularCard(title, body=body, icon=icon, height=88 if has_body else 62)
            self.notif_box.pack_start(card, False, False, 0)
        self.notif_box.show_all()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide_sidebar()
        return False

    def setup_socket(self):
        try:
            os.unlink(SOCKET_PATH)
        except:
            pass
        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(SOCKET_PATH)
        self.server_socket.listen(1)
        self.server_socket.setblocking(False)
        GLib.io_add_watch(self.server_socket.fileno(), GLib.IO_IN, self.on_socket_data)

    def on_socket_data(self, fd, condition):
        try:
            conn, _ = self.server_socket.accept()
            data = conn.recv(1024)
            conn.close()
            if data:
                cmd = data.decode().strip()
                with open("/tmp/sidebar.log", "a") as f:
                    f.write(f"DEBUG socket cmd={cmd}\n")
                if cmd == "toggle":
                    GLib.idle_add(self.toggle_sidebar)
        except Exception as e:
            with open("/tmp/sidebar.log", "a") as f:
                f.write(f"DEBUG socket exception: {e}\n")
        return True

    def toggle_sidebar(self, widget=None):
        if self.visible:
            self.hide_sidebar()
        else:
            self.show_sidebar()

    def show_sidebar(self):
        self.visible = True
        self.show_all()
        self.slide_to(0)

    def hide_sidebar(self, widget=None):
        self.visible = False
        self.slide_to(-self.sidebar_width)

    def slide_to(self, target):
        self._cancel_slide()
        current = GtkLayerShell.get_margin(self, GtkLayerShell.Edge.RIGHT)
        steps = 18
        step = (target - current) / float(steps)
        count = [0]

        def tick():
            count[0] += 1
            if count[0] >= steps:
                GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, int(target))
                self.anim_id = None
                return GLib.SOURCE_REMOVE
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, int(current + step * count[0]))
            return GLib.SOURCE_CONTINUE

        self.anim_id = GLib.timeout_add(16, tick)

    def _cancel_slide(self):
        if self.anim_id is not None:
            GLib.source_remove(self.anim_id)
            self.anim_id = None

if __name__ == "__main__":
    sidebar = NotificationSidebar()
    sidebar.show()
    Gtk.main()