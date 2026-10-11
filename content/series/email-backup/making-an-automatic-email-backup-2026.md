+++
title = "Making an Automatic Email Backup (2026): One Repo, Better Search"
date = 2026-10-11
path = "making-an-automatic-email-backup-2026"
description = "Five years in, my self-hosted email archive gets cleaned up: four repos become one, Solr is replaced by Dovecot's built-in search, All Mail and Flagged folders finally work, and certificate renewals stop needing a manual restart."

[taxonomies]
category = ["Self Hosting"]
tag = ["email", "home lab", "claude"]
+++

I have been running this email setup for about five years now. Every email from my Fastmail account gets copied to my home server, Dovecot serves that copy back to me over IMAP, and my iPhone connects to it over a WireGuard split tunnel wherever I am. It has been remarkably stable. It also means I own a copy of every email I have ever received, and I can keep the mailbox at my provider trimmed without losing anything.

In 2024 I added Solr so that searching from my phone didn't take forever. Since then I had kept tweaking things on my server, and at some point I realized I no longer knew what I was actually running. The code was spread across four GitHub repos (dovecot, mbsync, solr, and an example compose file tying them together), and none of them matched my server. The running containers were the only real source of truth.

So, like I did with [my Home Assistant setup](/cleaning-up-six-years-of-home-assistant-with-claude), I sat down with Claude and cleaned it up. I pulled the config files out of the running containers, Claude compared them with the repos and my old posts, and we rebuilt the whole thing as one repo: [mailstack](https://github.com/jon6fingrs/mailstack). Claude did the reading, writing and testing. I answered questions and made the decisions.

![Before: four repos and four containers. The Dovecot repo said 2.3 while the server ran a 2.4 image I had built myself, it ran chown on every start, debug logging was on, and certificate renewals needed a manual restart. mbsync used cron and sudo and had the password written into its config. Solr used up to 4 GB of memory, ran nightly cron jobs and had port 8983 open on the LAN with no password. Tika had no version pinned, so it was whatever was newest when I last pulled it (2.9.0). After: one repo and three containers. Dovecot 2.4.5 with built-in search that matches partial words, All Mail and Flagged folders, automatic certificate reloads and read-only certificates. mbsync 1.5.1 runs a simple loop as my own user and never writes the password to disk. Tika 4.1 runs on a private network. Versions are pinned, a 23-check test runs on every change, and images are built for amd64 and arm64.](/img/2026/10/mail-before-after.png)
*Then and now*

## What We Found

In retrospect, my amateur attempt at building this was successful, but it wasn't as clean as I had thought.

- **The repos didn't match my server.** GitHub still had the 2024 version, built on Dovecot 2.3. My server was running a Dovecot 2.4 image I had built myself at some point and tagged `2.4.1-beta-3`, which wasn't in any repo.
- **My "All Mail" and "Flagged" folders never existed.** The config labelled them, but the folders they pointed at were never created. I just never noticed.
- **Solr was open to my whole network.** Port 8983 was published with no password. Anyone on my LAN could have read or deleted the search index.
- **Debug logging was still on**, writing a line for every little thing Dovecot did.
- **The startup script changed permissions on everything.** Every time Dovecot started, it ran `chown` and `chmod` on my entire mail archive *and* on my certificate folder. More on why that mattered below.
- **New mail wasn't indexed until I searched.** mbsync writes new mail straight to disk, and Dovecot only indexes automatically when mail is delivered through it. So the first search after new mail arrived had to index it on the spot.

## Search: Goodbye Solr

This was the biggest change, and honestly the one I didn't see coming. I added Solr in 2024 because I assumed it was the only option. Without some kind of index, Dovecot really does read every message one by one for each search, and with a few hundred thousand emails that is painfully slow.

It turns out Dovecot now has a search index built in, called [flatcurve](https://doc.dovecot.org/latest/core/plugins/fts_flatcurve.html). It keeps its index right next to the mail, so there's no separate Java service to run. Tika is still there to read attachments.

I didn't want to swap it in on faith, so Claude generated a test archive of 50,000 emails (made from public-domain books, with a few words planted on purpose) and ran the same searches against both.

![Search on a 50,000-message test archive. Searching for "invo" finds "invoice": 0 hits with Solr, 513 with flatcurve. Accents, word variants like swimming and swims, and text inside attachments work with both. Searching all folders takes about 0.3 seconds with either. Solr builds the index faster, 18 seconds against 45. Solr was using about 350 MB of memory on my server; flatcurve needs none extra. Solr is an extra service to run and update, with Java, schema files, cron jobs and a port to lock down; flatcurve is none. Index size: 14 MB for Solr, 66 MB for flatcurve, and 192 MB for flatcurve with mid-word matching, against 199 MB of mail. A note says Solr can also do typo-tolerant search, but only when a mail app asks for it specially; Dovecot doesn't advertise it and common mail apps never ask, so in practice it goes unused.](/img/2026/10/mail-search.png)
*Same searches, same test archive. Green marks the winner of each row*

The first row is the one I care about most. As you type, the iPhone's Mail app only searches the mail that's already on the phone. When that doesn't turn up what I want, I hit Search and it asks the server to search the whole archive, sending whatever is in the box at that moment. Solr only matches whole words, so a partial word like "invo", or the first half of someone's name, came back empty. Flatcurve matches the start of words, so the server now finds "invoice" from "invo", much like the phone's own search does.

![A mock-up of iPhone Mail after searching the All folder on the server for "invo", showing five invoices from different folders and years, each with "invo" highlighted](/img/2026/10/mail-phone-search.png)
*A mock-up with made-up mail (not my inbox), but this is the idea: a partial word sent to the server now finds things*

### Why flatcurve anyway

Solr isn't bad at this. Its index is a fraction of the size, it builds that index faster, and searches were just as quick with either one. So why switch?

- **One less thing to run.** Solr is a whole Java application with its own schema files, its own cron jobs to commit and optimize the index, its own upgrades, and its own port, which, as I found out, I had left open to my network. Flatcurve is part of Dovecot. For a self-hoster, every service you don't run is one you never have to fix.
- **Memory.** Solr was using about 350 MB on my server just sitting there. Flatcurve needs nothing extra.
- **Less disk churn.** That same Solr container had written 12 GB to disk in about three weeks, I suspect mostly from the nightly optimize rewriting the whole index.
- **Partial words**, as above.

The price is disk space. My Solr index is 2.75 GB, and going by the test I expect flatcurve's to land somewhere around 13 GB, so roughly 10 GB more once Solr is gone. On a server with room to spare, that's an easy trade for less complexity, less memory and better partial matches. If your disk is tight, Solr is still a perfectly good choice.

Two smaller notes:

- **Typo-tolerant ("fuzzy") search isn't available.** Solr can do it and flatcurve can't, but only when a mail app asks for it specially. Dovecot doesn't advertise it, and the common mail apps, iPhone Mail included, don't ask, so in practice nothing changes.
- **Matching from the middle of words** (so "voice" would find "invoice") is also possible, but it tripled the index again, so it's off by default.

## All Mail and Flagged, For Real This Time

Since those folders never existed, we built them properly. They're Dovecot "virtual" folders: live views over the real folders, so nothing is copied.

- **All** is every message except Trash and Spam. Searching it searches the whole archive at once.
- **Flagged** is every flagged message from every folder. Unflag something there and it's unflagged where it really lives.

![A mock-up of iPhone Mail's mailbox list for the archive account: Inbox, Drafts, Sent, Archive, Spam, Trash and a couple of personal folders, then a Virtual section with two new folders, All and Flagged](/img/2026/10/mail-phone-folders.png)
*Another mock-up: the two new folders show up under Virtual*

The Spam and Archive folders are now labelled properly too, so the iPhone knows which folder is which when I archive something or mark it as junk.

## Certificates That Renew Themselves

This one fixed an annoyance I had stopped even thinking about. My certificate is a wildcard certificate that Traefik gets for my domain. A job pulls it out of Traefik every night, and Syncthing copies it to every machine that needs it, including the mail server.

Two things went wrong regularly. Dovecot only reads its certificate when it starts, so after a renewal it kept serving the old one until I restarted it by hand. And because the old startup script ran `chown` and `chmod` on the certificate folder every time, Syncthing saw "changes" it didn't make and got confused about permissions. I would clear the errors and it would fix itself, but it was always something.

![How certificates get to Dovecot now. 1, web server: Traefik renews the certificate and a nightly job copies it out of acme.json as cert.pem and key.pem. Syncthing copies the folder to the mail server. 2, mail server: the folder is mounted read-only, so Dovecot can read the files but never changes them, where before it ran chown and chmod on every start. Every 5 minutes it checks whether the files changed. 3, Dovecot: once the new certificate and key match, it runs doveadm reload, where before it needed a manual restart.](/img/2026/10/mail-certs.png)
*No more restarting Dovecot after a renewal*

Now the folder is mounted read-only, so nothing ever touches it, and Dovecot checks every five minutes whether the files changed. When they have, and the new certificate actually matches the key (so a half-synced file can't break anything), it reloads itself.

## Smaller Things That Add Up

- **Passwords stay out of files.** The old images pasted my passwords into config files with `sed` (which could also break on passwords containing certain characters). Now mbsync asks for the password only when it logs in, and both passwords can come from Docker secret files if you don't want them in environment variables.
- **No more cron inside containers.** mbsync just runs in a loop, with the interval in a setting. I'm setting mine to two minutes, so mail reaches my server faster.
- **New mail gets indexed in the background** within a couple of minutes of arriving, so searches don't stall on it.
- **Nothing runs as root that doesn't need to.** mbsync runs as my own user. Tika sits on a private Docker network with no internet access and no published ports, since it has no password.
- **Everything is pinned and tested.** Every change runs a test that starts the whole stack against a throwaway mail server and checks 23 things: syncing, logging in, searching (including inside attachments), the virtual folders, certificate reloads, and that deleting mail at the provider never deletes my local copy. GitHub then builds the images for both regular PCs and ARM boards like a Raspberry Pi.

## What About Push?

I wanted to mention this because I asked about it myself. The iPhone's Mail app only does true background push for iCloud, Exchange and a few big providers, not for a self-hosted IMAP server like this one. With Mail open, new mail shows up instantly. Otherwise the phone checks on the schedule under Settings → Apps → Mail → Mail Accounts → Fetch New Data. There's no good way around that, so the best I can do is keep the sync interval short.

## Switching Over

The nice part is that your mail folder doesn't change. Message numbers and read/flagged states carry over, so mail apps don't re-download anything, and mbsync picks up exactly where the old container left off. The settings have new names, though, so it's a one-time edit:

```bash
mkdir -p ~/mailstack && cd ~/mailstack
curl -fsSLO https://raw.githubusercontent.com/jon6fingrs/mailstack/main/compose.yaml
curl -fsSL -o .env https://raw.githubusercontent.com/jon6fingrs/mailstack/main/.env.example
nano .env                  # fill in your settings
docker compose up -d
```

If you run your stacks through Portainer like I do, the settings go in the stack's **Environment variables** section instead of a `.env` file, and the compose file doesn't need any changes.

The [migration guide](https://github.com/jon6fingrs/mailstack/blob/main/MIGRATING.md) has a table mapping every old setting to its new name, and how to go back if you need to. The search index gets built once in the background after the switch. It took the test archive under a minute, and a big archive with lots of attachments can take an hour or more. Mail works normally in the meantime.

The old `thehelpfulidiot/dovecot`, `mbsync` and `solr` images stay on Docker Hub so nothing breaks for anyone using them, but they won't be updated.

## How My Switch Went

I switched my own server over the morning I finished this post. It's working, but not before I tripped over my own feet a couple of times.

- **Nothing re-downloaded.** mbsync's first run went through all 42 of my folders and came back with `Near: +0`, meaning there was nothing new to copy. It picked up exactly where the old container left off, and a few minutes later it pulled down one new email, which is the whole job.
- **I filled in the settings wrong.** I had loaded the example values into Portainer and only edited some of them, so Dovecot started up with the placeholder username "me", and somehow my real username had ended up in the password field. Living up to the name of this blog.
- **Two small papercuts got fixed along the way.** My old setup took the certificate as just `cert.pem`. The new one wanted `/ssl/cert.pem` and refused to start without it; it now accepts either. And when mbsync couldn't write to my mail folder (my files still belong to the user ID from my old Synology days), its error message only said that. Now it tells you exactly which `PUID` and `PGID` to set.
- **My iPhone said the server wasn't responding.** This was the interesting one. The logs showed the phone logging in fine, turning on IMAP compression, and hanging up a few milliseconds later:

  ```text
  imap-login: Info: Logged in: user=<…>, method=PLAIN, TLS
  imap: Info: Disconnected: Connection closed (COMPRESS finished 0.004 secs ago)
  ```

  My old Dovecot never offered compression; the new one does by default. Switching it off fixed my phone immediately. It's now off in the images, with a test so it can't sneak back in. On a home network or a VPN, compression barely saves anything anyway.
- **mbsync prints `Maildir warning: ignoring INBOX in /mail/` on every run.** That's harmless. It's about how my INBOX folder sits inside the mail folder, INBOX still syncs, and the old container printed it too, just where I never looked.
- **The search index builds in the background.** About 430 MB so far after the first big folder, and still going as I write this. Mail worked normally the whole time.

## Closing

Five years ago this started as an LXC, a couple of config files and a lot of trial and error. It turned into four Docker images that mostly worked, and now it's one repo I actually understand again, with better search than before and one less service to run.

If you're running the old images, I'd love to hear how the move goes. And as always, let me know if you have any questions or if I got something wrong.

Thanks for reading!
