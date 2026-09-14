+++
title = "Controlling Home Assistant with an Old Remote"
date = 2021-10-03
updated = 2024-04-15
path = "controlling-home-assistant-with-an-old-remote"
description = "I, like many other I'm sure, have plenty of old infrared remotes laying around from TVs past. They were just collecting dust, but what if they could be…"

[taxonomies]
category = ["Smart Home"]
tag = ["flirc", "home assistant"]
+++

I, like many other I'm sure, have plenty of old infrared remotes laying around from TVs past. They were just collecting dust, but what if they could be useful again? Well thanks to the [Flirc USB](https://flirc.tv/more/flirc-usb), a small USB IR receiver, those old remotes can be used to control anything your Home Assistant Box can control.

![](/wp-content/uploads/2021/10/image-6-1024x802.png)
*The Flirc USB*

![](/wp-content/uploads/2021/10/image-7.png)
*Banana for scale*

The amazing thing about this device is its simplicity. First, you plug it into a PC, Mac, or Linux machine. Then download the software. The software lets you assign buttons to a virtual keyboard by selecting individual keys and firing your remote at it. Those codes are saved on the device itself, so it can be moved to your Home Assistant Operating System box and will be seen as just an ordinary keyboard. Except, instead of interacting by physically pressing keys, the key is "pressed" when it detects the corresponding infrared frequency.

## Set Up

So let's walk through how this would be set up.

First, [download the software](https://flirc.tv/support/flirc-usb) from the website and plug in the USB device.

![](/wp-content/uploads/2021/10/image-8-1024x763.png)
*Flirc Software*

There are a number of virtual keyboard or remotes you can select. I think selecting a standard keyboard makes the most sense to maximize the number of programmable keys.

Next, click on a key, and it will ask you to press the corresponding button on the remote. You do not need to remember which buttons are mapped to which keys because they will later be identified in Home Assistant by watching the event log.

Once you have recorded all the keys you want, you unplug the device from your computer and plug it into your Home Assistant box.

## Home Assistant

Now the Flirc can be set up in Home Assistant using the [Keyboard Remote](https://www.home-assistant.io/integrations/keyboard_remote/) integration. First, confirm it is recognized by Home Assistant by looking in the Supervisor's Hardware tab.

![](/wp-content/uploads/2021/10/image-9-1024x614.png)
*Flirc recognized in Hardware tab*

Once you see it's recognized, add the following to your configuration.yaml and restart:

```yaml
keyboard_remote:
  - device_name: 'flirc.tv flirc Keyboard'
    type: 'key_down'
```

## Creating Automations:

Now you can make automations capable of anything your Home Assistant can do from the press of a button. To do so, you need to obtain the "key_code" for each programmed button. Go to the Developer Tools and then the Events tab. Listen for events from "keyboard_remote_command_received" and press the individual buttons. For example:

![](/wp-content/uploads/2021/10/image-10-1024x749.png)
*Example of keyboard_remote_command_received response*

So now I know that my remote's "Netflix" button is mapped to keycode 50.

A corresponding automation trigger would look like this:

```yaml
platform: event
event_type: keyboard_remote_command_received
event_data:
  device_name: flirc.tv flirc Keyboard
  key_code: 50
```

And from there it can do whatever you want- turn off lights, lock doors, turn on music, or even turn on your TV using your old remote!

## Logitech Harmony

Now, I happen to be a big fan of the Harmony Remote and its Home Assistant integration. As far as I know, the integration is one way, meaning that you can fire commands through the Harmony but Home Assistant cannot receive commands. If instead of an old remote you wanted to use the Harmony, you could simply set up some dummy device and make sure the the Harmony Hub or an IR mini blaster will have line of sight to the Flirc Receiver. Set up the device in the same way and then you can integrate Home Assistant actions into your Harmony Hub Activity.

## BONUS - MagiQuest Wands

Some of you may be familiar with [MagiQuest](https://en.wikipedia.org/wiki/MagiQuest). It is an interactive live role playing game at many tourist attractions. My family and I, specifically, encountered it at Great Wolf Lodge. To participate, you purchase (expensive) customized wands and can run around the hotel or tourist destination waving it at different objects.

![](/wp-content/uploads/2021/10/image-11-534x1024.png)
*MagiQuest Wand*

Well the wand is actually just an infrared transmitter which is fired when the wand is flicked. Instead of bringing them home and having life-less souvenirs, you can integrate them into Home Assistant using the Flirc!

## Conclusion

I hope this write-up was helpful. For only $19.95 on Amazon, I definitely think it is a good device at a good price with a lot of possibility. Please let me know if you have any questions.

**Affiliate Link**

[FLIRC USB Universal Remote Control Receiver](https://www.amazon.com/gp/product/B01NBRBWS6/ref=as_li_tl?ie=UTF8&camp=1789&creative=9325&creativeASIN=B01NBRBWS6&linkCode=as2&tag=thehelpfulidi-20&linkId=9a56ceec3c171749a83b8b1af6b4555c)

**Non-Affiliate Link**

<meta charset="utf-8">[FLIRC USB Universal Remote Control Receiver](https://www.amazon.com/Universal-Remote-Control-Receiver-Raspberry/dp/B01NBRBWS6?ref_=ast_sto_dp)
