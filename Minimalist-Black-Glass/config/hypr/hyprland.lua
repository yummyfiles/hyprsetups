
-- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
-- BLACK & WHITE HYPRLAND CONFIG
-- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --

------------------
---- MONITORS ----
------------------
hl.monitor({
    output   = "",
    mode     = "preferred",
    position = "auto",
    scale    = "auto",
})

---------------------
---- MY PROGRAMS ----
---------------------
local terminal    = "kitty"
local fileManager = "dolphin"
local menu        = "rofi -show drun -theme ~/.config/rofi/themes/bw.rasi"

-------------------
---- AUTOSTART ----
-------------------
hl.on("hyprland.start", function () 
    hl.exec_cmd("hyprpaper")
    hl.exec_cmd("wl-clip-persist --clipboard both") -- keep clipboard data (incl. images) alive for pasting
    hl.exec_cmd("sh ~/.config/waybar/scripts/waybar-watch.sh")
    hl.exec_cmd("python3 ~/.config/waybar/scripts/notify-daemon.py")
    hl.exec_cmd("eww daemon") -- eww widget engine (notification sidebar, HUDs, desktop widgets)
    -- desktop_watcher.sh is started by the systemd user unit desktop-widgets.service
    hl.exec_cmd("sh ~/.config/cava/scripts/setup-spotify-sink.sh") -- Spotify-only sink for cava
    hl.exec_cmd("sh ~/.config/waybar/scripts/cava.sh") -- audio visualizer rendered behind all windows
    hl.exec_cmd("bash ~/.config/waybar/scripts/cava-fade.py") -- idle fade for cava bars
    hl.exec_cmd("hypridle")
    hl.exec_cmd("nm-applet --indicator") -- NetworkManager tray icon just in case, but we have rofi
end)

-------------------------------
---- ENVIRONMENT VARIABLES ----
-------------------------------
hl.env("XCURSOR_SIZE", "24")
hl.env("HYPRCURSOR_SIZE", "24")
hl.env("QT_QPA_PLATFORMTHEME", "kde")
hl.env("QT_STYLE_OVERRIDE", "kvantum")
hl.env("KVANTUM_THEME", "MonoFlat")

-----------------------
---- LOOK AND FEEL ----
-----------------------
hl.config({
    general = {
        gaps_in  = 5,
        gaps_out = 10,
        border_size = 2,
        col = {
            active_border   = "rgba(ffffffff)",
            inactive_border = "rgba(000000ff)",
        },
        layout = "dwindle",
    },

    decoration = {
        rounding       = 0,
        active_opacity   = 1.0,
        inactive_opacity = 1.0,
        shadow = {
            enabled      = false,
        },
        blur = {
            enabled   = false,
        },
    },

    animations = {
        enabled = true,
        bezier = {
            { name = "myBezier", points = {{0.05, 0.9, 0.1, 1.05}} }
        },
        animation = {
            { leaf = "windows", enabled = true, speed = 5, bezier = "myBezier" },
            { leaf = "windowsOut", enabled = true, speed = 5, bezier = "default", style = "popin 80%" },
            { leaf = "border", enabled = true, speed = 5, bezier = "default" },
            { leaf = "fade", enabled = true, speed = 5, bezier = "default" },
            { leaf = "workspaces", enabled = true, speed = 5, bezier = "default" },
        }
    },
})

----------------
----  MISC  ----
----------------
hl.config({
    misc = {
        force_default_wallpaper = 0,
        disable_hyprland_logo   = true,
        background_color = "0x000000",
        allow_session_lock_restore = true,
    },
})

---------------
---- INPUT ----
---------------
hl.config({
    input = {
        kb_layout  = "us",
        follow_mouse = 1,
        sensitivity = 0,
        touchpad = {
            natural_scroll = false,
        },
    },
})

---------------------
---- KEYBINDINGS ----
---------------------
local mainMod = "SUPER"

hl.bind(mainMod .. " + Q", hl.dsp.exec_cmd(terminal))
hl.bind(mainMod .. " + C", hl.dsp.window.close())
hl.bind(mainMod .. " + M", hl.dsp.exec_cmd("hyprlock"))
hl.bind(mainMod .. " + E", hl.dsp.exec_cmd(fileManager))
hl.bind(mainMod .. " + V", hl.dsp.window.float({ action = "toggle" }))
hl.bind(mainMod .. " + R", hl.dsp.exec_cmd(menu))

-- Control Panels
hl.bind(mainMod .. " + F1", hl.dsp.exec_cmd("sh ~/.config/waybar/scripts/volume.sh"))
hl.bind(mainMod .. " + F2", hl.dsp.exec_cmd("sh ~/.config/waybar/scripts/wifi.sh"))
hl.bind(mainMod .. " + F3", hl.dsp.exec_cmd("sh ~/.config/waybar/scripts/bluetooth.sh"))

-- Focus
hl.bind(mainMod .. " + left",  hl.dsp.focus({ direction = "left" }))
hl.bind(mainMod .. " + right", hl.dsp.focus({ direction = "right" }))
hl.bind(mainMod .. " + up",    hl.dsp.focus({ direction = "up" }))
hl.bind(mainMod .. " + down",  hl.dsp.focus({ direction = "down" }))

-- Multimedia
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"), { locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"),      { locked = true, repeating = true })
hl.bind("XF86AudioMute",        hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"),     { locked = true, repeating = true })
hl.bind("XF86AudioNext",  hl.dsp.exec_cmd("playerctl next"),       { locked = true })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPlay",  hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPrev",  hl.dsp.exec_cmd("playerctl previous"),   { locked = true })

-- Mouse drag/resize
hl.bind(mainMod .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true })
hl.bind(mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

-- Screenshots (grimblast: copy + save to ~/Pictures)
hl.bind("Print", hl.dsp.exec_cmd("grimblast --notify copysave output"))
hl.bind("SHIFT + Print", hl.dsp.exec_cmd("grimblast --notify copysave area"))
hl.bind(mainMod .. " + Print", hl.dsp.exec_cmd("grimblast --notify save area"))

-- Reload waybar (the watcher retires any previous watcher and restarts the bar)
hl.bind(mainMod .. " + SHIFT + R", hl.dsp.exec_cmd("sh ~/.config/waybar/scripts/waybar-watch.sh"))

-- Exit Hyprland
hl.bind(mainMod .. " + SHIFT + Q", hl.dsp.exit())

-------------------------------
---- WINDOWS AND WORKSPACES ----
--------------------------------
hl.window_rule({
    name  = "suppress-maximize-events",
    match = { class = ".*" },
    suppress_event = "maximize",
})

hl.window_rule({
    name  = "cava-bar",
    match = { class = "^(cava-bar)$" },
    float = true,
    no_initial_focus = true,
    no_focus = true,
    stay_focused = false,
    border_size = 0,
    rounding = 0,
    move = { "0", "(monitor_h * 1) - 120" },
    size = { "monitor_w", "120" },
})

-- Cava-bar visibility and z-order are handled dynamically by cava-fade.py:
-- it moves the kitty window to a hidden special workspace while idle and back
-- to the active workspace (pinned to the bottom) once audio resumes.
