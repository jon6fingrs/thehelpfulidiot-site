+++
title = "UPDATE: A Wired Sonoff Zigbee Alternative"
date = 2021-10-15
updated = 2024-04-15
path = "update-a-wired-sonoff-zigbee-alternative"
description = "So while the documentation in the initial post on how to compile and flash Tasmota to the ZB-GW03 works, there is a bug when using the Tasmotized device…"

[taxonomies]
category = ["Smart Home"]
tag = ["home assistant", "ZB-GW03", "zigbee2tasmota"]
+++

**[ORIGINAL POST](/a-wired-sonoff-zigbee-alternative)**

**[UPDATE 10/18: READ IF YOU PLAN TO USE HUB WITH Zigbee2Tasmota](/update-2-a-wired-sonoff-zigbee-alternative)**

So while the documentation in the initial post on [how to compile and flash Tasmota to the ZB-GW03](/a-wired-sonoff-zigbee-alternative) works, there is a bug when using the Tasmotized device with Home Assistant.

After changing the device to a ZHA Bridge, a power disruption will prevent a reconnection to Home Assistant once power is restored. The only way to reconnect appears to be by switching the device template back to Zigbee2Tasmota, letting it start, and then back to the ZHA Bridge template. Afterwards it will reconnect as usual. A software initiated reboot DOES NOT cause the same issue.

I do not know enough to say exactly why this is the case, but my theory is that the Zigbee2Tasmota template initializes the Zigbee Radio when it boots up and maybe that is not happening with Home Assistant when the device is shut down in an unsafe state.

Fortunately, I have developed a work around which appears to work well and essentially fixes the problem without further intervention.

It requires two rules:

1. Turning on after an unsafe shutdown changes the device back to Zigbee2Tasmota
2. Once the device boots into Zigbee2Tasmota and the Zigbee radio is fully initialized, the device switches back to ZHA bridge.

In my somewhat brief testing, this has worked really well and the device reconnects as expected after an unsafe shutdown without any user intervention.

Unfortunately, to accomplish this, requires a bit more work than one would think. Tasmota only saves one user defined Module at a time, and I was not able to save a rule with template information, probably due to the fact that it is in JSON format. Therefore, I had to compile a new Tasmota firmware, with the two file modifications on the initial instruction page, plus two new modules, one for each template.

[tasmota_template](/wp-content/uploads/2021/10/tasmota_template.h)

To compile it yourself, you just need to replace tasmota_template.h with the following. Towards the end are the modules for ESP32 devices and you can see two additional modules for the ZB-GW03, one for ZHA and one for Zigbee2Tasmota.

1. Module 2 - ZHA_Bridge
2. Module 3 - Zigbee2Tasmota

If you prefer, you can just download the updated firmware below:

[tasmota32-EWELINK-updated](/wp-content/uploads/2021/10/tasmota32-EWELINK-1.bin)

Once you have the new firmware installed, you can use the following rules:

```
backlog rule1 on system#boot do backlog wifi 0; TCPStart 8888 endon; rule1 on
backlog rule2 on Info3#RestartReason=Vbat power on reset do module 3 endon; rule2 on
backlog rule3 on ZbState#Message=Started do module 2 endon; rule3 on
```

The first rule combines rules 1 and 2 from the initial post and sets up the Zigbee Web Server and turns off wifi. If you intend to use wifi (which I probably wouldn't recommend), just use the following instead for the first rule:

```
backlog rule1 on system#boot do TCPStart 8888 endon; rule1 on
```

Rule2 changes the module to Zigbee2Tasmota ONLY when the power is cut and the device undergoes an unsafe shutdown.

Rule3 as soon as the device boots to Zigbee2Tasmota and the Zigbee radio is fully initialized, it switched back to ZHA Radio at which point the device should be able to reconnect to Home Assistant as expected.

An issue has been opened on Github so please reply if you have experienced the same problem:

[https://github.com/arendst/Tasmota/issues/13350](https://github.com/arendst/Tasmota/issues/13350)

Please let me know about any additional issues or if you have any problems with the above solution.

**[ORIGINAL POST](/a-wired-sonoff-zigbee-alternative)**

**[UPDATE 10/18: READ IF YOU PLAN TO USE HUB WITH Zigbee2Tasmota](/update-2-a-wired-sonoff-zigbee-alternative)**
