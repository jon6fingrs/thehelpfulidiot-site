+++
title = "UPDATE 3: ENTER TASMOTA 10.0"
date = 2024-04-09
path = "update-3-enter-tasmota-10-0"
draft = true
description = "I'm sorry for my negligence in keeping my posts uploaded. Have had a lot of things going on at home. Anyway, this should be the final update as Tasmota…"

[taxonomies]
category = ["Smart Home"]
+++

I'm sorry for my negligence in keeping my posts uploaded. Have had a lot of things going on at home. Anyway, this should be the final update as [Tasmota 10.0](https://ota.tasmota.com/tasmota32/release/) appears to have fixed the various issues noted with using the [EACHEN eWeLink Zigbee Bridge Pro](https://ewelink.eachen.cc/product/eachen-ewelink-zigbee-bridge-pro-zbbridge-pro/).

## Updating from Previous

If you have been using the hub on Tasmota 9.x, you can update it to Tasmota 10.0, although, as with all things, if the hub is working for you, you are probably better off leaving it alone.

First, let's disable the rules set previously just to be on the safe side.

```
backlog rule1 off; rule2 off; rule3 off
```

This could be especially important as during the upgrade process, I imagine the ethernet could easily stop working and it will be important to have access to the device over WiFi. So make sure you can do before continuing.

Next, Tasmota 10 is too large to update all at once, so we will first need to perform an intermediary update with a minimal version. Unfortunately, the unofficial minimal version from the tasmota32 download page is still too large

As of writing this post, the options for tasmota32 firmwares are limited on the official download page. However, as previously, there is an unofficial download page of custom firmwares which I imagine are part of the nightly schedule. Unfortunately, this means that the resulting firmware could break at any point. Download it to your computer, then go to your Zigbee Hub and select firmware upgrade:

![](/wp-content/uploads/2021/12/tasmota-upgrade-1.jpg)
*Firmware Upgrade*

Then select the file location on your computer and click start upgrade:

![](/wp-content/uploads/2021/12/tasmota-upgrade-2.jpg)
*Upgrade step 2*
