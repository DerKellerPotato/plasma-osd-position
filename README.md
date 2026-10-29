# plasma-osd-position

> **Heads up:** This project was built with AI assistance (Claude) and is provided as-is.
> It scratches a very specific personal itch and will most likely **not** receive
> ongoing maintenance. Feel free to fork it, open PRs, or use it as a starting
> point for your own tool — just don't expect active support.

A small Qt application to graphically set the position of KDE Plasma's volume
and brightness OSD (on-screen display).

Plasma doesn't offer a built-in setting for this — the OSD is drawn by KWin
itself. The only supported way to move it is a window rule that matches the
*On-Screen Display* window type and forces both **position** and **initial
placement**. That's exactly the rule this program creates for you.

## Features

- Distance from the bottom screen edge plus horizontal alignment (center/left/right)
- Multi-monitor support: target screen selectable, X/Y computed in global coordinates
- Preview of all screens in their actual arrangement
- Fine-tuning via X/Y offset and the assumed OSD size
- Apply the rule, test it (`org.kde.osdService`), and remove it again
- KWin reloads the configuration immediately (`qdbus org.kde.KWin /KWin reconfigure`)

## What exactly gets written

A group with its own UUID is created in `~/.config/kwinrulesrc`:

```ini
[<uuid>]
Description=OSD position (plasma-osd-position)
types=65536        # NET::OnScreenDisplayMask == 1 << 16
position=X,Y       # KConfig serializes QPoint as "x,y"
positionrule=2     # KWin Rules::Force
placement=0        # KWin Placement::NoPlacement
placementrule=2    # KWin Rules::Force
```

`count` and `rules` in the `[General]` group are updated as well. Without the
forced `placement=0`, KWin would override the coordinates with its own
placement logic — that's why the program sets both values together.

Writing happens via `kwriteconfig6` (falling back to `kwriteconfig5`) so that
KConfig semantics and the file format are preserved.

## Installation

Every `v*` tag publishes these files on the GitHub release page:

| Distribution | File | Install |
|---|---|---|
| Debian / Ubuntu / Linux Mint / KDE neon | `plasma-osd-position_<ver>_all.deb` | `sudo apt install ./plasma-osd-position_*_all.deb` |
| Fedora / openSUSE | `plasma-osd-position-<ver>-1.noarch.rpm` | `sudo dnf install ./plasma-osd-position-*.rpm` / `sudo zypper install ./plasma-osd-position-*.rpm` |
| Arch / Manjaro / EndeavourOS / CachyOS | `plasma-osd-position-<ver>-1-any.pkg.tar.zst` | `sudo pacman -U ./plasma-osd-position-*.pkg.tar.zst` |
| Any (Flatpak) | `plasma-osd-position-<ver>-x86_64.flatpak` | `flatpak install --user ./plasma-osd-position-*.flatpak` |
| Any (AppImage, glibc ≥ 2.28) | `plasma-osd-position-<ver>-x86_64.AppImage` | `chmod +x` and run |

Directly from source, without a package:

```bash
python3 src/plasma_osd_position/__main__.py
```

Runtime dependencies: `python3` and PyQt6. `kwriteconfig6` is used when
available; otherwise the program edits `kwinrulesrc` itself. KWin is reloaded
via D-Bus (QtDBus, falling back to `qdbus6`).

The Flatpak needs access to `~/.config` (`--filesystem=xdg-config`), because
KWin reads the rule from the host's `kwinrulesrc`, and talks to
`org.kde.KWin` and `org.kde.plasmashell` on the session bus.

## Building packages yourself

```bash
./packaging/build-deb.sh       # needs dpkg-deb
./packaging/build-rpm.sh       # needs rpmbuild
./packaging/build-arch.sh      # needs makepkg (not as root)
./packaging/build-appimage.sh  # downloads python-appimage, PyQt6 and appimagetool
flatpak-builder --user --install-deps-from=flathub build \
  packaging/flatpak/io.github.derkellerpotato.PlasmaOsdPosition.yml
```

The GitHub Actions workflow `.github/workflows/build.yml` builds all formats
on every push and PR, test-installs the native packages on Debian, Ubuntu,
Fedora, openSUSE Tumbleweed and Arch, and attaches everything (plus
`SHA256SUMS`) to the release on `v*` tags.

## Rolling out via Ansible

The rule is pure user configuration. For a consistent position across
multiple workstations, it's enough to set the rule once locally and ship the
resulting section of `~/.config/kwinrulesrc` to the target machines via
`community.general.ini_file` (or as a template) — the UUID can stay identical.
Afterwards, per user session:

```bash
qdbus6 org.kde.KWin /KWin reconfigure
```

## Known limitations

- **One rule = one absolute position.** KWin has no concept of a
  screen-relative position, so once the rule is applied the OSD always
  appears on the chosen monitor and no longer follows the active one. A
  consistent bottom margin across multiple screens can't be expressed this way.
- The rule sets the window's **top-left corner**. To anchor to the bottom
  edge, the OSD height is therefore needed; the default values are an
  estimate and adjustable in the dialog.
- With fractional scaling, the logical Qt coordinates can differ from the
  coordinates KWin uses for the rule — adjust X/Y manually in that case.
- Tested against Plasma 6. Older Plasma 5 versions sometimes still store
  `placement` as a string.

## License

MIT
