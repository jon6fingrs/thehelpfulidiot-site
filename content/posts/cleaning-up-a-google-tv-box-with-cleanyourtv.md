+++
title = "Turning a Google TV Box into an Ad-Free Streamer and Family Photo Frame"
date = 2026-11-04
path = "cleaning-up-a-google-tv-box-with-cleanyourtv"
description = "How I used the open-source cleanyourtv project and Claude Code to strip the ads and telemetry off a Xiaomi TV Box S, then added Jellyfin, a photo screensaver from Immich, remapped remote buttons, Home Assistant control and an ESP32 Bluetooth keyboard."

[taxonomies]
category = ["Self Hosting"]
tag = ["android tv", "claude", "home assistant", "immich", "jellyfin", "esp32"]
+++

I was listening to [LINUX Unplugged episode 690](https://linuxunplugged.com/690) ("The S in PHP is for Security") when they mentioned [cleanyourtv](https://github.com/Gathin23/cleanyourtv), an open-source project that promises to "debloat any Android or Google TV over Wi-Fi and get an Apple TV-style home." They linked the box they used, a [Xiaomi TV Box S (3rd gen)](https://www.amazon.com/Xiaomi-TV-Box-3rd-Gen/dp/B0F3JWFL56), and I bought one.

Out of the box it's a capable little streamer buried under a Google TV home screen full of sponsored rows, plus Xiaomi's own content tabs, promo apps and analytics. About two hours later it was this:

![Before: a Google TV home screen with a sponsored banner, "Top picks for you" and Xiaomi TV+ rows. After: a clock and a six-app dock with Jellyfin, Netflix, Disney+, Prime Video, Apple TV and YouTube](/img/2026/11/gtv-home-before-after.svg)
*Roughly what changed. No rows, no recommendations, no ads.*

It also turned out to be a replacement for my old Kodi box's best feature: a screensaver that shows only photos of my kids, pulled from my self-hosted Immich.

## What I Wanted

- A home screen with **only my apps**. No "recommendations," no sponsored anything.
- **Keep my streaming apps**: Netflix, Disney+, Prime Video, Apple TV, YouTube, Hulu, Peacock, Tubi, Max, YouTube TV and YouTube Music.
- **Add Jellyfin** for my home media server.
- **Remove the voice assistant** and as much Xiaomi software as was safe to remove.
- **Don't touch my DNS.** My network already handles that.
- **Replace the Kodi screensaver**: photos of my kids from Immich, with the date and location on each.
- **Keep Home Assistant working** with the TV.

## What cleanyourtv Is

cleanyourtv is a repo meant to be driven by an AI coding agent. You point the agent at `PROMPT.md`, tell it your TV model, and it follows a written, safety-first procedure. Inside:

| Folder | What's in it |
|---|---|
| `PROMPT.md` | The step-by-step procedure and its safety rules |
| `examples/` | Tested debloat lists for specific models. **My exact box already had a folder**, with notes and a theme |
| `tools/` | `disable.sh`, `restore.sh`, `theme.sh`, a screenshot tool, and a check that ADB is closed afterwards |
| `launcher/` | A small Apple TV-style home screen you build from source. No internet permission, no analytics |

What sold me was the safety philosophy:

- **Disable, never uninstall.** Everything uses `pm disable-user`, so `restore.sh` can undo every step. No root, nothing flashed.
- **Back up first**: package lists, settings and system properties, before the first change.
- **Never touch the core Android packages.** The scripts refuse a list that includes them.
- **A "Home guard."** The stock launcher is only disabled after the new one is confirmed as Home, so you can't end up at a black screen with no way back.

## The Setup

I ran [Claude Code](https://claude.ai/code) inside a Linux container on the same VLAN as the TV. It talked to the box over ADB (Android Debug Bridge) on the network, which you turn on under Developer options on the TV.

Before it did anything, I gave it some ground rules:

- **Read-only first.** No disabling, no installs, no Wi-Fi or DNS changes, no launcher swap and no reboot without my OK.
- **Back up everything** before the first change.
- **Ask me what to keep.**
- **Screenshot every stage** to prove it worked.

Here's how the two hours went:

![Eight steps: look don't touch; fix the Wi-Fi trap; decide what stays; disable in 3 batches; build the launcher from source; sideload Jellyfin; swap the launcher; then the screensaver, remote and Home Assistant](/img/2026/11/gtv-steps.svg)

## Step 1: Look, Don't Touch

The first pass changed nothing. It found my firmware (V816.0.25.2.11) was newer than the one the repo's example was tested on, and flagged that. It counted 153 packages, 9 installed by me and none disabled. It recorded the display settings (4K panel, 1080p UI) so they could be put back exactly.

Then it saved a full backup folder: every package list, all the system, secure and global settings, display info, which apps claim the Home button, and who owns the Wi-Fi network. That last one turned out to matter a lot.

Its first backup attempt had a bug in a chained shell command that tried to `chmod` the root of the TV. The system refused and nothing was harmed, and the agent told me about it instead of quietly redoing it. That set the tone for the rest of the morning.

## Step 2: The Wi-Fi Trap

This is the gotcha I'd never have caught myself.

On Google TV, the setup wizard (`com.google.android.tungsten.setupwraith`) can **own** your saved Wi-Fi networks. When you disable an app, Android deletes the networks that app owns. And on this box, the setup wizard has to be disabled before the launcher can be swapped.

So the obvious next step would have knocked the TV off Wi-Fi and cut the agent's connection halfway through the job.

![The trap: Wi-Fi owned by setupwraith, disable it, Android deletes its networks and ADB dies. The fix: forget and re-join the Wi-Fi on the TV, confirm the owner is now system, then disable safely](/img/2026/11/gtv-wifi-trap.svg)

The agent caught it by checking ownership before touching anything:

```bash
adb shell dumpsys wifi | grep cname=
```

All four saved networks belonged to `setupwraith`. The fix was low-tech: I forgot the network in the TV's settings and joined it again, and now it belonged to `system`. The repo's disable script also refuses to disable `setupwraith` while it owns a network, so there's a second guard.

**If you do this yourself, check who owns your Wi-Fi first.**

## Step 3: Deciding What Stays

The agent asked before acting, and some of the questions made me rethink my answers.

- **Streaming apps:** I kept all of them. Disney+ was on the example's disable list, so it came off mine.
- **"Get rid of all the Xiaomi stuff":** it pushed back on taking that literally. Some Xiaomi-named packages are the box's plumbing.
- **Voice:** I asked to remove the Assistant. It warned me the mic button would go dead. Fine by me.

| Stays (on purpose) | Why |
|---|---|
| `mitv.service` | The core TV service |
| `com.mi.bluetooth` | The remote and pairing |
| `com.droidlogic*` | The Amlogic chip layer |
| `partnercustomizer` | Setup customizer; the example says leave it |
| `mitv.overseaservice` | Purpose unknown, so left alone |
| The firmware updater | I still want security updates |
| Play Store, Play Services, Chromecast | Apps and casting still need them |

## Step 4: Disabling in Small Batches

Three batches, one command per package, then a check against the disabled list and a screenshot:

```bash
adb shell pm disable-user --user 0 com.miui.tv.analytics
```

- **Batch 1 (11 packages): telemetry, feedback and promos.** Xiaomi analytics and statistics, Google feedback, Xiaomi's PatchWall content rows and the "Xiaomi TV+" promo, and an Amlogic auto-installer that pushes apps onto the box.
- **Batch 2: screen sharing and voice.** Mi share/Miracast, the Assistant (`katniss`) and `tv.remote.service`. Remember that last one. It comes back.
- **Batch 3: Xiaomi's own apps.** Music, gallery, video player and media explorer, plus the print spooler, TalkBack and Play Games.

One screenshot came back byte-for-byte identical to the one before it. That's a known stale-frame quirk (the repo documents it), so the agent force-stopped the old launcher and took it again.

## Step 5: Building the Launcher on a Box With No Build Tools

The repo forbids handing over APKs built somewhere else; you build the launcher yourself. My container had no Java, no Android SDK, no Docker, no `sudo`, and 2 GB of RAM.

With my OK, the agent downloaded Java 17 and the Android command-line tools into my home folder, **checked every download against its published checksum**, and ran Gradle with a small memory limit to fit in 2 GB. The launcher came out at 588,061 bytes, just under the repo's 576 KB size limit.

## Step 6: Jellyfin

The agent pulled Jellyfin for Android TV 0.19.10 from Jellyfin's official GitHub releases, checked the SHA-256 against GitHub's published digest, and confirmed the APK is signed by the Jellyfin team before installing it.

The first install failed because ADB dropped (more on that below). After I woke the TV, the agent confirmed nothing had changed, matched the checksum on both ends again, and installed it.

## Step 7: Swapping the Launcher

This is the step that can leave you staring at a black screen, so the order matters:

1. Disable `setupwraith` (safe now), then confirm Wi-Fi and ADB are still up.
2. Install the new launcher with my theme: 6 columns, my dock order, and Google's ambient screensaver turned off.
3. Confirm the new launcher **is** Home.
4. Only then disable the stock Google TV launcher.
5. Reboot once.

It came back in about 70 seconds, landed on the new home screen, and had the same disabled list as before the reboot.

## Step 8: A Screensaver That's Just a Web Page

This was the part I actually cared about.

cleanyourtv's showcase lists a community "Homelab companion" app with an Immich screensaver, so we tried it first. Before building it, the agent read the code, because it asks for a powerful permission. Claude's safety check then blocked the build of this third-party code. The agent didn't try to work around that. It reviewed the build files read-only, told me what it found (standard, pinned plugins, no custom download or exec steps), and asked me. I said yes.

It worked, but it could only filter by "last N days" or hide albums. It couldn't filter by **person**, and my old Kodi setup showed only my kids.

I already run [immich-kiosk](https://github.com/damongolding/immich-kiosk), a web app that shows an Immich slideshow in a browser. It filters by person right in the URL (`?person=...&person=...`) and overlays the date, location and weather. So: can a screensaver just be a web page?

Not directly. Android TV has no "screensaver = URL" setting; a screensaver has to be an app that provides a "dream" service. Rather than install some random "web screensaver" APK, the agent wrote a tiny one: about 1,000 lines of Java, a 27 KB APK.

![Flowchart: after 3 minutes idle, load the immich-kiosk page. If it loads within 25 seconds without an HTTP error, show my kids' photos with date, location and weather. If not, show Wikimedia Commons landscape and city photos, and check the kiosk page every 10 minutes to switch back](/img/2026/11/gtv-screensaver-flow.svg)

- It shows the Kiosk page full-screen in a WebView.
- If the page doesn't load in time (25 seconds by default) or returns an error, it switches to a **fallback**.
- On the fallback, it checks the Kiosk page every 10 minutes and switches back once it's up.
- It tears the WebView down when it exits, to be kind to the box's limited RAM.
- The settings live in a small file on the TV, so my kids' Immich IDs are on the TV and not in any code.

For the fallback I asked for something like Apple TV's aerial views. The agent picked Wikimedia Commons' "Featured pictures" of landscapes, cityscapes and mountains: free, properly licensed, no API key. It only uses landscape-shaped photos and shows the title, photographer and licence on each.

Testing: the Kiosk page rendered full-screen with date, location and Baltimore weather. With the Kiosk server deliberately made unreachable, it fell back almost instantly to 58 Commons photos, crossfading every 20 seconds. The Homelab companion got disabled (not uninstalled).

### Never Sleep

I asked whether it mattered if the TV went to sleep. Instead of yes or no, I got the trade-offs: power and heat, burn-in on an OLED from the clock and weather overlay (my TV is LCD), the TV switching HDMI inputs when the box sleeps, and ADB reliability. I chose screensaver after 3 minutes, sleep never:

```bash
adb shell settings put system screen_off_timeout 180000
adb shell settings put secure sleep_timeout -1
```

The agent then proved it worked the real way: it kept its hands off and watched the system log until the power manager started the screensaver on its own, about 3.5 minutes later.

### A Settings Screen for the Remote

I didn't want to need ADB for every tweak, so the agent added a "Screensaver" tile to the home screen with remote-friendly rows:

| Setting | Options |
|---|---|
| Kiosk page URL | on-screen keyboard |
| Fallback | built-in nature/city photos, or your own https page |
| Start screensaver after | 1, 2, 3, 5, 10, 15 or 30 minutes |
| TV sleep | Never, 30 minutes, or 1, 2, 4 or 8 hours |
| Give up on the page after | 10, 25, 45 or 90 seconds |
| Check the page again every | 1, 5, 10, 30 or 60 minutes |

Plus "Use as screensaver" and "Preview now," and a status block at the top. It refuses settings that can't work, like a sleep time shorter than the screensaver delay. This version needs two settings permissions granted over ADB so it can change the timeouts, and the agent told me how to take them back.

This firmware doesn't even show the normal Android screensaver settings screen, so this ended up filling a real gap.

## Step 9: Fixing the Remote Buttons

The remote has Netflix, Prime Video, YouTube, Apps and "Xiaomi TV+" buttons. Netflix and Prime still worked. YouTube and Apps didn't, because the stock launcher used to handle them, and Xiaomi TV+ pointed at the promo app we'd just disabled.

The launcher has a key helper (an accessibility service), and the repo's notes for this exact remote already had the button codes:

| Button | Now opens |
|---|---|
| Xiaomi TV+ | Jellyfin |
| YouTube | YouTube |
| Apps | The launcher's app library |

The agent insisted on a real test, because a simulated keypress doesn't go through the same path as a physical button when an accessibility helper is involved. I pressed the real buttons, and all three worked first try.

## Step 10: The Home Assistant Surprise

Home Assistant's [Android TV Remote](https://www.home-assistant.io/integrations/androidtv_remote/) integration wouldn't pair. Remember `tv.remote.service` from batch 2? That isn't just voice. It's the network remote that listens on ports 6466 and 6467, which is exactly what Home Assistant (and the Google TV phone app) uses.

While checking, the agent found and owned up to a second problem: the Assistant (`katniss`), which it had reported as disabled, was **enabled again**. I hadn't touched it. Most likely a Play Store update quietly turned it back on.

The fix: re-enable `tv.remote.service`, disable `katniss` again. The ports came back, the Assistant stayed off, and Home Assistant paired. It took a few tries, though.

## Bonus: An ESP32 as a Bluetooth Keyboard

The Android TV Remote integration works over the network, which means it depends on that one service staying enabled. I wanted a second way in that doesn't, and maybe a way to wake the box from standby. So in a separate session I set up an [M5Stack ATOM Echo](https://docs.m5stack.com/en/atom/atomecho) (a tiny ESP32) as a Bluetooth keyboard using [HomeOps/esphome-blekeyboard](https://github.com/HomeOps/esphome-blekeyboard).

![Three ways to control the box: the physical remote over Bluetooth; Home Assistant through the Android TV Remote service over the network, which also reports what's playing; and Home Assistant through the ATOM Echo acting as a Bluetooth keyboard, which is still being paired](/img/2026/11/gtv-control-paths.svg)
*The keyboard can only send keys. Knowing what's playing still comes from the network side.*

The ESPHome config is short, because the project ships packages for the keyboard and the media keys:

```yaml
esphome:
  name: google-tv-remote
  friendly_name: Google TV Remote

esp32:
  board: m5stack-atom
  framework:
    type: esp-idf

logger:
api:
ota:
  - platform: esphome

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  power_save_mode: none

external_components:
  - source:
      type: git
      url: https://github.com/HomeOps/esphome-blekeyboard
      ref: v0.8.0
      path: components
    components: [ble_keyboard]

packages:
  keyboard:
    url: https://github.com/HomeOps/esphome-blekeyboard
    ref: v0.8.0
    files: [packages/keyboard.yaml]
  media_keys:
    url: https://github.com/HomeOps/esphome-blekeyboard
    ref: v0.8.0
    files: [packages/media_keys.yaml]
```

That gives Home Assistant buttons for navigation and media keys, a `send_keys` action for typing text, and buttons to switch between or forget paired hosts.

Getting there was the usual ESPHome adventure:

- **ESPHome kept trying to reach the device at `1.1.1.1`.** My server had a `search` domain in `/etc/resolv.conf`, so `google-tv-remote` became `google-tv-remote.<my domain>`, which resolved to a public address. Removing the search line fixed the lookup.
- **Updates over the network timed out**, so I downloaded the factory firmware and flashed it over USB with [ESPHome Web](https://web.esphome.io/). The serial log showed the Bluetooth keyboard starting up and advertising.
- **It wouldn't join one of my Wi-Fi networks** (it saw it but timed out connecting). Pointing it at another one worked right away.

On the box, *Settings → Remotes & Accessories → Pair accessory* found **ESP32 BLE KB** and said "Connecting...". That's where it stands right now. Still to do: finish pairing, test navigation and typing from Home Assistant, and find out whether a Bluetooth keypress can wake the box from standby, which was the main reason for doing this.

## What Went Wrong

- **ADB dropped twice.** The TV still answered pings, but port 5555 closed, and the second time I had to accept the "Allow debugging?" prompt again. I don't know why. Each time the agent stopped instead of retrying in a loop, confirmed nothing was half-applied, and asked me to wake the TV.
- **The TV's own idle timer fired mid-test** and started the old screensaver. Harmless, and it accidentally proved that third-party screensavers work on this firmware.
- **The agent's capture of raw button presses recorded nothing.** It had passed two devices to a tool that accepts one. It said so, and since the repo's button codes were right, we didn't need the capture anyway.

## Lessons Learned

About the TV:

- **Check who owns your Wi-Fi** before disabling the setup wizard.
- **"Remove all the Xiaomi stuff" needs exceptions.** Some vendor packages are the Bluetooth, the chip layer and the core service.
- **"Remove voice" can break home automation.** Disable the Assistant (`katniss`), but leave `tv.remote.service` alone if Home Assistant talks to your TV.
- **Disabled apps don't always stay disabled.** A Play Store update can quietly turn a Google app back on. Check the list now and then.
- **A screensaver can be any web page** with a tiny app wrapping a WebView. immich-kiosk does everything my old nightly-download Kodi script did, and it asks Immich live.
- **Give a network screensaver a fallback.** Wikimedia Commons' featured pictures are a free, keyless stand-in for Apple TV aerials.
- **Test remapped buttons with the real remote.** Simulated presses take a different path.
- **Test from the device that matters.** My container looked up my Kiosk server's name and got a public address; the TV got the right local one.

About working with an AI agent:

- **Start it read-only and make it ask.** That opening produced an inventory and a list of questions, and it's how the Wi-Fi trap got caught before it bit.
- **Small batches with a check after each one** keep mistakes small and easy to trace.
- **A good agent tells you when it was wrong.** It owned up to the backup bug, the stale screenshot, the empty button capture and the "katniss is disabled" claim that wasn't true. Each one made me trust the rest more, not less.
- **Verify downloads and read third-party code.** Everything was checksum-verified, and when Claude's safety check blocked a build, it reviewed and asked rather than finding a way around it.
- **Give standing permission with conditions.** "Do steps 1 through 3 without asking, as long as everything goes as expected" kept things moving without handing over a blank check.
- **Model-specific community notes beat generic guides.** Someone had already worked out this exact box's quirks and remote codes.

## Undoing It

Nothing was uninstalled, rooted or flashed, so everything can be reversed:

```bash
# re-enable every disabled package
TV_HOST=<tv ip>:5555 tools/restore.sh backup/<backup-folder>/applied-debloat.txt

# remove the dock theme
tools/theme.sh --reset

# put the screensaver back to default
adb shell settings delete secure screensaver_components

# if Home is ever black, bring back the stock launcher
adb shell pm enable com.google.android.apps.tv.launcherx
```

## Before You Call It Done

One thing is still on my list, and it's the most important one: **turn ADB off**. Network ADB on port 5555 is unencrypted, and anyone on your network who gets past the "Allow debugging?" prompt has full control of the box. When I'm finished tinkering, I'll turn off wireless and USB debugging, revoke the saved authorizations, reboot, and confirm the port is closed with the repo's `tools/adb-closed.py`.

## Was It Worth It?

Yes. The box boots straight to my apps, the YouTube, Apps and formerly useless Xiaomi TV+ buttons all do something useful, and after 3 minutes it turns into a photo frame of my kids. If my server is down, it shows mountains and cities instead.

If you want to try it, the [Xiaomi TV Box S](https://www.amazon.com/Xiaomi-TV-Box-3rd-Gen/dp/B0F3JWFL56) already has a tested folder in cleanyourtv, which made this much easier than starting from scratch. Thanks to Gathin23 and the [cleanyourtv](https://github.com/Gathin23/cleanyourtv) contributors, epochcoder for the Homelab companion, the Immich, immich-kiosk and Jellyfin folks, the Wikimedia Commons photographers, and the LINUX Unplugged crew for the tip.

Thanks for reading.
