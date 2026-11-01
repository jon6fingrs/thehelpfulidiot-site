+++
title = "Goodbye AdGuard Home: One DNS Cluster, Five VLANs, and a Little Too Much Proxmox HA"
date = 2026-11-01
path = "goodbye-adguard-home-technitium-dns-cluster"
description = "Replacing five AdGuard Home instances with two clustered Technitium DNS servers, moving DHCP, keeping separate VLAN and kids' blocking policies, and adding Proxmox HA with ZFS replication."

[taxonomies]
category = ["Self Hosting"]
tag = ["home lab", "dns", "technitium", "proxmox", "adguard", "opnsense"]
+++

For the past several years, I've been using AdGuard Home for DNS, ad blocking, and DHCP on my home network. I have five VLANs, and at some point this turned into five separate AdGuard Home instances. One for each network, each with its own settings, blocklists, and DHCP reservations.

It worked. Mostly. Under heavy use, though, I kept getting AdGuard dropouts: lookups that stalled for a moment and made the whole connection feel unstable, even when the internet itself was fine. It probably didn't help that each VLAN had a single DNS server with no redundancy: if that one instance hiccuped, every device on the network felt it. And whenever I wanted to make a change, I had to remember which instance was responsible for what. I had also managed to build several different sets of blocking rules, including a custom list for my kids' iPads. Having five servers that all do essentially the same thing started to feel a little ridiculous.

Naturally, I decided to solve this by building a DNS cluster, migrating DHCP for five networks, creating my own blocklist web server, and putting the whole thing under Proxmox high availability. Definitely the simplest way to spend a weekend.

This is how I moved from AdGuard Home to Technitium DNS Server, including some of the things that didn't work the first time.

## The Old Setup

I run OPNsense as my router and use multiple VLANs to keep the various parts of the house separated. AdGuard Home had ended up deployed once per VLAN:

| Network | Old AdGuard address | Purpose |
|---|---|---|
| VLAN0 | `192.168.10.2` | Main network |
| VLAN10 | `192.168.11.2` | Personal devices |
| VLAN20 | `192.168.12.2` | Separate, essentially unfiltered network |
| VLAN30 | `192.168.13.2` | Guest network: light ad blocking, clients isolated from each other, and a good fit for the kids' iPads |
| VLAN40 | `192.168.14.2` | My "Google network": big-tech devices that talk to their cloud services live here |

VLAN30 is my guest network. It gets light ad blocking, and devices on it aren't allowed to talk to each other, which made it the natural home for the kids' iPads. VLAN40 is where anything from big tech that constantly phones home to a cloud service ends up, so it gets its own filtering rules.

The annoying part wasn't really DNS. It was DHCP reservations, different filtering policies, and the fact that some clients had special rules that didn't apply to the rest of their VLAN.

What I wanted was pretty simple:

1. Two DNS servers, on two physically separate Proxmox machines, with identical local DNS zones and filtering policies.
2. One DHCP server responsible for all five VLANs, so I wasn't maintaining five separate DHCP configurations.
3. Different ad-blocking policies for each VLAN, with exceptions for individual devices.
4. Local recursive DNS, rather than blindly forwarding everything to a public resolver.
5. Recovery when a Proxmox host fails, without having to remember a dozen manual steps.

The finished layout looks like this:

![Diagram of two Technitium DNS containers on separate Proxmox hosts, serving clients on five VLANs and WireGuard, with ZFS replication between the hosts and a local blocklist web server](/img/2026/11/technitium-dns-architecture.svg)
*Two DNS servers, one DHCP server, five VLANs*

Both Technitium instances serve DNS. CT 701 is the only DHCP server; CT 702 is not a second DHCP server. Proxmox HA can restart a failed container using replicated ZFS storage, but this isn't instantaneous or zero-data-loss failover.

## Two Technitium Containers Instead of Five AdGuard Instances

I created two Debian 13 LXCs running Technitium DNS Server 15.6.2. Each has two CPU cores, 2 GB of RAM, and a 16 GB ZFS-backed root disk.

- **CT 701**, `technitium-1`, on PVE-MAIN, runs DNS and DHCP.
- **CT 702**, `technitium-2`, on pve-backup, runs DNS only.

Both Proxmox hosts have the bridges `vmbr0`, `vmbr10`, `vmbr20`, `vmbr30`, and `vmbr40`. Each container has a virtual NIC on every bridge, so it can serve all five VLANs directly.

| Network | CT 701 | CT 702 |
|---|---|---|
| VLAN0 | `192.168.10.3` | `192.168.10.4` |
| VLAN10 | `192.168.11.110` | `192.168.11.111` |
| VLAN20 | `192.168.12.110` | `192.168.12.111` |
| VLAN30 | `192.168.13.110` | `192.168.13.111` |
| VLAN40 | `192.168.14.110` | `192.168.14.111` |

That distinction matters: these are ten IP addresses, but only two DNS servers.

For reference, this is part of the Proxmox configuration for CT 701, with the addresses changed for this post:

```ini
arch: amd64
cores: 2
hostname: technitium-1
memory: 2048
nameserver: 192.168.10.3
net0: name=eth0,bridge=vmbr0,gw=192.168.10.1,hwaddr=02:5A:C3:11:70:01,ip=192.168.10.3/24,type=veth
net1: name=eth1,bridge=vmbr10,hwaddr=02:5A:C3:11:70:02,ip=192.168.11.110/24,type=veth
net2: name=eth2,bridge=vmbr20,hwaddr=02:5A:C3:11:70:03,ip=192.168.12.110/24,type=veth
net3: name=eth3,bridge=vmbr30,hwaddr=02:5A:C3:11:70:04,ip=192.168.13.110/24,type=veth
net4: name=eth4,bridge=vmbr40,hwaddr=02:5A:C3:11:70:05,ip=192.168.14.110/24,type=veth
rootfs: local-zfs:subvol-701-disk-0,size=16G
unprivileged: 1
```

The MAC addresses are made up too. The key is that each interface belongs to the corresponding Proxmox bridge.

## Clustering the DNS Servers

Technitium has built-in DNS clustering. I set the servers up as `ns1.dns-cluster.home.example` and `ns2.dns-cluster.home.example`. The cluster synchronizes my local zones; there are 15 of them in the catalog, including the internal records I use for my various services.

I also kept split-horizon local DNS behavior, so internal names can resolve differently depending on the client network where appropriate.

There is an important distinction here: Technitium DNS clustering is not DHCP clustering. I have one DHCP server, CT 701. CT 702 does not automatically take over issuing leases merely because it's part of the DNS cluster. That's where Proxmox HA comes in later.

## Let Technitium Do Its Own Recursion

I wanted Technitium to resolve DNS recursively using the root DNS servers rather than forwarding every request to OPNsense's Unbound or a public DNS provider.

This initially ran into an old OPNsense DNS redirection rule. Once that was corrected, both Technitium instances could perform recursive lookups. I also checked that DNSSEC validation was doing something useful:

```bash
dig @192.168.10.3 example.com A +short
dig @192.168.10.4 example.com A +short

dig @192.168.10.3 dnssec-failed.org A +noall +comments
```

The intentionally broken DNSSEC domain returned `SERVFAIL`, as it should. It isn't a perfect security audit, but it's a better test than simply checking whether Google resolves.

## Moving DHCP Without Rebuilding Every Reservation

This was probably the part I was most reluctant to touch. DNS failures are annoying; DHCP failures can make the house seem haunted.

I exported the AdGuard configurations and used the existing reservations and lease information to build Technitium's DHCP scopes. The main network alone had 105 reservations. VLAN10 had 19 existing static reservations, plus eight dynamic leases that I converted into reservations as part of the migration.

The new DHCP scopes are:

| Network | DHCP pool | Gateway | DNS servers handed to clients |
|---|---|---|---|
| VLAN0 | `192.168.10.30–254` | `192.168.10.1` | `.3`, `.4` |
| VLAN10 | `192.168.11.2–254` | `192.168.11.1` | `.110`, `.111` |
| VLAN20 | `192.168.12.3–100` | `192.168.12.1` | `.110`, `.111` |
| VLAN30 | `192.168.13.3–100` | `192.168.13.1` | `.110`, `.111` |
| VLAN40 | `192.168.14.3–100` | `192.168.14.1` | `.110`, `.111` |

In the last column, `.110` and `.111` mean the corresponding VLAN's full addresses. For example, `192.168.13.110` and `192.168.13.111` on VLAN30.

I used 24-hour leases and disabled automatic DNS registration from DHCP. I also made sure existing infrastructure addresses, including the new DNS servers and old AdGuard hosts, wouldn't be handed out accidentally.

I migrated the scopes one network at a time and then disabled DHCP on the corresponding AdGuard instance. For VLAN10, I checked a real client renewal and confirmed that my phone received its expected IP and the new DNS servers.

Do not run two independent DHCP servers on the same network with overlapping pools unless you've intentionally designed them to coexist. In this setup, the old AdGuard DHCP services are disabled. They're available as a rollback reference, not as active servers.

## Recreating AdGuard's Blocking Policies

Technitium's Advanced Blocking app was the closest fit for what I was already doing in AdGuard. It supports separate groups, source-network matching, allowlists, blocklists, and Adblock-format lists.

My original AdGuard setup didn't simply block advertisements. Several VLANs also had a long list of blocked services: social media platforms, shopping sites, game launchers, and so on. I wanted those settings to survive the move.

I audited AdGuard's service definitions and converted the simple domain-based rules into ordinary blocklists. The results were roughly:

| Policy | Generated domains |
|---|---:|
| VLAN0 | 719 |
| VLAN10 | 799 |
| VLAN40 | 1,221 |
| Kids' iPads | 748 |

A small number of complex wildcard or exception rules could not be converted cleanly into plain domains. Rather than silently guessing, I saved those rules separately for review. In particular, AdGuard's `denyallow` syntax can't always be represented faithfully by expanding the blocked domain into a simple hosts list.

### The Giant JSON Paste That Didn't Work

My first idea was to put all 2,739 VLAN-specific domains directly into Advanced Blocking's configuration JSON.

This was a mistake.

The browser spent a very long time trying to submit the enormous configuration, then Technitium's web server returned:

```text
Reading the request body timed out due to data arriving too slowly.
See MinRequestBodyDataRate.
```

The fix was much simpler: keep the Advanced Blocking configuration small and serve the bulk domain lists as ordinary text files.

### Hosting the Blocklists Locally

My main server already runs Docker and Nginx Proxy Manager. I created a tiny nginx container to serve the lists from disk.

The files live at:

```text
/opt/docker/technitium-lists/
├── lists/
│   ├── vlan0.txt
│   ├── vlan10.txt
│   ├── vlan40.txt
│   └── kids-ipads.txt
└── nginx.conf
```

The Compose stack is deliberately boring:

```yaml
services:
  technitium-lists:
    image: nginx:stable-alpine
    container_name: technitium-lists
    restart: unless-stopped
    volumes:
      - /opt/docker/technitium-lists/lists:/usr/share/nginx/html:ro
      - /opt/docker/technitium-lists/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    networks:
      - zzzz

networks:
  zzzz:
    external: true
```

Here `zzzz` is the existing Docker network attached to Nginx Proxy Manager, not a special name required by Technitium. A plain static-file nginx configuration is all the container needs.

Nginx Proxy Manager exposes the lists at `https://dns-lists.home.example/`, forwarding to `technitium-lists:80` with a valid HTTPS certificate. Both Technitium servers have an internal DNS record resolving `dns-lists.home.example` to `192.168.10.111`, the proxy's address.

I learned the hard way that the host OS resolver is not necessarily the DNS server you think you're testing. My laptop and Docker host initially resolved the list hostname to a public Cloudflare address rather than my internal reverse proxy. That produced a Cloudflare 403 instead of the list.

To test the local proxy directly, without relying on the client's resolver:

```bash
curl --noproxy '*' \
  --resolve dns-lists.home.example:443:192.168.10.111 \
  https://dns-lists.home.example/vlan10.txt | wc -l
```

The VLAN10 file returned 800 lines, including its comment/header line. Both Technitium LXCs could also fetch the file normally after I corrected their container DNS resolver settings.

One easy-to-miss detail: CT 702 was still using OPNsense (`192.168.10.1`) as its Linux system resolver. Technitium's own DNS responses were correct, but commands such as `curl` inside the LXC resolved the internal hostname incorrectly. Setting its Proxmox `nameserver` to `192.168.10.4` and restarting the container fixed that.

### Advanced Blocking: One Policy Per Network

The useful part of Technitium's Advanced Blocking configuration is that the group names are arbitrary. I created groups named `vlan0`, `vlan10`, `vlan20`, `vlan30`, `vlan40`, `kids-ipads`, and `default`.

Here's an excerpt of the mapping I actually ended up using:

```json
{
  "localEndPointGroupMap": {},
  "networkGroupMap": {
    "192.168.10.0/24": "vlan0",
    "192.168.11.0/24": "vlan10",
    "192.168.12.0/24": "vlan20",
    "192.168.13.0/24": "vlan30",
    "192.168.14.0/24": "vlan40",
    "192.168.13.65": "kids-ipads",
    "192.168.13.66": "kids-ipads",
    "172.20.8.0/24": "vlan10",
    "172.20.8.5": "vlan20",
    "172.20.8.6": "kids-ipads",
    "172.20.8.13": "kids-ipads",
    "172.20.8.14": "kids-ipads",
    "172.20.8.16": "vlan0",
    "0.0.0.0/0": "default",
    "[::]/0": "default"
  }
}
```

This is an excerpt, not a complete Advanced Blocking configuration file. The full configuration also contains the group definitions and blocklist URLs.

The `vlan20` and `default` groups have blocking disabled. The `kids-ipads` group inherits the standard VLAN30 ad-block lists and adds its own service-blocking list:

```json
{
  "name": "kids-ipads",
  "enableBlocking": true,
  "allowTxtBlockingReport": true,
  "blockAsNxDomain": true,
  "blockingAddresses": ["0.0.0.0", "::"],
  "allowed": [],
  "blocked": [],
  "allowListUrls": [],
  "blockListUrls": [
    "https://dns-lists.home.example/kids-ipads.txt"
  ],
  "allowedRegex": [],
  "blockedRegex": [],
  "regexAllowListUrls": [],
  "regexBlockListUrls": [],
  "adblockListUrls": [
    "https://adguardteam.github.io/HostlistsRegistry/assets/filter_1.txt",
    "https://adguardteam.github.io/HostlistsRegistry/assets/filter_2.txt",
    "https://adguardteam.github.io/HostlistsRegistry/assets/filter_27.txt",
    "https://adguardteam.github.io/HostlistsRegistry/assets/filter_3.txt"
  ]
}
```

One advantage of this setup is that I can change the group for a single device simply by assigning it a stable IP. The individual host entries are more specific than the VLAN subnet entries.

### A Nice Little WireGuard Complication

I use WireGuard to connect back to the house when I'm away, with tunnel addresses in `172.20.8.0/24`.

Initially I wanted the blocking policy to depend on which DNS destination the VPN client selected. In other words, send a request to the DNS server's VLAN0 address for VLAN0 filtering, or to its VLAN10 address for VLAN10 filtering. This sounds simple until you remember that I don't want that behavior for everyone on the local network.

Advanced Blocking can match the local destination endpoint, or the client source subnet, but the stock configuration doesn't offer a combined rule like "if the source is WireGuard, then select the group using the destination address." There were ways around this with NAT, extra DNS IP aliases, or a custom app modification. All of them seemed like too much work for something that should be simple.

Instead, I gave each WireGuard client a stable tunnel IP and mapped specific clients to the desired group. Unlisted VPN clients get VLAN10 filtering. One client gets unfiltered VLAN20 behavior, one gets VLAN0, and several get the kids' policy.

It's less clever than I originally imagined, but probably more reliable, which is often how these projects end up.

This policy depends on Technitium seeing the actual WireGuard source IP. If OPNsense source-NATs the requests, the client-specific matches won't work as intended; the query log's client-IP field is the place to check.

### Testing the Policy That Actually Matched

The `dig` response tells you not just whether a domain is blocked, but which group and list blocked it:

```bash
dig @192.168.10.3 snapchat.com A +noall +comments
dig @192.168.10.4 snapchat.com A +noall +comments
```

From a VLAN10 client, both servers returned `NXDOMAIN` with an extended DNS error containing something like:

```text
EDE: 15 (Blocked):
(source=advanced-blocking-app;
 group=vlan10;
 blockListUrl=https://dns-lists.home.example/vlan10.txt;
 domain=snapchat.com)
```

That is far more useful than simply seeing `NXDOMAIN`. It proves that the source-IP policy and the newly hosted blocklist are both being used. The occasional `recursion requested but not available` warning on these locally generated blocked responses wasn't evidence that public recursion was broken; public lookups worked separately.

## Now Make It Survive a Proxmox Host Failure

At this point, DNS was redundant, but my primary DHCP service was still sitting on one Proxmox host. If PVE-MAIN died, the secondary DNS server would keep resolving queries, but nothing would issue new DHCP leases until the primary came back.

I already have a four-node Proxmox cluster with a qdevice:

- **pve-main**: one of the more capable machines.
- **pve-backup**: another capable machine, physically elsewhere in the house.
- **pve-lite-1** and **pve-lite-2**: weaker machines I didn't want running these containers unless I deliberately changed the plan.

The important difference between these four boxes is that PVE-MAIN and pve-backup both have `local-zfs` storage and all five required network bridges. The two Technitium containers use ZFS-backed disks, so Proxmox replication is a good fit.

### Replicate the Container Disks

On PVE-MAIN I created the primary container's replication job:

```bash
pvesr create-local-job 701-0 pve-backup --schedule '*/1'
```

And on pve-backup:

```bash
pvesr create-local-job 702-0 pve-main --schedule '*/5'
```

The first job replicates CT 701 every minute; the other replicates CT 702 every five minutes. I waited for both to complete an initial successful synchronization before enabling HA.

```bash
pvesr status
```

A job saying `OK` with no `LastSync` yet doesn't prove that its first copy has finished. I wanted to see a successful timestamp and no errors.

ZFS replication isn't synchronous storage. If a host suddenly dies, some writes since the most recent snapshot can be lost, including recent DHCP lease changes. That is a tradeoff I'm accepting, not something HA magically solves.

### Proxmox HA: The Order Matters

My first attempt to create the HA placement rules failed:

```text
create ha rule failed: cannot use unmanaged resource(s) ct:701.
```

As it turns out, Proxmox won't let you reference a container in a node-affinity rule until that container has already been added to HA. Once I figured that out, I registered both resources:

```bash
ha-manager add ct:701 --state started
ha-manager add ct:702 --state started
```

Then I added strict node-affinity rules:

```bash
ha-manager rules add node-affinity technitium-701 \
  --resources ct:701 \
  --nodes 'pve-main:2,pve-backup:1' \
  --strict 1

ha-manager rules add node-affinity technitium-702 \
  --resources ct:702 \
  --nodes 'pve-backup:2,pve-main:1' \
  --strict 1
```

This makes PVE-MAIN the preferred host for CT 701 and pve-backup the preferred host for CT 702. Either one is allowed to run on the other machine if necessary. The strict rule excludes the weaker hosts from running them.

The relevant part of `/etc/pve/ha/rules.cfg` now looks like:

```ini
node-affinity: technitium-701
        nodes pve-main:2,pve-backup:1
        resources ct:701
        strict 1

node-affinity: technitium-702
        nodes pve-main:1,pve-backup:2
        resources ct:702
        strict 1
```

`ha-manager status` reported both containers started on their preferred hosts.

### Actually Test a Migration

Of course, a configuration that looks correct is not quite the same thing as a configuration that works.

I decided to migrate CT 702 to PVE-MAIN and back. It's the secondary DNS server, so briefly interrupting it wouldn't take away the primary DHCP service.

My first attempt was rejected:

```bash
ha-manager migrate ct:702 pve-main
```

```text
cannot migrate resource 'ct:702' to node 'pve-main'
- resource 'ct:702' not allowed on target node 'pve-main'
```

This was confusing because PVE-MAIN was explicitly in the list of allowed hosts. The problem turned out to be failback. With automatic failback enabled, Proxmox wouldn't accept a manual migration to the lower-priority host while the higher-priority host was still healthy.

Temporarily disabling failback fixed it:

```bash
ha-manager set ct:702 --failback 0
ha-manager migrate ct:702 pve-main
```

After the migration completed, the output was:

```text
service ct:701 (pve-main, started)
service ct:702 (pve-main, started)
```

And, more importantly:

```bash
dig @192.168.10.4 example.com +short
dig @192.168.10.4 snapchat.com +noall +comments
```

Both tests worked. The secondary kept its IP address even though its underlying Proxmox host had changed. It could still resolve public domains, and the blocked Snapchat request identified the expected VLAN0 blocklist. That was an actual functional test, not just a green check mark in Proxmox.

I then returned CT 702 to pve-backup and restored failback:

```bash
ha-manager migrate ct:702 pve-backup
ha-manager set ct:702 --failback 1
```

The final HA state showed CT 701 running on PVE-MAIN and CT 702 on pve-backup.

I did not deliberately kill a Proxmox host, and I did not run a migration test for CT 701. The tested result is a successful controlled relocation of the DNS-only container. Automatic recovery after a hard host failure still depends on quorum, fencing, and an available replicated snapshot.

## Monitoring It With Uptime Kuma

After all that, it seemed like a good idea to find out if either DNS server stopped working before someone complained that the internet was broken.

I already use Uptime Kuma. I created DNS monitors that query an internal hostname and verify the actual answer:

| Setting | Primary | Secondary |
|---|---|---|
| Type | DNS | DNS |
| Hostname | `dns-lists.home.example` | `dns-lists.home.example` |
| Resolver | `192.168.10.3` | `192.168.10.4` |
| Port | `53` | `53` |
| Record type | `A` | `A` |
| Expected answer | `192.168.10.111` | `192.168.10.111` |
| Interval | 60 seconds | 60 seconds |

This tests much more than whether port 53 is open: the server must actually return the expected internal record. I can add public-recursion checks and web-interface checks separately if I want more detail.

It doesn't prove DHCP is healthy. Nor does monitoring something on the same physical host help much when the entire host loses power, so monitoring placement is worth thinking about too.

## Was It Worth It?

I went from five AdGuard Home instances to two Technitium DNS servers, with a single DHCP configuration covering all five VLANs. The DNS servers synchronize local zones, each VLAN still gets its own filtering rules, the kids' iPads and WireGuard devices have individual policies, and Proxmox can recover either container on the other strong host.

The project had a few detours: an old OPNsense redirect interfering with recursion, the container's own DNS resolver pointing at the wrong place, a giant JSON configuration that timed out, HA rules that couldn't be created in the order I expected, and a perfectly reasonable migration that Proxmox refused until I disabled failback.

So, pretty much a normal weekend in my home lab.

The architecture is more capable than before, but it isn't magical. DHCP is still active on only one Technitium instance. A host failure requires HA recovery, and ZFS replication can lose recent changes. Also, I still need to see how it behaves over time before I can call the migration completely boring, which is really what I'm hoping for.

If you're thinking of making a similar switch, my advice would be to audit your AdGuard rules first, migrate DHCP one VLAN at a time, keep the blocklists separate from the app configuration, and test at least one actual relocation. The configuration screens are reassuring, but a real DNS answer after moving a container is much more reassuring.
