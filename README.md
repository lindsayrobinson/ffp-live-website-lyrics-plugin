# Live Website Lyrics — FPP plugin 1.0

Reads FPP's playback status API and sends it to the existing website lyrics receiver.
The website retains the lyric files, lead-track filtering, capitalisation and follow-line behaviour.
Aircraft blackouts do not pause audio or lyric timing.

## Installation on this player

For FPP 10.2–10.x, open Plugins and enter this plugin information URL:

https://raw.githubusercontent.com/lindsayrobinson/ffp-live-website-lyrics-plugin/main/pluginInfo.json

Install the plugin, then open **Content Setup → Live Website Lyrics**.
For manual installation, extract into `media/plugins/fpp-plugin-loe-lyrics` and
run `bash scripts/fpp_install.sh` as root. No FPP restart is needed.

The installer imports the existing `config/loe-lyrics.json` including its private
website key and all sequence mappings. On a fresh player, sending stays disabled
until a key is entered and the checkbox enabled. Updates preserve configuration.

The repository is named `ffp-live-website-lyrics-plugin` (as requested); the internal
plugin ID remains `fpp-plugin-loe-lyrics` for compatibility with existing installations.
Private runtime settings and keys are excluded from Git and downloadable packages.

## What it installs

* Plugin files, settings and private configuration under this plugin directory.
* `/etc/systemd/system/loe-lyrics.service`, running Python as the unprivileged
  `fpp` user. The same unit name replaces the old sender and prevents duplicates.
* One runtime log: `plugin-fpp-plugin-loe-lyrics.log` in FPP's logs directory.

The private directory is dot-prefixed because FPP 10.3's plugin file-serving
wrapper rejects dot paths; Apache also denies dot directories. Do not move keys
into publicly served JSON files. The distributable contains no actual key.

Settings changes are detected within a few seconds. Turning sending off terminates
the sender child; the supervisor stays available for re-enabling it. The website
expires its last playback update normally. The plugin does not edit FPP core,
playlists, sequences, aircraft code or network forwarding.

## Uninstall and rollback

Use FPP's uninstall control if listed, or run `scripts/fpp_uninstall.sh` as root
before removing the plugin folder. This stops and removes only this plugin's
service, leaving the old script and old configuration untouched. It is safe to
run uninstall twice. Uninstall does not automatically restart the legacy sender.

If a legacy unit existed, its original text is retained in `.private/legacy-service.backup`.
For rollback, stop the service, restore that file to `/etc/systemd/system/loe-lyrics.service`
with mode 644, run `systemctl daemon-reload`, then `systemctl enable --now loe-lyrics.service`.
If no old unit existed (for example after an OS image upgrade), restore the legacy
unit from the website project's `integrations/lyrics/loe-lyrics.service` instead.
Both approaches reuse the untouched original sender script and configuration.

## Data sent

HTTPS requests every two seconds (configurable 1–5) contain song filename,
playback state/position, observation time and a random playback session identifier.
They authenticate with the separate website lyrics key. No audio, lyric text,
lighting control or inbound internet access is involved.

FPP lifecycle hooks stop this sender on an orderly FPP stop and start it again
with FPP. The start hook can restore the service unit after an OS-image upgrade,
using the retained plugin configuration. FPP core is never patched.
