+++
title = "Fully Local Universal Remote Control with Home Assistant"
date = 2024-02-11
updated = 2024-04-09
path = "fully-local-universal-remote-control-with-home-assistant"
description = "I have had a Logitech Harmony remote solution for almost 10 years. In my opinion, it is a very nice product. It integrates nicely into Home Assistant, and…"

[taxonomies]
category = ["Self Hosting"]
tag = ["home assistant", "home lab", "remote"]
+++

## Background

I have had a Logitech Harmony remote solution for almost 10 years. In my opinion, it is a very nice product. It integrates nicely into Home Assistant, and so, while it didn't behave as intuitively as I wanted out of the box, Home Assistant automations were able to modify its behavior so that it largely performed seamlessly in the way that I wanted.

Unfortunately, as with many other quality products, Logitech decided to [discontinue](https://www.tomsguide.com/news/logitech-kills-off-harmony-universal-remotes-but-theres-a-little-good-news) the Harmony line of products.

Luckily, Logitech has learned from its previous mistake when it [discontinued the Harmony Link years earlier](https://arstechnica.com/gadgets/2017/11/logitech-to-shut-down-service-and-support-for-harmony-link-devices-in-2018/). At the time, they announced that the devices would lose support and become bricks. This rustled a few jimmies and so they ultimately shipped a free Harmony Hub (the upgraded, but now current generation of IR hub) to the unhappy customers.

So even though Logitech has announced an end to the Harmony brand, they have stated that they will continue to support the devices currently in the wild. Well this is obviously a relief, but who can say how long we will get this reprieve before Logitech decides they've given us enough of their "free" computing power?

Recently, my dog ate one of my Harmony remotes. I had to purchase a used replacement from ebay. When it came, it was still paired to its previous hub, and trying to repair it set off a very difficult mission which required my downloading the official Harmony software onto a Windows Box so that I could restore my old profile.

It worked, but took several hours and was extremely frustrating to have to rely on a black box to fix something which had become integral to many automations and to my WAF. This got me thinking, how much longer do I have with Harmony? When will this next remote be destroyed? When will Harmony's recovery tools become out-dated and unusable?

This set me off on searching for a more stable, long-term solution.

## Alternatives

So what are the alternatives? Well surprisingly few.

There appears to be a pretty popular Harmony replacement, called the [Sofabaton](https://www.sofabaton.com/). It seems to have received pretty positive reviews all around, and if I'm being honest, I didn't really look into it too much. Regardless of whether or not it behaves locally, I just saw it as trading one walled garden for another. It seemed like you would need an internet connection and the company's servers in order to add new devices. I wanted something that would be totally local.

Immediately, I was drawn to the [Broadlink RM4 mini](https://ebroadlink.com/products/broadlink-rm4-mini-universal-remote-wi-fi-ir-control-hub_certified-wwa-work-with-alexa_-black). It is a cheap IR blaser which can learn from IR remotes, or can use codes found online. It integrates very nicely into Home Assistant, and works over a local connection. I attempted to set it up normally, but there was some issue. The device was added to my wifi but not to my Broadlink account. However, this turned out to be the perfect outcome since I was able to integrate it into Home Assistant and now do not need to worry about a device calling home constantly.

The IR blaser is for my TV and soundbar which are not controllable by wifi. Otherwise, I have a kodi box, an Apple TV, and a Roku. These are all controllable over wifi.

So now, we have a way to interact with my media devices. I can use it through various automations, from my phone, a computer, etc. But I really just want a remote. There is nothing quite like controlling your media with an old-fashioned remote. It is always there and the batteries last like 10 years.

Perhaps there are bluetooth remotes available? My Home Assistant instance is in the basement while the media center is on the first floor. So if I am able to find a bluetooth remote, there needs to be a way to forward all commands to my Home Assistant instance.

Once that's done, it's just a matter of connecting the correct input with the correct output which would be fairly easy.

## Solution: Remote Hardware

After much searching, I came across the [Air Mouse Remote MX3 Pro with Backlit](https://amzn.to/3OGVINg). It is not Bluetooth. I actually could not find a decent Bluetooth Remote. It does still use a 2.4ghz signal. It comes with a pre-paired USB dongle. Just plug it into a computer, and BOOM- the computer has a hardware keyboard device added.

Another nice feature is it has 5 programmable IR buttons at the bottom for backup in the event something isn't working.

There are many iterations of this remote. It seems to be a white labelled device and is just branded and repackaged by various companies. I did try several of them to try and find the best, but to be honest, they are all the same. I simply prefer the remote with the backlight versus without (although you do lose a button).

## Problem: Send keypresses to Home Assistant

Ok, so the next problem. The remote is plugged into my Kodi box (Manjaro) in the family room and my Home Assistant box is in the basement. How do I get keypresses from one to the other?

I have played with USBIP in the past and, I don't like it very much. In my experience (and I am far from an expert), it works great until it doesn't. It doesn't really have a way to catch and recover from errors. It just wasn't the sort of stable, low maintenance solution I wanted (but that may have been an error on my part).

After searching far and low, I came across the git:

[https://github.com/tjntomas/MI-Bluetooth-Remote-for-Home-Assistant](https://github.com/tjntomas/MI-Bluetooth-Remote-for-Home-Assistant).

It is a script for capturing a keyboard presses, and sending them to Home Assistsant so that each key_down and key_up event is converted to a Home Assistant event. From there, the hardware and "wiring" will be complete and it is a matter of using Home Assistant to create whatever series of automations for each key that your particular setup requires.

To use it, follow the instructions on the original repo. You need to make sure python is installed and that the python evtest module is installed.

The script wasn't perfect for me and so I made just a few changes. I wanted to specify the keyboard using a commandline argument since the remote I linked above creates three keyboard devices in linux. This is just easier that creating three seperate scripts. I also made sure that it would send the key code, along with the key name and type of press in the event data.

The following is a fork of the original git repo with the above mentioned and some other changes.

[https://github.com/jon6fingrs/Bluetooth-Remote-for-Home-Assistant/tree/main](https://github.com/jon6fingrs/Bluetooth-Remote-for-Home-Assistant/tree/main)

Here is my version of bt_remote_event.py:

```
"""
Script to listen to events from a bluetooth remote control and send
the events to Home Assistant.

Author: Tomas Jansson, https://github.com/tjntomas

"""

import json
import evdev # https://pypi.org/project/evdev/
import asyncio
import aiohttp
import logging
import os
import sys

# Set up logging and log levels.
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

BASE_API      = "http://IP_ADDRESS:8123/api/"  # URL to your HA instance.
DEV_INPUT     = "/dev/remote_"             
API_KEY       = "API_KEY_STRING"
HA_EVENT_NAME = "bt_remote" # Arbitrary name of the event that will get fired.
GRAB_DEVICE   = True # If set to True, the devices will be locked to this script and the system will not receive any events.

EVENT_PATH    = "events/" + HA_EVENT_NAME
BASE_API_URL  = BASE_API + EVENT_PATH
HEADERS       = {'content-type': 'application/json','Authorization': 'Bearer {}'.format(API_KEY)}
CMD           = "cmd"
CMD_TYPE      = "cmd_type"
CMD_NUM       = "cmd_num"

EVENT_LOG_TEMPLATE = "Fired event {} with event data{}"

async def run():
  device = evdev.InputDevice(DEV_INPUT + sys.argv[1])
  print("Using Bluetooth", str(device))
  
  if GRAB_DEVICE:
    device.grab()

  # Listen for events from the remote through the async-based evdev library.
  for event in device.read_loop():
    if event.type == evdev.ecodes.EV_KEY:   
      # Get the name of the remote key pressed, one of:
      # KEY_HOME    
      # KEY_F5      
      # KEY_COMPOSE   
      # KEY_BACK       
      # KEY_UP          
      # KEY_DOWN   
      # KEY_LEFT      
      # KEY_RIGHT    
      # KEY_ENTER      
      # KEY_VOLUMEUP   
      # KEY_VOLUMEDOWN 

      # The event string returned from the evdev library looks like this:
      # key event at 1609103448.769025, 28 (KEY_ENTER), down
      # We are only interested in the key name "KEY_ENTER" and the keypress type "down".
      cmd = str(evdev.categorize(event)).split(",")[1].split("(")[1].replace(")","")

      cmd_num = str(evdev.categorize(event)).split(",")[1].split("(")[0].replace(" ","")

      # Get the type of keypress, one of:
      # up
      # down
      # hold
      cmd_type = str(evdev.categorize(event)).split(",")[2].replace(" ","")

      # Compose the payload to send to HA when firing the event.
      payload = {CMD: cmd, CMD_TYPE: cmd_type, CMD_NUM: cmd_num}

      # Since the evdev library is async-based, we use async to send the event to HA.
      async with aiohttp.ClientSession() as session:
        await session.post(BASE_API_URL, data=json.dumps(payload), headers=HEADERS)
        logging.info(EVENT_LOG_TEMPLATE.format(HA_EVENT_NAME,payload))
        await session.close()

if __name__ == '__main__':
    # Create, start and gracefully shut down the asyncio event loop.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
```

So, first we need to figure out what our keyboards are with a tool called evtest. On Ubuntu, it can be installed with:

```bash
sudo apt install evtest
```

This will list the name and location of all connected input devices, like the following:

```yaml
No device specified, trying to scan all of /dev/input/event*
Not running as root, no devices may be available.
Available devices:
/dev/input/event0: Sleep Button
/dev/input/event1: Power Button
/dev/input/event10: Dell WMI hotkeys
/dev/input/event11: Video Bus
/dev/input/event12: DP-1
/dev/input/event13: HDA Intel PCH Headphone Mic
/dev/input/event14: HDA Intel PCH Front Line Out
/dev/input/event15: HDA Intel PCH HDMI/DP,pcm=3
/dev/input/event16: HDA Intel PCH HDMI/DP,pcm=7
/dev/input/event17: HDA Intel PCH HDMI/DP,pcm=8
/dev/input/event18: ydotoold virtual device
/dev/input/event2: Power Button
/dev/input/event3: flirc.tv flirc Keyboard
/dev/input/event4: 2.4G Composite Devic
/dev/input/event5: 2.4G Composite Devic Mouse
/dev/input/event6: 2.4G Composite Devic Consumer Control
/dev/input/event7: 2.4G Composite Devic System Control
/dev/input/event8: Pulse-Eight USB-CEC Adapter
/dev/input/event9: PC Speaker
Select the device event number [0-18]:
```

The "four" devices which represent my remote are:

```yaml
/dev/input/event4: 2.4G Composite Devic
/dev/input/event5: 2.4G Composite Devic Mouse
/dev/input/event6: 2.4G Composite Devic Consumer Control
/dev/input/event7: 2.4G Composite Devic System Control
```

The devices at 4, 6, and 7 represent the keyboards. The remote also can toggle into a gyroscopic mouse. This actually works out great for me since it is connected directly to my kodi box, so even though we will continue with the complicated setup that prevents the keyboards from directly interacting with the system, the mouse will still work if desired.

Anyway, if you try to access one of these devices, you will get:

```
Testing ... (interrupt to exit)
***********************************************
  This device is grabbed by another process.
  No events are available to evtest while the
  other grab is active.
  In most cases, this is caused by an X driver,
  try VT-switching and re-run evtest again.
  Run the following command to see processes with
  an open fd on this device
 "fuser -v /dev/input/event6"
***********************************************
```

Ok, so there are two things we have to accomplish.

1. <li>we need to deactivate the devices
2. <li>we need to give each device a stable name (eventX could change)

Luckily, there is one solution to accomplish both of these things- udev! I have added an example udev rule to my above linked git.

```
SUBSYSTEMS=="input", ATTRS{name}=="keyboard name from evtest", ENV{LIBINPUT_IGNORE_DEVICE}="1", SYMLINK+="remote_abc"
```

Each device will need its own file. Maybe it could be done with one, but I am not an expert, I did it with three. It is a one time procedure and then you forget about it. If you have a nice way to accomplish the same with one file, however, please let me know.

Anyway, my subsequent three files will look like:

```
SUBSYSTEMS=="input", ATTRS{name}=="2.4G Composite Devic Consumer Control", ENV{LIBINPUT_IGNORE_DEVICE}="1", SYMLINK+="remote_consumer"
```

```
SUBSYSTEMS=="input", ATTRS{name}=="2.4G Composite Devic System Control", ENV{LIBINPUT_IGNORE_DEVICE}="1", SYMLINK+="remote_system"
```

```
SUBSYSTEMS=="input", ATTRS{name}=="2.4G Composite Devic", ENV{LIBINPUT_IGNORE_DEVICE}="1", SYMLINK+="remote_keyboard"
```

For the symlink portion, keep "remote_" the same or else it will need to be changed in the script, but you can make the string after the underscore whatever you want. I chose remote_consumer, remote_system, and remote_keyboard just so I could remember which was which.

Ok so those three files can be named whatever (99-ignore-my device-whatever.rules) and they should be placed in /etc/udev/rules.d.

You can restart your system or enter the following command as root to activate the new rules:

```
udevadm control --reload-rules && udevadm trigger
```

Now, when you try and use evtest, it will be able to capture any of the three keyboards.

There are now a few modifications you have to make to the script so that it works for your setup.

1. <li>change the BASE_API to point to your instance's API endpoint
2. <li>from home assistant, create a long-lasting token and paste it in the API_KEY

So now, you could run the script to control one keyboard at a time and have each click send to home assistant by typing:

```bash
python3  /path_to_your_script/bt_remote_event.py %i
```

The argument is whatever keywords you decided to use after "remote_". For example "bt_remote_event.py keyboard" and it will run the script for the "keyboard" device.

One caveat to what we have done so far, even though the three keyboards are not being used by the system, the power button on the remote will still trigger whatever action your computer typically triggers when its power button is pressed. Therefore, I used the option in Gnome to disable the power button. This does have the consequence of even disabling the button on the PC itself, but that is not an issue for me. I am not sure if there is a way to only disable the power button only from the remote.

So now with the keyboard script running, you should be able to go into your home assistant instance, the developer's tools, events, and listen for the "bt_remote" events.

Hopefully you see your button presses and notice each press gives you two events:

```yaml
event_type: bt_remote
data:
  cmd: KEY_HOMEPAGE
  cmd_type: down
  cmd_num: "172"
origin: REMOTE
time_fired: "2024-02-11T19:53:40.964943+00:00"
context:
  id: sdfgsdfgsdfgsdfgsd
  parent_id: null
  user_id: sdfgsdfgsdfgsdfgsd
```

```yaml
event_type: bt_remote
data:
  cmd: KEY_HOMEPAGE
  cmd_type: up
  cmd_num: "172"
origin: REMOTE
time_fired: "2024-02-11T19:53:41.026000+00:00"
context:
  id: sdfgsdfgsdfgsdfgsdfgsdgsdf
  parent_id: null
  user_id: ddsfgsdfgsdfgsdfgsdfgsdfg
```

Each button will give you its down and then up events separately, and each even will give the key name, the button direction, and the raw key code. I added the key code because, for my setup, knowing the keycode was helpful for some subsequent actions.

Great so now that we know it works, how can we exit the running bt_remote_event script. We have to set up three scripts and make sure they start automatically. In the git repository, you should see btmon@.service. This will allow us to capture all three devices.

First, copy it to /etc/systemd/system/

```bash
sudo cp btmon@.service /etc/systemd/system/
```

Now you simply enable it three times for the three devices we named earlier:

```bash
sudo systemctl enable --now btmon@consumer.service
sudo systemctl enable --now btmon@system.service
sudo systemctl enable --now btmon@keyboard.service
```

Perfect! Now all those presses are headed straight for Home Assistant. The PC where the USB is physically plugged can be restarted and the scripts will pick up where its left off.

## Solution: Represent Keypresses in Home Assistant

Ok, so now Home Assistant is getting all those key press events, but so what? I wanted a way to have a single press and a long press. The long press shouldn't set off the single press, and the single press shouldn't be more delayed than absolutely necessary.

First, I made a trigger based binary sensor to more easily display the button presses and the necessary information:

{% raw %}
```
  - trigger:
      - platform: event
        event_type: bt_remote
        event_data:
          cmd_type: "down"
        id: "on"
      - platform: event
        event_type: bt_remote
        event_data:
          cmd_type: "up"
        id: "off"
    binary_sensor:
      - name: remote_button_press
        state: "{{ trigger.id }}"
        attributes:
          button: "{{ trigger.event.data.cmd }}"
          code: "{{ trigger.event.data.cmd_num }}"
          timestamp_up: >
            {% if trigger.id == 'off' %}
              {{ as_timestamp( trigger.event.time_fired)|float(default=0) }}
            {% else %}
              {{ this.attributes.timestamp_up|float(default=0) }}
            {% endif %}
          timestamp_down: >
            {% if trigger.id == 'on' %}
              {{ as_timestamp( trigger.event.time_fired)|float(default=0) }}
            {% else %}
              {{ this.attributes.timestamp_down|float(default=0) }}
            {% endif %}
          pressed_duration: >
            {% if trigger.id == 'on' %}
              0
            {% else %}
              {{ as_timestamp( trigger.event.time_fired)|float(default=0) - (this.attributes.timestamp_down)|float(default=0) }}
            {% endif %}
```
{% endraw %}

This creates a single binary_sensor. It is on during the time the button is pressed down, and off when it is released, so off the vast majority of the time. However, in its attributes, it has the current or last key and code pressed, but also the amount of time the key was pressed down in seconds (0 if the keys is pressed down at that moment). This has created a very easy system to make automations.

Now, as you probably guessed, to set everything up correctly, to identify each button and decide what you want it to do, it takes time. There also is not a one size fits all solution.

However, I will show examples of what I have done in case it can help anyone else.

## Respond to key presses

So I essentially have two automations. One for single presses and one for double presses.

The single press is actually triggered when our binary_sensor goes off, meaning that someone has just released a button. I have chosen a hold time of 0.5 seconds to represent a button hold. Anything shorter is a single press, and longer is a hold. Therefore, for this automation, I want to make sure we only act if the button was released before the hold automation is activated.

The following is my trigger and condition:

```yaml
alias: kodi remote
description: ""
trigger:
  - platform: state
    entity_id:
      - binary_sensor.remote_button_press
    from: "on"
    to: "off"
condition:
  - condition: numeric_state
    entity_id: binary_sensor.remote_long_press
    attribute: pressed_duration
    below: 0.5
```

Then I just have a giant choose between 30 actions. Again, it will be different for everyone, but I will show it before to highlight a couple things:

{% raw %}
```yaml
action:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_POWER' }}"
        sequence:
          - choose:
              - conditions:
                  - condition: state
                    entity_id: binary_sensor.vizio_tv_on
                    state: "on"
                sequence:
                  - service: script.all_off
                    data: {}
            default:
              - if:
                  - condition: state
                    entity_id: select.harmony_hub_2_activities
                    state: power_off
                then:
                  - service: select.select_option
                    target:
                      entity_id: select.harmony_hub_2_activities
                    data:
                      option: Watch Kodi
                else:
                  - service: remote.send_command
                    target:
                      entity_id: remote.family_room_broadlink
                    data:
                      num_repeats: 1
                      delay_secs: 0.4
                      hold_secs: 0
                      device: Vizio TV
                      command: PowerOn
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_VOLUMEUP' }}"
        sequence:
          - service: media_player.volume_up
            data: {}
            target:
              entity_id: media_player.family_room_tv
            enabled: false
          - service: script.increase_tv_volume_x1
            data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_VOLUMEDOWN' }}"
        sequence:
          - service: media_player.volume_down
            data: {}
            target:
              entity_id: media_player.family_room_tv
            enabled: false
          - service: script.decrease_tv_volume_x1
            data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_PLAYPAUSE' }}"
        sequence:
          - choose:
              - conditions:
                  - condition: state
                    entity_id: media_player.family_room_speaker
                    state: playing
                  - condition: not
                    conditions:
                      - condition: state
                        entity_id: media_player.family_room_tv
                        state:
                          - paused
                          - playing
                sequence:
                  - service: media_player.media_play_pause
                    data: {}
                    target:
                      entity_id: media_player.family_room_speaker
            default:
              - service: media_player.media_play_pause
                data: {}
                target:
                  entity_id: media_player.family_room_speaker
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_PREVIOUSSONG' }}"
        sequence:
          - choose:
              - conditions:
                  - condition: state
                    entity_id: media_player.family_room_speaker
                    state: playing
                  - condition: not
                    conditions:
                      - condition: state
                        entity_id: media_player.family_room_tv
                        state:
                          - paused
                          - playing
                sequence:
                  - service: media_player.media_previous_track
                    target:
                      entity_id: media_player.family_room_speaker
                    data: {}
            default:
              - service: media_player.media_previous_track
                target:
                  entity_id:
                    - media_player.family_room_tv
                  device_id: []
                  area_id: []
                data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_NEXTSONG' }}"
        sequence:
          - choose:
              - conditions:
                  - condition: state
                    entity_id: media_player.family_room_speaker
                    state: playing
                  - condition: not
                    conditions:
                      - condition: state
                        entity_id: media_player.family_room_tv
                        state:
                          - paused
                          - playing
                sequence:
                  - service: media_player.media_next_track
                    target:
                      entity_id: media_player.family_room_speaker
                    data: {}
            default:
              - service: media_player.media_next_track
                target:
                  entity_id:
                    - media_player.family_room_tv
                  device_id: []
                  area_id: []
                data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_CONFIG' }}"
        sequence:
          - choose:
              - conditions:
                  - condition: state
                    entity_id: select.harmony_hub_2_activities
                    state: Watch Kodi
                sequence:
                  - if:
                      - condition: state
                        entity_id: binary_sensor.vizio_tv_on
                        state: "off"
                    then:
                      - service: remote.send_command
                        target:
                          entity_id: remote.family_room_broadlink
                        data:
                          num_repeats: 1
                          delay_secs: 0.4
                          hold_secs: 0
                          device: Vizio TV
                          command: PowerOn
                      - delay:
                          hours: 0
                          minutes: 0
                          seconds: 0
                          milliseconds: 200
                      - service: remote.send_command
                        data:
                          device: Vizio Amp
                          command: InputOptical
                        target:
                          entity_id: remote.family_room_broadlink
                      - delay:
                          hours: 0
                          minutes: 0
                          seconds: 15
                          milliseconds: 0
                  - service: remote.send_command
                    target:
                      entity_id: remote.family_room_broadlink
                    data:
                      num_repeats: 1
                      delay_secs: 0.4
                      hold_secs: 0
                      device: Vizio TV
                      command: InputHdmi5
            default:
              - service: select.select_option
                target:
                  entity_id: select.harmony_hub_2_activities
                data:
                  option: Watch Kodi
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_MAIL' }}"
        sequence:
          - choose:
              - conditions:
                  - condition: state
                    entity_id: select.harmony_hub_2_activities
                    state: Watch Roku
                sequence:
                  - if:
                      - condition: state
                        entity_id: binary_sensor.vizio_tv_on
                        state: "off"
                    then:
                      - service: remote.send_command
                        target:
                          entity_id: remote.family_room_broadlink
                        data:
                          num_repeats: 1
                          delay_secs: 0.4
                          hold_secs: 0
                          device: Vizio TV
                          command: PowerOn
                      - delay:
                          hours: 0
                          minutes: 0
                          seconds: 0
                          milliseconds: 200
                      - service: remote.send_command
                        data:
                          device: Vizio Amp
                          command: InputOptical
                        target:
                          entity_id: remote.family_room_broadlink
                      - delay:
                          hours: 0
                          minutes: 0
                          seconds: 15
                          milliseconds: 0
                  - service: remote.send_command
                    target:
                      entity_id: remote.family_room_broadlink
                    data:
                      num_repeats: 1
                      delay_secs: 0.4
                      hold_secs: 0
                      device: Vizio TV
                      command: InputHdmi3
            default:
              - service: select.select_option
                target:
                  entity_id: select.harmony_hub_2_activities
                data:
                  option: Watch Roku
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_WWW' }}"
        sequence:
          - choose:
              - conditions:
                  - condition: state
                    entity_id: select.harmony_hub_2_activities
                    state: Watch Apple TV
                sequence:
                  - if:
                      - condition: state
                        entity_id: binary_sensor.vizio_tv_on
                        state: "off"
                    then:
                      - service: remote.send_command
                        target:
                          entity_id: remote.family_room_broadlink
                        data:
                          num_repeats: 1
                          delay_secs: 0.4
                          hold_secs: 0
                          device: Vizio TV
                          command: PowerOn
                      - delay:
                          hours: 0
                          minutes: 0
                          seconds: 0
                          milliseconds: 200
                      - service: remote.send_command
                        data:
                          device: Vizio Amp
                          command: InputOptical
                        target:
                          entity_id: remote.family_room_broadlink
                      - delay:
                          hours: 0
                          minutes: 0
                          seconds: 15
                          milliseconds: 0
                  - service: remote.send_command
                    target:
                      entity_id: remote.family_room_broadlink
                    data:
                      num_repeats: 1
                      delay_secs: 0.4
                      hold_secs: 0
                      device: Vizio TV
                      command: InputHdmi2
            default:
              - service: select.select_option
                target:
                  entity_id: select.harmony_hub_2_activities
                data:
                  option: Watch Apple TV
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_BACK' }}"
        sequence:
          - service: script.kodi_remote_back
            data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_UP' }}"
        sequence:
          - service: script.kodi_remote_up
            data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_DOWN' }}"
        sequence:
          - service: script.kodi_remote_down
            data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_LEFT' }}"
        sequence:
          - service: script.kodi_remote_left
            data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_RIGHT' }}"
        sequence:
          - service: script.kodi_remote_right
            data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_ENTER' }}"
        sequence:
          - service: script.kodi_remote_enter
            data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_HOMEPAGE' }}"
        sequence:
          - service: script.kodi_remote_home
            data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_FASTFORWARD' }}"
        sequence:
          - service: script.kodi_remote_fastforward
            data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_REWIND' }}"
        sequence:
          - service: script.kodi_remote_rewind
            data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_COMPOSE' }}"
        sequence:
          - service: script.kodi_remote_info
            data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_SEARCH' }}"
        sequence:
          - service: script.kodi_remote_search
            data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_ZOOMIN' }}"
        sequence:
          - service: script.kodi_remote_toggle_subtitles
            data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_ZOOMOUT' }}"
        sequence:
          - service: script.kodi_remote_audio_track
            data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_PAGEDOWN' }}"
        sequence:
          - service: script.kodi_remote_page_down
            data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_PAGEUP' }}"
        sequence:
          - service: script.kodi_remote_page_up
            data: {}
      - conditions:
          - condition: template
            value_template: "    {{ trigger.to_state.attributes.button.split(\"_\")[1]|length == 1 }}"
        sequence:
          - service: script.kodi_remote_letter
            data:
              key_pressed: |
                {{ trigger.to_state.attributes.button.split("_")[1]|lower }}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_BACKSPACE' }}"
        sequence:
          - service: script.kodi_remote_backspace
            data: {}
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_SPACE' }}"
        sequence:
          - service: script.kodi_remote_space
            data:
              key_pressed: 57
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_ESC' }}"
        sequence:
          - service: script.kodi_remote_gen_button
            data:
              key_pressed: 1
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_DOT' }}"
        sequence:
          - service: script.kodi_remote_gen_button
            data:
              key_pressed: 52
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.button == 'KEY_COMMA' }}"
        sequence:
          - service: script.kodi_remote_gen_button
            data:
              key_pressed: 51
```
{% endraw %}

The majority of my actions involve identifying the button by name by matching to one of the binary sensor's attributes. Then I usually call for a script just to make things a little cleaner. There is some logic in this spiderweb too. It really just depends and I'm sorry I can't make this cleaner.

I want to point out one of the options though. The back of the remote has a keyboard! Wouldn't it be great to use it? I really don't want to make an option for every letter in the alphabet. Instead, I made a single option to capture anytime the key name is a single letter:

{% raw %}
```
      - conditions:
          - condition: template
            value_template: "    {{ trigger.to_state.attributes.button.split(\"_\")[1]|length == 1 }}"
        sequence:
          - service: script.kodi_remote_letter
            data:
              key_pressed: |
                {{ trigger.to_state.attributes.button.split("_")[1]|lower }}
```
{% endraw %}

This will send the letter by itself to a special script I have which sends the letter wherever its needed depending on what device I am using. For single presses it is always a lower case letter, and as you will see, for long presses it is an upper case letter.

The long press automation is a little different. There are two situations to consider. One is a long press for something like volume. You want it to continue raising or lowering the volume as long as you are pressing it. Second is a long press which is simply a way to use the same button for a second action. In that case, we want it to perform a single action and then stop.

The automation is somewhat similarly triggered:

```yaml
platform: state
entity_id:
  - binary_sensor.remote_button_press
for:
  hours: 0
  minutes: 0
  seconds: 0.5
from: "off"
to: "on"
```

And my action block is in a repeat action and will continue to repeat, unless stopped, as long as the button remains "on" (pressed), and will stop when it is "off" released.

{% raw %}
```
repeat:
  sequence:
    - choose:
        - conditions:
            - condition: template
              value_template: "{{ trigger.to_state.attributes.button == 'KEY_VOLUMEUP' }}"
          sequence:
            - service: script.increase_tv_volume_x1
              data: {}
        - conditions:
            - condition: template
              value_template: "{{ trigger.to_state.attributes.button == 'KEY_VOLUMEDOWN' }}"
          sequence:
            - service: script.decrease_tv_volume_x1
              data: {}
        - conditions:
            - condition: template
              value_template: "{{ trigger.to_state.attributes.button == 'KEY_PLAYPAUSE' }}"
          sequence:
            - choose:
                - conditions:
                    - condition: state
                      entity_id: media_player.family_room_speaker
                      state: playing
                    - condition: not
                      conditions:
                        - condition: state
                          entity_id: media_player.family_room_tv
                          state:
                            - paused
                            - playing
                  sequence:
                    - service: media_player.media_stop
                      target:
                        entity_id:
                          - media_player.family_room_speaker
                      data: {}
              default:
                - service: script.kodi_remote_stop
                  data: {}
            - stop: ""
        - conditions:
            - condition: template
              value_template: "{{ trigger.to_state.attributes.button == 'KEY_UP' }}"
          sequence:
            - service: script.kodi_remote_up
              data: {}
        - conditions:
            - condition: template
              value_template: "{{ trigger.to_state.attributes.button == 'KEY_DOWN' }}"
          sequence:
            - service: script.kodi_remote_down
              data: {}
        - conditions:
            - condition: template
              value_template: "{{ trigger.to_state.attributes.button == 'KEY_LEFT' }}"
          sequence:
            - service: script.kodi_remote_left
              data: {}
        - conditions:
            - condition: template
              value_template: "{{ trigger.to_state.attributes.button == 'KEY_RIGHT' }}"
          sequence:
            - service: script.kodi_remote_right
              data: {}
        - conditions:
            - condition: template
              value_template: "{{ trigger.to_state.attributes.button == 'KEY_FASTFORWARD' }}"
          sequence:
            - service: script.kodi_remote_fastforward
              data: {}
        - conditions:
            - condition: template
              value_template: "{{ trigger.to_state.attributes.button == 'KEY_REWIND' }}"
          sequence:
            - service: script.kodi_remote_rewind
              data: {}
        - conditions:
            - condition: template
              value_template: "{{ trigger.to_state.attributes.button == 'KEY_ZOOMIN' }}"
          sequence:
            - service: script.kodi_remote_switch_subtitles
              data: {}
            - stop: ""
        - conditions:
            - condition: template
              value_template: "{{ trigger.to_state.attributes.button == 'KEY_ZOOMOUT' }}"
          sequence:
            - service: media_player.volume_mute
              target:
                entity_id: media_player.family_room_tv
              data:
                is_volume_muted: false
            - stop: ""
        - conditions:
            - condition: template
              value_template: "    {{ trigger.to_state.attributes.button.split(\"_\")[1]|length == 1 }}"
          sequence:
            - service: script.kodi_remote_letter
              data:
                key_pressed: |
                  {{ trigger.to_state.attributes.button.split("_")[1] }}
            - stop: ""
        - conditions:
            - condition: template
              value_template: "{{ trigger.to_state.attributes.button == 'KEY_COMPOSE' }}"
          sequence:
            - service: script.kodi_remote_menu
              data: {}
            - stop: ""
        - conditions:
            - condition: template
              value_template: "{{ trigger.to_state.attributes.button == 'KEY_BACKSPACE' }}"
          sequence:
            - choose:
                - conditions:
                    - condition: state
                      entity_id: sensor.active_player
                      state: media_player.apple_tv
                  sequence:
                    - service: shell_command.pyatv_root
                      data:
                        command: text_clear
                    - stop: ""
              default:
                - service: script.kodi_remote_gen_button
                  data:
                    key_pressed: 14
        - conditions:
            - condition: template
              value_template: "{{ trigger.to_state.attributes.button == 'KEY_PAGEDOWN' }}"
          sequence:
            - service: script.kodi_remote_page_down
              data: {}
        - conditions:
            - condition: template
              value_template: "{{ trigger.to_state.attributes.button == 'KEY_PAGEUP' }}"
          sequence:
            - service: script.kodi_remote_page_up
              data: {}
        - conditions:
            - condition: template
              value_template: "{{ trigger.to_state.attributes.button == 'KEY_WWW' }}"
          sequence:
            - choose:
                - conditions:
                    - condition: state
                      entity_id: select.harmony_hub_2_activities
                      state: Play Nintendo
                  sequence:
                    - if:
                        - condition: state
                          entity_id: binary_sensor.vizio_tv_on
                          state: "off"
                      then:
                        - service: remote.send_command
                          target:
                            entity_id: remote.family_room_broadlink
                          data:
                            num_repeats: 1
                            delay_secs: 0.4
                            hold_secs: 0
                            device: Vizio TV
                            command: PowerOn
                        - delay:
                            hours: 0
                            minutes: 0
                            seconds: 15
                            milliseconds: 0
                    - service: remote.send_command
                      target:
                        entity_id: remote.family_room_broadlink
                      data:
                        num_repeats: 1
                        delay_secs: 0.4
                        hold_secs: 0
                        device: Vizio TV
                        command: InputHdmi4
              default:
                - service: select.select_option
                  target:
                    entity_id: select.harmony_hub_2_activities
                  data:
                    option: Play Nintendo
            - stop: ""
        - conditions:
            - condition: template
              value_template: "{{ trigger.to_state.attributes.button == 'KEY_CONFIG' }}"
          sequence:
            - service: automation.trigger
              metadata: {}
              data:
                skip_condition: true
              target:
                entity_id: automation.turn_on_family_room_speaker
            - stop: ""
        - conditions:
            - condition: template
              value_template: "{{ trigger.to_state.attributes.button == 'KEY_ENTER' }}"
          sequence:
            - service: script.kodi_remote_return
              data: {}
            - stop: ""
    - delay:
        hours: 0
        minutes: 0
        seconds: 0
        milliseconds: 100
  while:
    - condition: state
      entity_id: binary_sensor.remote_long_press
      state: "on"
```
{% endraw %}

I added a short delay in the loop to make sure the button presses weren't being sent too quickly. You can see also that some of the actions are followed by a "stop" action when they are intended to run as a one-and-done action. Otherwise, the action will continue to repeat until the button is released.

## Summary

So, at this point, we have a 2.4ghz remote. The button presses are ignored by the host system and sent to home assistant as events. Home assistant then distinguished between long and short presses and enacts whatever action is necessary. Obviously, these buttons don't have to only act on my media center. The buttons can control anything in the house.

My setup basically allows the remote to work as intended based on what is playing on TV. That way, nobody ever has to switch inputs or profiles or whatever. It just works. I have noticed that my family gravitates towards it even instead of the harmony remotes. I have been very pleased with it so far which is why I wanted to share.

In the future, I can give examples of how I send the commands (including keyboard presses) seemlessly to kodi, roku, or apple tv. Those (especially apple tv) were tricky to figure out.

On a different kodi box, I have a separate remote set up and just have it send the keypresses back. That way, only the keys I want to modify are modified by home assistant while the remote buttons otherwise work for the kodi box just like they would without all this complicated work around.

I'm sure there are many more possibilities and would be excited to see what other people come up with.

## Links

Air Mouse Remote MX3 Pro with Backlit

Associate Link - [https://amzn.to/487vXMU](https://amzn.to/487vXMU)

Store Link - [https://www.amazon.com/gp/product/B08YRL56BT](https://www.amazon.com/gp/product/B08YRL56BT)

Rii MX3 Multifunction

Associate Link - https://amzn.to/3OGErnr

Store Link - https://www.amazon.com/gp/product/B01CL3ZXGO
