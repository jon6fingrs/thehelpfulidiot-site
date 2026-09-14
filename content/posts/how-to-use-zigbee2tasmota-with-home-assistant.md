+++
title = "How to Use Zigbee2Tasmota with Home Assistant"
date = 2021-10-02
updated = 2024-04-15
path = "how-to-use-zigbee2tasmota-with-home-assistant"
description = "To follow up my last post, integrating a newly flashed Tasmota Zigbee Coordinator with Home Assistant has a third option besides ZHA and Zigbee2MQTT; it…"

[taxonomies]
category = ["Smart Home"]
tag = ["home assistant", "mqtt", "zigbee", "zigbee2tasmota"]
+++

To follow up my last [post](/a-wired-sonoff-zigbee-alternative), integrating a newly flashed Tasmota Zigbee Coordinator with Home Assistant has a third option besides ZHA and Zigbee2MQTT; it can be used directly as a Zigbee Coordinator using its own amazing Tasmota Software.

The device itself uses a zigbee implementation called [Zigbee2Tasmota](https://tasmota.github.io/docs/Zigbee/), which is a full-fledged zigbee routing platform with the usual MQTT integration. Unfortunately, it is probably overlooked because its use is limited to the Tasmota console, but it may be an attractive option for some, especially for a potentially more reliable connection when relying on the WiFi radio of the Sonoff Zigbee Coordinator.

In this case, the Pros and Cons may have some subjectivity, but I will share why I was interested in using it, and the drawbacks associated with it.

First, as I stated in my first [post](/hello-world), when I began my self-hosting journey seriously by purchasing a machine with the intention of running ProxMox, I did what I'm sure everyone did. I put EVERYTHING I possibly could onto this single machine. That included Pihole (my dns server), Untangled (my firewall), Home Assistant, Mosquitto, EVERYTHING. I thought it was so cool to have a single machine running so many discrete tasks so elegantly through ProxMox, but I found that a host reboot was disastrous and caused a very long downtime in my house. Everything went down and the entire boot process could take up to 10 minutes. This had an extremely negative impact on my [WAF](https://en.wikipedia.org/wiki/Wife_acceptance_factor).

To solve this, I began splitting up my various services and really only have my plex server, my backup pihole, home assistant plus many other non-critical services on my ProxMox box now. I got a number of cheap Zotac mini-pcs from Amazon Warehouse and have begun using them to run baremetal services like OPNsense, zigbee/zwave radios, NVR, MQTT server, etc.

Back to my point, I did not initially enjoy turning my Tasmotized Zigbee Coordinator into a Home Assistant Zombie. When you integrate the Zigbee coordinator into ZHA, you lose all native Zigbee commands of the coordinator.

![](/wp-content/uploads/2021/10/image-1024x515.png)

In an effort to further decentralize my smart home infrastructure, I would prefer for the zigbee coordinator to maintain functioning even if my Home Assistant instance goes down. Having said that, the device now becomes dependent on a functioning MQTT server so that is certainly a trade-off. I personally keep my MQTT server running on my NAS so that it is always up. I also have a second instance of Home Assistant which meant that I could only integrate the coordinator natively with one instance, whereas when the connection is over MQTT, it can connect to an unlimited number of Home Assistant Servers. I also think an MQTT server is more stable than a WiFi serial over TCP connection. I subjectively and anecdotally noticed a quicker reaction time with Zigbee2Tasmota vs ZHA.

Second, based on my testing and internet research, it is really not possible to change the Zigbee channel from 11 when integrating the Zigbee Coordinator in ZHA. I have a Hue Hub and WiFi channels 1, 6, and 11 throughout my home and so for me, the ideal channel was 20. With Zigbee2Tasmota, this is a trivial command.

```
zbconfig {"Channel":<enter channel>}
```

Third, I purchased a number of cheap Sonoff and Aqara sensors without realizing the issues I would have when trying to pair them with standard Zigbee coordinators. I had many drop offs requiring a physical reset on the device when on ZHA, but the devices all just seemed to work with Zigbee2Tasmota. Now, this could be related to my second point and while on ZHA, there just may have been too much interference, but changing the channels of my other devices was not a viable option for me.

But it isn't all positive. There are certainly plenty of downsides with Zigbee2Tasmota.

First, all commands are done through the console except Zigbee Join and viewing the Zigbee Map, as you can see below. I suppose that negative depends on the individual, but it is certainly a nice option to have an easy to use GUI nicely integrated into Home Assistant. However, I should note once devices are added, they are listed on the main Tasmota page along with their current state, connection strength, battery level, etc.

![](/wp-content/uploads/2021/10/image-2.png)

It is definitely nice for a quick glance or to troubleshoot.

Second, along with all Zigbee network controls requiring commands through the Tasmota terminal, adding devices into Home Assistant also required manually configured MQTT entities and Template entities. Again, may or may not be a big deal. I will show some examples of my devices below. Honestly, once one device was written, it was trivial to copy and paste an additional device.

Third, while sensors worked quickly and flawlessly, lights were a bit of a different story. You can only send ONE command at a time. So changing the hue/color and brightness requires two separate commands. In Home Assistant, this required me to get a little creative with a template light ON TOP of the manually configured MQTT light. Also, the light updates in Home Assistant were a little slow since it required possibly sending multiple commands to the hub and then receiving a state message back to home assistant to update the entity. This probably wasn't a huge deal, but as you can imagine, my testing was artificial and involved a lot of stress testing which is probably beyond real world usage.

## Summary Comparison

| **Zigbee2Tasmota** | **ZHA** |
| --- | --- |
| Functions independently from Home Assistant | Nice and user-friendly GUI |
| Easily change Zigbee channel | Automatic device/entity creation after pairing |
| Good compatibility with nontraditional Zigbee protocols | Better light bulb compatibility and control |

## Helpful Zigbee2Tasmota Options

Ok, so you've read about Zigbee2Tasmota so far and you want to give it a try. There were a few global [Tasmota options](https://tasmota.github.io/docs/Commands/) I found very helpful in simplifying the administration of the network.

By default, every Zigbee device is communicated over MQTT using the same topic, `tele/%topic%/SENSOR`.

By setting SetOption89 to 1, each device is given their own topic, `tele/%topic%/<device>/SENSOR`. I found this much easier to keep the devices separated.

Each device is given a unique identifier when it joins the network, and that is used to initially populate the MQTT topic if you decided to make the change I suggested above, but there is fortunately a way to give friendly names to each device.

```
ZBName <device>,<new_friendly_name>
```

Once you do that, the device friendly name will display on the Tasmota home screen, and you can set SetOption112 to 1 so that the friendly name will be used in the MQTT topic instead of the unique identifier.

Ok, so now that we've done that, our Zigbee coordinator should be good to go. We have it connected to our MQTT broker and have tweaked the settings enough to hopefully add some devices.

## Example Home Assistant Entities

Here are some examples I made to control various devices. Like I said above, the MQTT topic for each device will now be  `tele/Zigbee/<friendly_device_name>/SENSOR`. I set my topic to zbbridge in Tasmota, so change yours accordingly along with the device names. I did my best to bold the device-specific names and options below.

{% raw %}
**Motion detector:**

```yaml
  - platform: mqtt
    name: <strong>master bath motion</strong>
    state_topic: "tele/<strong>zbbridge</strong>/<strong>master_bath_motion</strong>/SENSOR"
    value_template: "{{ value_json['ZbReceived']['<strong>master_bath_motion</strong>']['Occupancy'] }}"
    payload_on: 1
    payload_off: 0
    availability_topic: "tele/<strong>zbbridge</strong>/LWT"
    payload_available: "Online"
    payload_not_available: "Offline"
    qos: 0
    device_class: "motion"
```
{% endraw %}

{% raw %}
**Contact sensor:**

```yaml
  - platform: mqtt
    name: <strong>half bath door sensor</strong>
    state_topic: "tele/<strong>zbbridge</strong>/<strong>half_bath_door</strong>/SENSOR"
    value_template: "{{ value_json['ZbReceived']['<strong>half_bath_door</strong>']['ZoneStatusChange'] }}"
    payload_on: 1
    payload_off: 0
    availability_topic: "tele/<strong>zbbridge</strong>/LWT"
    payload_available: "Online"
    payload_not_available: "Offline"
    qos: 0
    device_class: "door"
```
{% endraw %}

{% raw %}
**Battery sensor:**

This was a little trickier. A battery percentage is not sent with each device update message. I added a template to the MQTT entity to say, "if message has updated value, use that, otherwise, keep old value." Without that addition, each time an updated message came without the specific value, the entity in Home Assistant became undefined.

```yaml
  - platform: mqtt
    name: <strong>half bath door battery</strong>
    state_topic: "tele/<strong>zbbridge</strong>/<strong>half_bath_door</strong>/SENSOR"
    value_template: >
      {% if value_json['ZbReceived']['<strong>half_bath_door</strong>']['BatteryPercentage'] > 0 %}
        {{ value_json['ZbReceived']['<strong>half_bath_door</strong>']['BatteryPercentage'] }}
      {% else %}
        {{ states(entity_id) }}
      {% endif %}
    availability_topic: "tele/<strong>zbbridge</strong>/LWT"
    payload_available: "Online"
    payload_not_available: "Offline"
    qos: 0
    device_class: "battery"
    expire_after: 86400
    unit_of_measurement: '%'
```
{% endraw %}

**Humidity and Temperature Sensors:**

The same is true for the Aqara Humidity and Temperature Sensor I use. Each message did not have ever variable and so it was important to only update the MQTT entity when the message had the necessary information. Also, to note, the temperature was reported in Celsius to Tasmota and so I had to add a freedom conversion to my MQTT entity for Fahrenheit.

{% raw %}
```yaml
  - platform: mqtt
    name: <strong>refrigerator temperature sensor</strong>
    state_topic: "tele/<strong>zbbridge</strong>/<strong>refrigerator_temperature_sensor</strong>/SENSOR"
    value_template: >
      {% if value_json['ZbReceived']['<strong>refrigerator_temperature_sensor</strong>']['Temperature'] > 0 %}
        {{ (value_json['ZbReceived']['<strong>refrigerator_temperature_sensor</strong>']['Temperature']|float + 1.8) + 32 }}
      {% else %}
        {{ states(entity_id) }}
      {% endif %}
    availability_topic: "tele/<strong>zbbridge</strong>/LWT"
    payload_available: "Online"
    payload_not_available: "Offline"
    qos: 0
    device_class: "temperature"
    expire_after: 86400
    unit_of_measurement: 'F'

  - platform: mqtt
    name: <strong>refrigerator humidity sensor</strong>
    state_topic: "tele/<strong>zbbridge</strong>/<strong>refrigerator_temperature_sensor</strong>/SENSOR"
    value_template: >
      {% if value_json['ZbReceived']['<strong>refrigerator_temperature_sensor</strong>']['Humidity'] > 0 %}
        {{ value_json['ZbReceived']['<strong>refrigerator_temperature_sensor</strong>']['Humidity'] }}
      {% else %}
        {{ states(entity_id) }}
      {% endif %}
    availability_topic: "tele/<strong>zbbridge</strong>/LWT"
    payload_available: "Online"
    payload_not_available: "Offline"
    qos: 0
    device_class: "humidity"
    expire_after: 86400
    unit_of_measurement: '%'
```
{% endraw %}

**Lights:**

Ok, so far things have  been relatively straightforward. Here is where they get tricky. I am in no way saying that this is the easiest or best way to accomplish light control. This is what I did which seemed to work. I did not attach any colored lights (thank god as I can only imagine that would add to the complication), but I did attach a number of white tunable lights.

Like I said above, the lights can only receive a single command at a time. Luckily, it is possible to group lights and send 1 command for multiple lights. To do so, use this following [command](https://tasmota.github.io/docs/Zigbee/#zigbee-groups):

```
ZbSend {"device":"IKEA_Light","Send":{"AddGroup":100}}
```

Replace the device with either the friendly name or unique identifier. The group number is a unique, arbitrary integer for each group. As far as I know, it is not possible to name the groups from within Tasmota and their status is not displayed on the front page.

First I will show how I handled a single light. It required both an mqtt entity and a template entity. The MQTT entity basically brought the device into home assistant, and the template entity made its control simpler by allowing me to change color temp and brightness at the same time by breaking down the single home assistant command into two separate MQTT commands. The MQTT device, for me, basically just sat there, hidden, and the Template light is how I interacted with the light.

Si**ngle Light:**

{% raw %}
```
   - platform: template
     lights:
       guest_bedroom_lamp_template:
         level_template: >
           {% if state_attr('light.guest_bedroom_lamp','brightness')|int >0 %}
             {{ state_attr('light.guest_bedroom_lamp','brightness') }}
           {% else %}
             0
           {% endif %}
         value_template: "{{ states('light.guest_bedroom_lamp') }}"
         temperature_template: >
           {% if state_attr('light.guest_bedroom_lamp','color_temp')|int >0 %}
             {{ state_attr('light.guest_bedroom_lamp','color_temp') }}
           {% else %}
             0
           {% endif %}
         turn_on:
           - service: light.turn_on
             data_template:
               entity_id: light.guest_bedroom_lamp
               brightness: "{{ (state_attr('switch.circadian_lighting_circadian_lighting','brightness')|float*(255/100)|float)|int }}"
           - service: light.turn_on
             data_template:
               entity_id: light.guest_bedroom_lamp
               color_temp: "{{ ((1000000)|float/state_attr('sensor.circadian_values','colortemp')|float)|int }}"
         turn_off:
           - service: light.turn_off
             data_template:
               entity_id: light.guest_bedroom_lamp
         set_level:
         - service: light.turn_on
           data_template:
             brightness: "{{ brightness|int }}"
             entity_id: light.guest_bedroom_lamp
         set_temperature:
         - service: script.change_brightness_and_color_temp
           data_template:
             light_ct: light.guest_bedroom_lamp
             brightness: "{% if brightness is defined %}{{ brightness|int }}{% else %}-1{% endif %}"
         - service: light.turn_on
           data_template:
             color_temp: "{{ color_temp|int }}"
             entity_id: light.guest_bedroom_lamp
         max_mireds_template: 370
         min_mireds_template: 153

   - platform: mqtt
     schema: template
     name: "Guest Bedroom Lamp"
     command_topic: "cmnd/zbbridge/ZbSend"
     state_topic: "tele/zbbridge/guest_room_lamp/SENSOR"
     command_on_template: >
       {"device": "guest_room_lamp","send":{
       {%- if brightness is defined -%}
       "Dimmer": {%- if brightness == 255 -%}254{%- else -%}{{ brightness }}{%- endif -%}
       {%- elif color_temp is defined -%}
       "CT": {{ color_temp }}
       {%- else -%}
       "Power": 1
       {%- endif -%}
       }}
     command_off_template: '{"device": "guest_room_lamp","send":{"Power":0}}'
     state_template: >
       {% if value_json['ZbReceived']['guest_room_lamp']['Power'] == 1 %}
         on
       {% elif value_json['ZbReceived']['guest_room_lamp']['Power'] == 0 %}
         off
       {% else  %}
         {{ states('light.guest_bedroom_lamp') }}
       {% endif %}
     brightness_template: >
       {% if value_json['ZbReceived']['guest_room_lamp']['Dimmer'] is defined %}
         {% if value_json['ZbReceived']['guest_room_lamp']['Dimmer'] == 255 %}
           254
         {% else %}
           {{ value_json['ZbReceived']['guest_room_lamp']['Dimmer'] }}
         {% endif %}
       {% else %}
         {{ state_attr('light.guest_bedroom_lamp','brightness') }}
       {% endif %} 
     color_temp_template: >
       {% if value_json['ZbReceived']['guest_room_lamp']['CT'] is defined %}
         {% if value_json['ZbReceived']['guest_room_lamp']['CT'] > 370 %}
           370
         {% elif value_json['ZbReceived']['guest_room_lamp']['CT'] < 153 %}
           153
         {% else %}
           {{ value_json['ZbReceived']['guest_room_lamp']['CT'] }}
         {% endif %}
       {% else %}
         {{ state_attr('light.guest_bedroom_lamp','color_temp') }}
       {% endif %} 
     availability_topic: "tele/zbbridge/LWT"
     payload_available: "Online"
     payload_not_available: "Offline"
     optimistic: true
     qos: 0
     max_mireds: 370
     min_mireds: 153
```
{% endraw %}

So basically, Guest Bedroom Lamp is the mqtt light, and Guest bedroom lamp template is (obviously), the template light. The only reason I made a template light was so I could change the temperature and brightness at the same time. For a template light, if the brightness variable is defined, the set_level script is called. However, if brightness and color_temp are both defined, the color_temp script is called. To deal with this, I made a separate script which basically turns the light on at the desired brightness first if brightness is defined and then sends the color_temp command. The script which you can see is called from my template script is:

{% raw %}
```yaml
alias: change brightness and color temp
sequence:
  - choose:
      - conditions:
          - condition: template
            value_template: '{{ brightness != -1 }}'
        sequence:
          - service: light.turn_on
            data_template:
              entity_id: '{{ light_ct }}'
              brightness: '{{ brightness }}'
    default: []
mode: parallel
max: 100
```
{% endraw %}

As you can see, my lights are also customized with the min and max color_temp and to use circadian lighting (which is an awesome HACS integration).

**Group Lights**

Controlling a group of lights was also a little tricky. I set up the same MQTT and template entities for each light, but the group light required its own template entity.

{% raw %}
```
  - platform: template
    lights:
      kids_bath_1:
        friendly_name: "kids_bath_1"
        level_template: >
          {% if state_attr('light.kids_bath_1_mqtt','brightness')|int >0 %}
            {{ state_attr('light.kids_bath_1_mqtt','brightness') }}
          {% else %}
            0
          {% endif %}
        value_template: "{{ states('light.kids_bath_1_mqtt') }}"
        temperature_template: >
          {% if state_attr('light.kids_bath_1_mqtt','color_temp')|int >0 %}
            {{ state_attr('light.kids_bath_1_mqtt','color_temp') }}
          {% else %}
            0
          {% endif %}
        turn_on:
          - service: light.turn_on
            data_template:
              entity_id: light.kids_bath_1_mqtt
              brightness: "{{ (state_attr('switch.circadian_lighting_circadian_lighting','brightness')|float*(255/100)|float)|int }}"
          - service: light.turn_on
            data_template:
              entity_id: light.kids_bath_1_mqtt
              color_temp: "{{ ((1000000)|float/state_attr('sensor.circadian_values','colortemp')|float)|int }}"
        turn_off:
          - service: light.turn_off
            data_template:
              entity_id: light.kids_bath_1_mqtt
        set_level:
        - service: light.turn_on
          data_template:
            brightness: "{{ brightness|int }}"
            entity_id: light.kids_bath_1_mqtt
        set_temperature:
        - service: script.change_brightness_and_color_temp
          data_template:
            light_ct: light.kids_bath_1_mqtt
            brightness: "{% if brightness is defined %}{{ brightness|int }}{% else %}-1{% endif %}"
        - service: light.turn_on
          data_template:
            color_temp: "{{ color_temp|int }}"
            entity_id: light.kids_bath_1_mqtt
        max_mireds_template: 370
        min_mireds_template: 153

  - platform: mqtt
    schema: template
    name: "kids bath 1 mqtt"
    command_topic: "cmnd/zbbridge/ZbSend"
    state_topic: "tele/zbbridge/kids_bath_1/SENSOR"
    command_on_template: >
      {"device": "kids_bath_1","send":{
      {%- if brightness is defined -%}
      "Dimmer": {%- if brightness == 255 -%}254{%- else -%}{{ brightness }}{%- endif -%}
      {%- elif color_temp is defined -%}
      "CT": {{ color_temp }}
      {%- else -%}
      "Power": 1
      {%- endif -%}
      }}
    command_off_template: '{"device": "kids_bath_1","send":{"Power":0}}'
    state_template: >
      {% if value_json['ZbReceived']['kids_bath_1']['Power'] == 0 %}
        off
      {% elif value_json['ZbReceived']['kids_bath_1']['Power'] == 1 %}
        on
      {% else  %}
        {{ states('light.kids_bath_1_mqtt') }}
      {% endif %}
    brightness_template: >
      {% if value_json['ZbReceived']['kids_bath_1']['Dimmer'] is defined %}
        {% if value_json['ZbReceived']['kids_bath_1']['Dimmer'] == 255 %}
          254
        {% else %}
          {{ value_json['ZbReceived']['kids_bath_1']['Dimmer'] }}
        {% endif %}
      {% else %}
        {{ state_attr('light.kids_bath_1_mqtt','brightness') }}
      {% endif %} 
    color_temp_template: >
      {% if value_json['ZbReceived']['kids_bath_1']['CT'] is defined %}
        {% if value_json['ZbReceived']['kids_bath_1']['CT'] > 370 %}
          370
        {% elif value_json['ZbReceived']['kids_bath_1']['CT'] < 153 %}
          153
        {% else %}
          {{ value_json['ZbReceived']['kids_bath_1']['CT'] }}
        {% endif %}
      {% else %}
        {{ state_attr('light.kids_bath_1_mqtt','color_temp') }}
      {% endif %} 
    availability_topic: "tele/zbbridge/LWT"
    payload_available: "Online"
    payload_not_available: "Offline"
    optimistic: false
    qos: 0
    max_mireds: 370
    min_mireds: 153
    
  - platform: template
    lights:
      kids_bath_2:
        friendly_name: "kids_bath_2"
        level_template: >
          {% if state_attr('light.kids_bath_2_mqtt','brightness')|int >0 %}
            {{ state_attr('light.kids_bath_2_mqtt','brightness') }}
          {% else %}
            0
          {% endif %}
        value_template: "{{ is_state('light.kids_bath_2_mqtt','on') }}"
        temperature_template: >
          {% if state_attr('light.kids_bath_2_mqtt','color_temp')|int >0 %}
            {{ state_attr('light.kids_bath_2_mqtt','color_temp') }}
          {% else %}
            0
          {% endif %}
        turn_on:
          - service: light.turn_on
            data_template:
              entity_id: light.kids_bath_2_mqtt
              brightness: "{{ (state_attr('switch.circadian_lighting_circadian_lighting','brightness')|float*(255/100)|float)|int }}"
          - service: light.turn_on
            data_template:
              entity_id: light.kids_bath_2_mqtt
              color_temp: "{{ ((1000000)|float/state_attr('sensor.circadian_values','colortemp')|float)|int }}"
        turn_off:
          - service: light.turn_off
            data_template:
              entity_id: light.kids_bath_2_mqtt
        set_level:
        - service: light.turn_on
          data_template:
            brightness: "{{ brightness|int }}"
            entity_id: light.kids_bath_2_mqtt
        set_temperature:
        - service: script.change_brightness_and_color_temp
          data_template:
            light_ct: light.kids_bath_2_mqtt
            brightness: "{% if brightness is defined %}{{ brightness|int }}{% else %}-1{% endif %}"
        - service: light.turn_on
          data_template:
            color_temp: "{{ color_temp|int }}"
            entity_id: light.kids_bath_2_mqtt
        max_mireds_template: 370
        min_mireds_template: 153

  - platform: mqtt
    schema: template
    name: "kids bath 2 mqtt"
    command_topic: "cmnd/zbbridge/ZbSend"
    state_topic: "tele/zbbridge/kids_bath_2/SENSOR"
    command_on_template: >
      {"device": "kids_bath_2","send":{
      {%- if brightness is defined -%}
      "Dimmer": {%- if brightness == 255 -%}254{%- else -%}{{ brightness }}{%- endif -%}
      {%- elif color_temp is defined -%}
      "CT": {{ color_temp }}
      {%- else -%}
      "Power": 1
      {%- endif -%}
      },"endpoint":1}
    command_off_template: '{"device": "kids_bath_2","send":{"Power":0}}'
    state_template: >
      {% if value_json['ZbReceived']['kids_bath_2']['Power'] == 0 %}
        off
      {% elif value_json['ZbReceived']['kids_bath_2']['Power'] == 1 %}
        on
      {% else  %}
        {{ states('light.kids_bath_2_mqtt') }}
      {% endif %}
    brightness_template: >
      {% if value_json['ZbReceived']['kids_bath_2']['Dimmer'] is defined %}
        {% if value_json['ZbReceived']['kids_bath_2']['Dimmer'] == 255 %}
          254
        {% else %}
          {{ value_json['ZbReceived']['kids_bath_2']['Dimmer'] }}
        {% endif %}
      {% else %}
        {{ state_attr('light.kids_bath_2_mqtt','brightness') }}
      {% endif %} 
    color_temp_template: >
      {% if value_json['ZbReceived']['kids_bath_2']['CT'] is defined %}
        {% if value_json['ZbReceived']['kids_bath_2']['CT'] > 370 %}
          370
        {% elif value_json['ZbReceived']['kids_bath_2']['CT'] < 153 %}
          153
        {% else %}
          {{ value_json['ZbReceived']['kids_bath_2']['CT'] }}
        {% endif %}
      {% else %}
        {{ state_attr('light.kids_bath_2_mqtt','color_temp') }}
      {% endif %} 
    availability_topic: "tele/zbbridge/LWT"
    payload_available: "Online"
    payload_not_available: "Offline"
    optimistic: false
    qos: 0
    max_mireds: 370
    min_mireds: 153
    
  - platform: template
    lights:
      kids_bath:
        friendly_name: "kids_bath"
        level_template: "{{ (state_attr('light.kids_bath_1_mqtt','brightness')|int + state_attr('light.kids_bath_2_mqtt','brightness')|int )/2 }}"
        value_template: "{{ is_state('light.kids_bath_2_mqtt','on') and is_state('light.kids_bath_1_mqtt','on') }}"
        temperature_template: "{{ (state_attr('light.kids_bath_1_mqtt','color_temp')|int + state_attr('light.kids_bath_2_mqtt','color_temp')|int )/2 }}"
        turn_on:
          - service: mqtt.publish
            data:
              topic: cmnd/zbbridge/ZbSend
              payload_template: >
                {"group": "101","send":{"Dimmer": {%- if brightness == 255 -%}254{%- else -%}{{ (state_attr('switch.circadian_lighting_circadian_lighting','brightness')|float*(255/100)|float)|int }}{%- endif -%}}}
          - service: mqtt.publish
            data:
              topic: cmnd/zbbridge/ZbSend
              payload_template: >
                {"group": "101","send":{"CT": {{ ((1000000)|float/state_attr('sensor.circadian_values','colortemp')|float)|int }} }}
        turn_off:
          - service: mqtt.publish
            data:
              topic: cmnd/zbbridge/ZbSend
              payload_template: '{"group": "101","send":{"Power":0}}'
        set_level:
          - service: mqtt.publish
            data:
              topic: cmnd/zbbridge/ZbSend
              payload_template: >
                {"group": "101","send":{"Dimmer": {%- if brightness == 255 -%}254{%- else -%}{{ brightness|int }}{%- endif -%}}}
        set_temperature:
          - service: script.change_brightness_and_color_temp_group
            data_template:
              group: 101
              brightness: "{% if brightness is defined %}{{ brightness|int }}{% else %}-1{% endif %}"
          - service: mqtt.publish
            data:
              topic: cmnd/zbbridge/ZbSend
              payload_template: >
                {"group": "101","send":{"CT": {{color_temp}} }}
        max_mireds_template: 370
        min_mireds_template: 153
```
{% endraw %}

This assumes an arbitrarily defined group number of 101 and uses a similar script to control both brightness and color_temp at the same time.

{% raw %}
```yaml
alias: change brightness and color temp group
sequence:
  - choose:
      - conditions:
          - condition: template
            value_template: '{{ brightness != -1 }}'
        sequence:
          - service: mqtt.publish
            data:
              topic: cmnd/zbbridge/ZbSend
              payload_template: >
                {"group": "{{ group }}","send":{"Dimmer": {%- if brightness ==
                255 -%}254{%- else -%}{{ brightness|int }}{%- endif -%}}}
    default: []
mode: parallel
max: 100
```
{% endraw %}

**Conclusion:**

As you can see, Zigbee2Tasmota is a fairly powerful platform, incredibly operating on a system with very limited resources. It is not for everyone, but could be enticing primarily for people with the Tasmotized Sonoff Zigbee Bridge. Connecting a WiFi device to Home Assistant through serial over TCP may not be the best or most stable setup. Instead allowing the coordinator to function independently and sharing the device information over MQTT might be more desirable.

On the other hand, if you have Tube's wired zigbee coordinator or the ZB-GW03 wired coordinator, you may be better off using ZHA for simplicity sake. Regarding Zigbee2MQTT, it should be noted that the EZSP radio found in the Sonoff Zigbee Adapter and the ZB-GW03 is not finalized and may be [buggy](https://github.com/Koenkk/zigbee-herdsman/issues/319).

**Links to adapters:**

**Sonoff Zigbee**

Affiliate link:

[SONOFF ZBBridge Smart Zigbee Bridge Hub, WI-FI & Zigbee Dual-protocol Supporting, APP Control and Multi-device Management](https://www.amazon.com/gp/product/B08BFT44QL/ref=as_li_tl?ie=UTF8&camp=1789&creative=9325&creativeASIN=B08BFT44QL&linkCode=as2&tag=thehelpfulidi-20&linkId=966fb5890513e368640eaf0f517c82f8)

Non-affiliate link:

[SONOFF ZBBridge Smart Zigbee Bridge Hub, WI-FI & Zigbee Dual-protocol Supporting, APP Control and Multi-device Management](https://www.amazon.com/ZBBridge-Dual-protocol-Supporting-Multi-device-Management/dp/B08BFT44QL/ref=sr_1_2?crid=2A7KXG2H6EAIN&dchild=1&keywords=sonoff+zigbee&qid=1633193142&sprefix=sonoff+zigbee%2Caps%2C167&sr=8-2)

[**Eachen ZB-GW03**](https://ewelink.eachen.cc/product/eachen-ewelink-zigbee-bridge-pro-zbbridge-pro/)

[**Tube's ZB Coordinator**](https://www.tubeszb.com/product/cc2652_coordinator/1?cp=true&sa=false&sbp=false&q=false&category_id=2)

Let me know if you have any questions. Thanks for reading!

Edit: changed instances of zigbee router to the correct terminology zigbee coordinator thanks to /u/chick_repellent.
