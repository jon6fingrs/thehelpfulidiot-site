+++
title = "UPDATE 2: A Wired Sonoff Zigbee Alternative"
date = 2021-10-18
updated = 2024-04-15
path = "update-2-a-wired-sonoff-zigbee-alternative"
description = "The updates for this little device keep coming. Thanks to the folks leaving comments, we keep getting more information. I apologize for not noticing this…"

[taxonomies]
category = ["Smart Home"]
tag = ["eachen", "ZB-GW03", "zigbee2tasmota"]
+++

**[ORIGINAL POST](/a-wired-sonoff-zigbee-alternative)**

**[UPDATE 10/15: READ IF YOU PLAN TO USE HUB WITH ZHA](/update-a-wired-sonoff-zigbee-alternative)**

The updates for this little device keep coming. Thanks to the folks leaving comments, we keep getting more information. I apologize for not noticing this myself, but I did not spend any time trying Zigbee2Tasmota on this device having played with it enough on the Sonoff hub.

A commenter, Ronald, noted that using Zigbee2Tasmota, attempting to pair Zigbee devices caused the hub to reboot. I confirmed this myself, and tried with both Zigbee firmware packages from the [EmberZNet NCP UART EZSP firmware page.](https://github.com/arendst/Tasmota/tree/development/tools/fw_SonoffZigbeeBridge_ezsp)

I attempted to build a firmware using the development branch of Tasmota instead of the Release branch, but it totally bricked my coordinator. After re-soldering and flashing again, I tried the [unofficial Tasmota32-zigbeebridge.bin](https://github.com/tasmota/install/raw/main/firmware/unofficial/tasmota32-zigbeebridge.bin) mentioned on the [Blakadder Template Repo](https://templates.blakadder.com/ewelink_ZB-GW03.html). At the time of this writing, the Tasmota version is 9.5.0.9. Miraculously, I was able to pair devices as expected.

![](/wp-content/uploads/2021/10/tasmota-pairing.jpg)
*Device allowed to join*

After flashing this firmware, you would set it up following the instructions from the [initial post](/a-wired-sonoff-zigbee-alternative) by changing the template and then disabling WiFi if desired.

To use ZHA, I would still recommend you follow the instructions from the[ first update](/update-a-wired-sonoff-zigbee-alternative) and building a custom firmware so that the necessary rules to self-correct following a cold boot will work.

Hopefully, whatever fixes exist in the nightly build will make their way to the stable branch and a single firmware will be able to accomplish ZHA and Zigbee2Tasmota.

Please keep me updated with any issues or questions. Thanks!

**[ORIGINAL POST](/a-wired-sonoff-zigbee-alternative)**

**[UPDATE 10/15: READ IF YOU PLAN TO USE HUB WITH ZHA](/update-a-wired-sonoff-zigbee-alternative)**

**UPDATE 10/30: **The above issue was acknowledged on [Github](https://github.com/arendst/Tasmota/issues/13350) and apparently had something to do with the serial communication in the Tasmota firmware. As noted above, that is why the unofficial zigbeebridge firmware works. It containts a fix for the serial communication.
