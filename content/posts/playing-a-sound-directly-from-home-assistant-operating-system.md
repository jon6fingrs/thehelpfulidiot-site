+++
title = "Playing a sound directly from Home Assistant Operating System"
date = 2021-10-02
updated = 2024-04-15
path = "playing-a-sound-directly-from-home-assistant-operating-system"
description = "This may sound like it should've been a trivial task to accomplish but took me way longer to solve than I anticipated. As I said it my first post, I…"

[taxonomies]
category = ["Smart Home"]
tag = ["home assistant", "nest", "vlc"]
+++

This may sound like it should've been a trivial task to accomplish but took me way longer to solve than I anticipated. As I said it my [first post](/hello-world), I started my Home Automation journey with things like Nest. This included the (now [killedbygoogle](https://killedbygoogle.com/)) Nest Secure with Nest Detects. I did enjoy a very pleasing *DING *each time a door opened.  As time went on, I tried to distance myself as much as possible from the cloud.

Integrating them into Home Assistant was a major PITA though. I had to purchase the amazing [Starling Home Hub](https://www.starlinghome.io/), and use Homekit to create an automation where each door open and door close event would trigger an automation to control an MQTT switch through Homebridge which would then pass the information into Home Assistant. This worked pretty well for the most part, but once the batteries started to die in the Nest Detects, it seemed like the perfect opportunity to replace the door sensors.

I just purchased cheap Aqara Door Sensors and mounted them on my door. Obviously, the open/close information was passed far more easily into Home Assistant and I was able to simplify my work flow, but one thing I did miss was the *DING*.

<audio controls src="/wp-content/uploads/2021/10/chime.wav"></audio>

*DING*

I wanted something as simple as possible, and to me, the obvious solution was to connect a speaker to my Home Assistant box's 3.5mm jack and just play the sound. This was wayyyy more complicated than I expected.

Home Assistant's addon store has a very bizarre version of VLC. It seems like it is feature incomplete and has almost no options. I couldn't figure out how to use it.

![](/wp-content/uploads/2021/10/image-3-1024x384.png)
*VLC from Official Add-on Store*

Fortunately, there exists another version of VLC from a repository belonging to [rodripf](https://github.com/rodripf/hassio-local-vlc). Simply add the following address to the add-on repository list to install it:

[https://github.com/rodripf/hassio-local-vlc](https://github.com/rodripf/hassio-local-vlc)

Once installed, it can be configured for telnet access. This is what I found to be the easiest and most reliable way to play a sound. Set the following options as desired.

![](/wp-content/uploads/2021/10/image-4.png)

Once that is set up, it is necessary to add a [vlc_telnet](https://www.home-assistant.io/integrations/vlc_telnet/) entity which is done through yaml.

```yaml
media_player:
  - platform: vlc_telnet
    name: vlc
    host: 6872d8d8-local-vlc
    password: <secret password>
```

Edit the entry as you see fit, but the important thing is the host, which identifies the Home Assistant container, should be written as above.

After a reboot, "media_player.vlc" should exist and through this, you can play whatever sound you want, locally. Although, I had trouble playing the music unless I uploaded it to the "/share" directory.

Once you've uploaded your sound file to the /share directory, the following will play it:

```yaml
service: media_player.play_media
target:
  entity_id: media_player.vlc
data:
  media_content_id: /share/chime.wav
  media_content_type: music
```

It is important to make the media_content_type "music" as that is the only media type currently playable by the vlc_telnet integration.

You can go to a web gui of your VLC instance by going to your homeassistanturl:9892 and using the password you created in the addon settings page.

![](/wp-content/uploads/2021/10/image-5.png)

It's important to make sure your volume here is set to something reasonable. At first, I could not get any sound to play since the volume defaulted to 0.

You can also set the volume through Home Assistant as you would for any media player.

```yaml
service: media_player.volume_set
target:
  entity_id: media_player.vlc
data:
  volume_level: 0.35
```

Hope that helps. Seems like a fairly complex solution for a fairly simply problem, but like I said, this was the only way I could figure to do something like this from within Home Assistant Operating System (obviously other installations in standard operating systems can probably do this trivially).

The nice thing about this as opposed to the Nest solution, is that now I have control over when the door dings and when it doesn't. For example, my ding automation does not fire when my kids are asleep. Now I don't have to worry about waking them when I run out to the car.

Thanks for reading.

<audio controls src="/wp-content/uploads/2021/10/chime.wav"></audio>
