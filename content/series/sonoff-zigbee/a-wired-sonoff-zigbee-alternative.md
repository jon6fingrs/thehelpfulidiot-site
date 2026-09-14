+++
title = "A Wired Sonoff Zigbee Alternative"
date = 2021-09-29
updated = 2024-04-15
path = "a-wired-sonoff-zigbee-alternative"
description = "Many of us have seen the Sonoff Zigbee Hub and how easy it is to flash to Tasmota thanks to many awesome videos and my personal favorite by DigiblurDIY…"

[taxonomies]
category = ["Smart Home"]
tag = ["eachen", "esp32", "home assistant", "tasmota", "ZB-GW03"]
+++

**[UPDATE 10/15: READ IF YOU PLAN TO USE HUB WITH ZHA](/update-a-wired-sonoff-zigbee-alternative)**

**[UPDATE 10/18: READ IF YOU PLAN TO USE HUB WITH Zigbee2Tasmota](/update-2-a-wired-sonoff-zigbee-alternative)**

**UPDATE 12/5: We've come full circle. The amazing developers of Tasmota have fixed the issue causing serial port disconnections to the zigbee radio with Tasmota 10. Now, the below instructions can be followed, without relying on the previous update posts from 10/15 and 10/18. The uploaded precompiled Tasmota firmware below has been updated to the newest version as of today.**

Many of us have seen the Sonoff Zigbee Hub and how easy it is to flash to Tasmota thanks to many awesome videos and my personal favorite by [DigiblurDIY](https://www.digiblur.com/2020/07/how-to-use-sonoff-zigbee-bridge-with.html). The device is amazing and works well, but some things like your Zigbee bridge shouldn't rely on WiFi.

Recently, another amazing individual going by Tube has created a homemade Franken Zigbee router using an ESP32 board, ethernet, zigbee, and a 3D printed case. It comes preflashed with ESPHome and is instantly compatible with Home Assistant ZHA or Zigbee2MQTT. However, each one of these devices is being made by hand and supply cannot meet demand.

I came across another wired zigbee hub using an ESP32 - [the EACHEN Zigbee Bridge Pro](https://ewelink.eachen.cc/product/eachen-ewelink-zigbee-bridge-pro-zbbridge-pro/). For only $30, I thought I would give it a try. It shipped from China, but arrived fairly quickly after only a couple of weeks.

![](/wp-content/uploads/2021/09/IMG_8685-1024x768.jpg)
*The hub*

![](/wp-content/uploads/2021/09/IMG_8686-1024x768.jpg)
*An ethernet port, a USB-C power port, and a reset pin hole*

The device is probably the same size as the Sonoff Zigbee Router. It is easy enough to disassemble though since there are no screws and the bottom can simply be pried off.

![](/wp-content/uploads/2021/09/IMG_8688-1024x768.jpg)
*The board*

The board pops right out. It is now ripe for flashing and you can see some solder still on mine. My experience with Tasmota so far had been with mainly Tuya-convert and flashing the Sonoff Zigbee router which did not require soldering. This was my first time soldering and was way more fun than I expected.

Now before we get to soldering and flashing, we need to compile our own Tasmota firmware. We need to make sure Tasmota has access to the Ethernet port and the Zigbee Radio. As in all things Tasmota, [Blakadder ](https://templates.blakadder.com/ewelink_ZB-GW03)has a page devoted to this device and instructions. The instructions were excellent, but assumed a certain level of knowledge to compile the firmware. Having not done this before, this part took me the longest. The tasmota32-zigbeebridge precompiled firmware mentioned on the site did not provide ethernet access or else this process would have been a lot easier.

After much trial and error, the easiest way I found to compile this firmware was by going to [GitPod](https://gitpod.io/#https://github.com/arendst/Tasmota/tree/master). After you log in, you are taken to a VS code window prepopulated with the latest Tasmota build.

![](/wp-content/uploads/2021/09/gitpod-1024x493.png)

The instructions from Blakadder's website say to edit two files- user_config_override.h and platform_override.ini.

'Platform_override.ini' is located in the root directory - /workspace/Tasmota. Open the file, scroll to the bottom, and add:

```ini
[env:tasmota32-EWELINK]
extends                 = env:tasmota32
board_build.f_cpu       = 240000000L
board_build.f_flash     = 40000000L
build_flags             = ${env:tasmota32_base.build_flags} -DFIRMWARE_EWELINK
```

![](/wp-content/uploads/2021/09/image-2-1024x395.png)

Now find the 'user_config_override.h' file which is located in the tasmota subdirectory (/workspace/Tasmota/tasmota). Open that file, erase all its contents and replace with:

```c
#ifdef FIRMWARE_EWELINK
  #warning **** Build: FIRMWARE FOR EWELINK ZB-GW03-V1.2 ****

  #undef  SERIAL_LOG_LEVEL
  #define SERIAL_LOG_LEVEL LOG_LEVEL_NONE

  #define USE_ZIGBEE
  #undef  USE_ZIGBEE_ZNP
  #define USE_ZIGBEE_EZSP
  #define USE_UFILESYS
  #define USE_ZIGBEE_EEPROM // T24C512A
  #define USE_TCP_BRIDGE
  #undef  USE_ZIGBEE_CHANNEL
  #define USE_ZIGBEE_CHANNEL 11 // (11-26)
  
  #define USE_ETHERNET
  #undef  ETH_TYPE
  #define ETH_TYPE 0 // ETH_PHY_LAN8720
  #undef  ETH_CLKMODE
  #define ETH_CLKMODE 3 // ETH_CLOCK_GPIO17_OUT
  #undef  ETH_ADDRESS
  #define ETH_ADDRESS 1 // PHY1
#endif
```

Ok, so those two parts were relatively easy, but the next part on how to compile took me probably longer than it should have to figure it out. In the terminal at the bottom of the screen, while in the /workspace/Tasmota directory, type the following:

```bash
platformio run -e tasmota32-EWELINK
```

![](/wp-content/uploads/2021/09/image-1-1024x321.png)

Now wait patiently for the new firmware to compile. Once it does, it can be found in /workspace/Tasmota/build_output/firmware. Download 'tasmota32-EWELINK.bin.

[tasmota32-EWELINK](/wp-content/uploads/2021/12/tasmota32-EWELINK.bin)

~~I compiled this on 10/7/2021, Tasmota32 9.5.0. I promise that I did not tamper with it (and would not know how to tamper with it if I wanted), but you should probably not download firmware from some random guy on the internet.~~

This is Tasmota 10 firmware compiled 12/5/21 using the above method. It should work as intended without the previously described work-arounds.

**NOTE: As reported by erkoc, my new tasmota firmware** **based on v10 was still giving him the same issue with reboots losing connection to ZHA without manual intervention. He forked Tasmota32 and made sure the serial communication patch was included. He has instructions on how to compile your own or you can simply download his precompiled version.**

[**https://github.com/vahempio/Tasmota-for-eWeLink**](https://github.com/vahempio/Tasmota-for-eWeLink)

Ok, now that we have the firmware, it's time to start flashing. Since we have an ESP32. I do not believe we can use Tasmotizer. I have Windows and used [ESP-Flasher-Windows-x64](https://github.com/Jason2866/ESP_Flasher/releases). Open it up, choose your serial port, the firmware we just compiled.

Now the fun part with soldering. Below I have a photo of the ESP32 board and the corresponding connection on my Serial Adapter (I use this [one](https://www.amazon.com/gp/product/B00IJXZQ7C/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1)).

![](/wp-content/uploads/2021/09/image-3-1024x767.png)
*ESP32 board - labels point to corresponding pin on Serial Converter*

![](/wp-content/uploads/2021/09/image-4-1024x770.png)
*Serial Converter - labels point to corresponding pin on ESP32*

Now Flash.

Once you finish, it's a matter of setting up Tasmota and a few more finishing touches.

Set up Tasmota through the access point first and add this Template by issuing the following command:

```
backlog Template {"NAME":"ZB-GW03-V1.2","GPIO":[0,0,3552,0,3584,0,0,0,5793,5792,320,544,5536,0,5600,0,0,0,0,5568,0,0,0,0,0,0,0,0,608,640,32,0,0,0,0,0],"FLAG":0,"BASE":1} ; module 0
```

From this [website](https://github.com/arendst/Tasmota/tree/development/tools/fw_SonoffZigbeeBridge_ezsp), select `ncp-uart-sw-6.7.8_115200.ota`. Go to the upgrade firmware screen to update the zigbee radio. The device will automatically recognize this as firmware for the zigbee radio and will apply it accordingly.

Now try plugging the device in to Ethernet. I noticed it was sort of strange and took a couple reboots and unplugging and plugging the cable back in, but I saw messages about setting up the Eth connection in the console. There was no real way to change Ethernet settings like you can with WiFi, but I noticed two DHCP listings in my router. Once Ethernet is set up, you can disconnect WiFi with the following, but do not do the following until Ethernet is set up! Make sure the first command turning WiFi off works first before applying the subsequent rule which will disable it on each reboot. The first command by itself will not persist across reboots.

```
Wifi 0
backlog rule2 on system#boot do Wifi 0 endon ; rule2 1
```

If something went wrong and now you are locked out of the device because Ethernet isn't working and WiFi is down, you can try [Tasmota device recovery](https://tasmota.github.io/docs/Device-Recovery/#fast-power-cycle-device-recovery).

The device is now set up to use with [Zigbee2Tasmota](/how-to-use-zigbee2tasmota-with-home-assistant). For Home Assistant, there are a few more steps.

To integrate with Home Assistant, we must remap the Zigbee Tx and Zigbee Rx pins directly to TCP Tx and TCP Rx. This will disable Zigbee2Tasmota, but will allow the device to integrate with Home Assistant. Use the following command to update the template:

```
backlog template {"NAME":"ZHA-bridge","GPIO":[0,0,5472,0,5504,0,0,0,5793,5792,320,544,5536,0,5600,0,0,0,0,5568,0,0,0,0,0,0,0,0,608,640,32,0,0,0,0,0],"FLAG":0,"BASE":1} ; module 0
```

Notice the change in the third and fifth positions. Afterwards, it will be possible to start the TCP Server which is what ZHA needs to connect to the coordinator.

Enter the following from the console to turn on the webserver for the Zigbee radio:

```
backlog rule1 on system#boot do TCPStart 8888 endon ; rule1 1 ; tcpstart 8888
```

Finally, you can jump into Home Assistant and set up the device for ZHA exactly how it's (masterfully) described by DigiBlur.

[https://www.digiblur.com/2020/07/how-to-use-sonoff-zigbee-bridge-with.html](https://www.digiblur.com/2020/07/how-to-use-sonoff-zigbee-bridge-with.html)

Thanks for reading. I hope this helps fill in the blanks for some folks like myself who are not as familiar with the inner workings of Tasmota. Please let me know if you have any questions.

Thanks to DigiBlur and Blakadder and all the other folks who did the hard work in getting this device to work.

## Alternative: a single template, no toggling

A reader working through this guide found a cleaner approach that avoids the
ZHA/Z2T toggling described above entirely. Rather than the `ZHA-bridge`
template, use:

```
backlog template {"NAME":"Zig_Bridge32","GPIO":[1,1,5472,1,5504,1,1,1,5793,5792,320,544,5536,1,5600,1,0,1,1,5568,0,1,1,1,0,0,0,0,608,640,32,1,1,3552,3584,1],"FLAG":0,"BASE":1}; module 0;
```

The reasoning: the `ZHA-bridge` template has no Zigbee Tx/Rx GPIOs at all, so
Tasmota never resets the EZSP chip at boot. Mapping Zigbee Rx and Tx to
otherwise unused GPIOs means the reset does happen, and the TCP connection
works across a cold start. The Zigbee2Tasmota UI is still visible but unused.

For Zigbee2MQTT, adding this to your config makes it reconnect within a minute
of a bridge reboot:

```yaml
availability:
  active:
    timeout: 1
```

## Link to Purchase

Affiliate Link:

[AliExpress.com Product - EACHEN EWeLink Zigbee Bridge Pro (Zbbridge Pro)](https://s.click.aliexpress.com/e/_9IDiIh)

[eWelink ZigBee 3.0 Smart Wired Wireless Gateway Hub](https://s.click.aliexpress.com/e/_Ac5sZP)

Non-Affiliate Link:

[AliExpress.com Product - EACHEN EWeLink Zigbee Bridge Pro (Zbbridge Pro)](https://www.aliexpress.com/item/4000459723849.html)

e[Welink ZigBee 3.0 Smart Wired Wireless Gateway Hub](https://www.aliexpress.com/item/1005003020568421.html)

EACHEN Website:

[EACHEN eWeLink Zigbee Bridge Pro (zbbridge pro)](https://ewelink.eachen.cc/product/eachen-ewelink-zigbee-bridge-pro-zbbridge-pro/)

---

CORRECTION 10/2: added steps to remap zigbee Tx and Rx to TCP.

CORRECTION 10/7: made changes based on feedback from /u/Vertigo722. Edited platformIO text. Changed some order of setup.

CORRECTION 10/14: hard reset of the coordinator breaks connection with ZHA until toggled back to Z2T and then back again. Using this firmware and the rules below automatically toggle back and forth only on cut power. Hopefully this workaround fixes things for now.

[tasmota32-EWELINK-1](/wp-content/uploads/2021/10/tasmota32-EWELINK-1.bin)

**[UPDATE 10/15: READ IF YOU PLAN TO USE HUB WITH ZHA](/update-a-wired-sonoff-zigbee-alternative)**

**[UPDATE 10/18: READ IF YOU PLAN TO USE HUB WITH Zigbee2Tasmota](/update-2-a-wired-sonoff-zigbee-alternative)**
