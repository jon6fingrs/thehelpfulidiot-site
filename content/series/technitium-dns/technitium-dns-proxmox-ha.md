+++
title = "Making Technitium DNS Survive a Proxmox Host Failure"
date = 2026-11-01T10:00:00
path = "technitium-dns-proxmox-ha"
description = "Adding ZFS replication and Proxmox HA to a two-container Technitium DNS setup, the order of operations that tripped me up, a real migration test, and Uptime Kuma monitoring."

[taxonomies]
category = ["Self Hosting"]
tag = ["home lab", "dns", "technitium", "proxmox"]
+++

With the Technitium cluster running, DNS was redundant but DHCP was not. If the host running CT 701 died, CT 702 would keep answering queries, but nothing would issue new leases until the primary came back. Proxmox HA with ZFS replication can fix that, with caveats.

## The Hardware

I have a four-node Proxmox cluster with a qdevice:

- **pve-main** and **pve-backup**: the two capable machines, in different parts of the house. Both have `local-zfs` and all five VLAN bridges.
- **pve-lite-1** and **pve-lite-2**: weaker machines I don't want running these containers.

Since both containers sit on ZFS, Proxmox replication fits.

## Replicate the Disks

On pve-main, replicate CT 701 every minute:

```bash
pvesr create-local-job 701-0 pve-backup --schedule '*/1'
```

On pve-backup, replicate CT 702 every five minutes:

```bash
pvesr create-local-job 702-0 pve-main --schedule '*/5'
```

Wait for a successful first sync before enabling HA. A job showing `OK` with no `LastSync` hasn't proven anything:

```bash
pvesr status
```

ZFS replication is asynchronous. If a host dies suddenly, writes since the last snapshot are lost, including recent DHCP lease changes. I'm accepting that tradeoff; HA doesn't remove it.

## HA: The Order Matters

Creating placement rules first fails:

```text
create ha rule failed: cannot use unmanaged resource(s) ct:701.
```

A container has to be added to HA *before* a rule can reference it:

```bash
ha-manager add ct:701 --state started
ha-manager add ct:702 --state started
```

Then the strict node-affinity rules. Each container prefers its own host and may run on the other, but never on the weak nodes:

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

`ha-manager status` then showed both containers started on their preferred hosts.

## Actually Test a Migration

A config that looks right isn't the same as one that works. I migrated CT 702, the DNS-only secondary, to pve-main and back, so DHCP was never at risk. The first attempt was refused:

```text
cannot migrate resource 'ct:702' to node 'pve-main'
- resource 'ct:702' not allowed on target node 'pve-main'
```

pve-main was in the allowed list, so this was confusing. The culprit was failback: with it enabled, Proxmox won't accept a manual move to the lower-priority node while the preferred node is healthy. Turn it off temporarily:

```bash
ha-manager set ct:702 --failback 0
ha-manager migrate ct:702 pve-main
```

Afterwards both containers showed as started on pve-main. The real test was DNS, and it passed:

```bash
dig @192.168.10.4 example.com +short
dig @192.168.10.4 snapchat.com +noall +comments
```

The secondary kept its IP on the new host, resolved public names, and the blocked lookup still named the expected VLAN0 list. Then I moved it home and restored failback:

```bash
ha-manager migrate ct:702 pve-backup
ha-manager set ct:702 --failback 1
```

I did **not** kill a host, and I did not migrate CT 701. What I tested is a controlled relocation of the DNS-only container. Automatic recovery after a hard failure still depends on quorum, fencing and a recent replicated snapshot.

## Monitoring With Uptime Kuma

I want to hear about a dead DNS server before someone says the internet is broken. In Uptime Kuma I created one DNS monitor per server that queries an internal name and checks the answer:

| Setting | Primary | Secondary |
|---|---|---|
| Hostname | `dns-lists.home.example` | `dns-lists.home.example` |
| Resolver | `192.168.10.3` | `192.168.10.4` |
| Record type | `A` | `A` |
| Expected answer | `192.168.10.111` | `192.168.10.111` |
| Interval | 60 seconds | 60 seconds |

That tests far more than "port 53 is open". It doesn't prove DHCP is healthy, and monitoring from the same physical host won't help when that host loses power, so think about where the monitor runs.

## Was It Worth It?

Yes, with limits. DNS has two independent servers, DHCP can be recovered on the other strong host, and I've seen a real container move without breaking resolution. But DHCP is still active on one instance, a hard failure needs HA recovery, and replication can lose recent changes. I still need to watch it over time before I call it boring, which is what I'm hoping for.

If you try something similar: audit your AdGuard rules first, migrate DHCP one VLAN at a time, keep blocklists out of the app config, and test at least one real relocation. A working DNS answer after moving a container is much more reassuring than a green check mark.
