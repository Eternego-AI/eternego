---
title: Desktop access on each OS
---

# Desktop access on each OS

For your persona to *use* your computer — take screenshots, move the mouse,
type into focused windows — Eternego talks to two surfaces of the operating
system:

- **Screenshot** — `OS.screenshot` captures the screen as a PNG.
- **Input** — `desktop.mouse_*` and `desktop.keyboard_*` synthesize mouse and
  keyboard events.

Each OS exposes these capabilities differently, and the permissions story
differs. Here's what works out of the box and what you may need to set up.

## macOS

| Capability | API | Permission |
| --- | --- | --- |
| Screenshot | `screencapture` (Apple's CLI, calls CoreGraphics) | TCC: Screen Recording |
| Input | `pynput` → Quartz event tap | TCC: Accessibility |

**On first use macOS prompts you** to grant Screen Recording and Accessibility
to the binary that's running Eternego (your terminal, the `.app` from the
DMG, or your IDE). Approve once in System Settings → Privacy & Security and
the persona has the access for as long as the binary's signed identity is
stable.

**Known issue with the unsigned `.dmg` build**: TCC may grant Screen
Recording in System Settings but not honor it when the unsigned bundle calls
the API — your persona gets wallpaper-only screenshots. Until a Developer-ID
signed bundle ships, install from source if you need reliable Screen
Recording on macOS.

## Windows

| Capability | API | Permission |
| --- | --- | --- |
| Screenshot | `Pillow.ImageGrab` (Win32 GDI BitBlt) | none — works with any user |
| Input | `pynput` → SendInput | none — works with any user |

Windows has no equivalent to TCC; both capabilities are available to any
process running as your user. The first launch SmartScreen warning is a
download trust prompt, not a permission gate — once you click "Run anyway"
it remembers, and there's nothing else to grant.

## Linux

| Capability | API | Permission |
| --- | --- | --- |
| Screenshot | `xdg-desktop-portal` over DBus | one-time portal grant on Wayland (KDE/GNOME remember "always allow this app") |
| Input | `evdev.UInput` → kernel `/dev/uinput` | write access to `/dev/uinput` |

The same code works on **both X11 and Wayland sessions**. The portal sits
above the display server and abstracts the differences for screenshots; the
kernel's `/dev/uinput` device sits below the display server and abstracts
them for input. No session-type detection is needed in your config.

### `/dev/uinput` access

By default `/dev/uinput` is owned `root:root` with mode `0600`, so a
non-root user can't write to it. Grant access either by adding yourself to
the `input` group or by shipping a udev rule.

**Group membership** (one-time):

```bash
sudo usermod -aG input $USER
# log out and back in for the group change to take effect
```

**udev rule** (alternative, persists across users):

```bash
echo 'KERNEL=="uinput", MODE="0660", GROUP="input"' \
  | sudo tee /etc/udev/rules.d/99-eternego-uinput.rules
sudo udevadm control --reload && sudo udevadm trigger
```

Either is sufficient. You can verify access with:

```bash
test -w /dev/uinput && echo writable || echo not writable
```

If the persona's input verbs return permission errors at runtime, this is
almost always why.

### Wayland on minimal compositors

Plasma, GNOME, COSMIC, Hyprland, sway and most other modern desktops ship
an `xdg-desktop-portal` backend by default. Bare-bones window managers
(some i3 setups, dwm, etc.) may not — install one of:

- `xdg-desktop-portal-gtk` — works under any X11 session and most Wayland
  compositors as a fallback.
- `xdg-desktop-portal-wlr` — wlroots-native (sway, hyprland).
- `xdg-desktop-portal-kde`, `xdg-desktop-portal-gnome` — desktop-specific.

If `OS.screenshot` raises a DBus error like *"org.freedesktop.portal.Desktop
not provided by any .service files"*, install one of the above and restart
the session.

## Docker

The published Eternego image ships an in-container desktop stack baked in:

- `Xvfb` virtual display
- `fluxbox` window manager
- `x11vnc` + `noVNC` so you can peek at the persona's screen at
  `http://localhost:6080/vnc.html`
- `xdg-desktop-portal` + `xdg-desktop-portal-gtk` + `dbus` for screenshot
- `dbus-run-session` wraps the daemon so the portal can be reached over the
  session bus

That covers screenshot end-to-end inside the container. **Input from the
container is more involved**: `/dev/uinput` lives on the host kernel, and
the container's user can only write to it if you pass it through:

```bash
docker run -d --name eternego --network=host \
  --device=/dev/uinput \
  -v ~/.eternego:/data \
  ghcr.io/eternego-ai/eternego:latest
```

`--device=/dev/uinput` makes the host's uinput device visible inside the
container. Without it, mouse / keyboard verbs raise a permission error and
only screenshot works.

## Headless hosts

`desktop.available()` returns `False` if no display is reachable. On Linux
that means neither `DISPLAY` nor `WAYLAND_DISPLAY` is set, or `/dev/uinput`
isn't writable. On macOS / Windows it means pynput's controller can't be
instantiated.

The persona checks `available()` to know whether `screen` and
`take_screenshot` will work; when it returns `False`, she politely tells
the person she can't see or act on the screen rather than raising
mid-cycle.
