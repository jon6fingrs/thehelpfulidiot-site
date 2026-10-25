+++
title = "Tuning My Home Assistant Automations on Real Data Instead of Guessing"
date = 2026-10-25
path = "tuning-home-assistant-automations-on-real-data"
description = "My bathroom fan kept starting when nobody was showering, and my bedroom night mode kept switching itself off at 2 am. I stopped guessing, exported Home Assistant's history and replayed it against the rules, with Claude writing the replay scripts. Here's how that works and what the numbers said."

[taxonomies]
category = ["Smart Home"]
tag = ["home assistant", "claude", "automation", "sensors"]
+++

For years my way of tuning an automation was: change a number, wait a few days, get annoyed, change it again. It works, but slowly, and you only learn about a mistake when someone in the house is standing in a cold bathroom or a dark bedroom.

This month I did it differently on two things that had been bugging me, the fan in the master bathroom and the "night mode" for our bedroom. Before I changed anything, I exported what the sensors had *actually* done over the last ten days and ran the old rule and the new rule over the same events. Then I looked at the numbers.

It's not fancy. It's a pile of small Python scripts. But it changed how I make decisions about the house, and it's a good job for an AI to do, so this is how it went.

## The Fan That Started for No Reason

The master bath has a fan on the same circuit as the shower spotlight. I wanted it to start by itself when someone showers and keep running until the steam is gone, so nobody has to remember. My first attempt at a smarter fan leaned on one humidity sensor and started the fan when it rose.

It mostly worked. It also:

- started the fan when someone just washed their hands at the sink
- missed a couple of showers completely
- used up its "once an hour" limit on a false start, so the *actual* shower right after it got no fan at all (October 7, 8:42 pm)

That limit is there for a reason. The bathroom shares a wall with one of the kids' bedrooms, and I don't want a fan roaring next to a sound machine all night.

I could have kept nudging the threshold. Instead I asked Claude to help me look at the data first.

## Ten Days of Everything

Home Assistant keeps ten days of history by default. A small read-only script, `export_history.py`, asks for every state change of just the entities I name and writes them to a compressed file:

```bash
docker exec homeassistant python3 /config/scripts/export_history.py --days 10 \
    --out /config/history-export.json.gz \
    sensor.athom_humidity sensor.shower_zigbee_humidity light.master_bath ...
```

(My real command lists a lot more than that, and those are not my real entity names.) It changes nothing. It's just a copy of what happened.

Then comes the part I'd never have bothered with alone: a **replay**. A second script walks through the export on a clock it controls and says what a rule *would* have done at each moment. Run the old rule and the new rule over the same ten days and you can compare them without anybody having to take a shower on purpose.

![The loop: export ten days of history, replay the old and new rules over it, read the numbers, build the change only if the numbers say so, then live with it for a week and export again](/img/2026/10/tune-loop.png)
*The whole method. Everything above "Build it" is read-only.*

Claude wrote these scripts and I read what came out. Questions like "what happened with the shower on the 5th?" turn into a lookup instead of a guess, because the answer is already in the export.

## What the Two Sensors Actually Do

The export made something easy to see that I'd missed living with these sensors. There are two humidity sensors in the bathroom, and they behave very differently:

- **The Athom**, a plug-in sensor across the room, reports every few seconds. It sees a shower first. But it also drifts all day, and it rises at the sink too.
- **The Zigbee sensor** right above the shower reports every 30 seconds or so. And then, while the shower runs, it goes **quiet**. Five to ten minutes without a single report. When it comes back it reads 15 to 20 points higher.

![A sketch of one shower: the Athom curve rises first, the Zigbee sensor goes silent while the water runs and comes back 15 to 20 points higher, the fan turns on a minute or two in and off when the Zigbee reading has lost half its rise](/img/2026/10/tune-shower-sketch.png)
*A sketch of the shapes, not real data. I'd rather say that than make up a pretty curve.*

So the Zigbee sensor is useless for catching a shower early, but its *silence* is a great clue. The Athom starting to climb while the Zigbee sensor has gone quiet is a shower. The Athom climbing while the Zigbee sensor is still chatting along is someone at the sink.

The new rule is:

- **On:** the Athom rose 2 points within 5 minutes *and* the Zigbee sensor has been silent for 2 minutes. Or the Zigbee reading is 4 points above its 15-minute low, which catches the steam afterwards. Everything else that used to be required (main light on, 6 am to 10 pm, the kid's sound machine off, once an hour) is unchanged.
- **Off:** the Zigbee reading has lost half of its rise over the pre-shower level. That takes 15 to 60 minutes, about 40 typically.

"Half" isn't magic. It's where the recorded showers said the steam was effectively gone.

## What the Replay Said

I replayed September 30 to October 10: **84 bathroom visits, 30 of which had a shower.**

![Two bar charts: false starts with no shower went from 6 with one sensor to 1 with two; the slow 6:51 pm shower got its fan after 6.8 minutes with a 4-point rise and 1.3 minutes with a 2-point rise](/img/2026/10/tune-fan-results.png)
*Same events, old rule and new rule. The footnote matters: nothing is free.*

- Starts with nobody showering: **6 down to 1**.
- Showers started a median of **1 minute later** than before. That's the cost, and I had to decide I was fine with it.
- The one-sensor rule I started with needed a 4-point rise on the Athom. On a slow shower (6:51 pm on the 5th) that meant the fan came on **6.8 minutes** in. At 2 points it's 1.3 minutes, with no extra false starts on the showers I tried.

Two of the 84 visits were unclear: you can't tell from the sensors whether somebody showered. The older triggers start the fan for both of them either way, so they don't change the comparison.

Not everything came from the numbers. At one point the main light going off stopped turning the fan off during a "clearing" run. I only found out because I noticed the fan was still going, and no replay would have told me, because that's a habit, not a sensor. It's fixed: turning the light off ends the run again, because that's how the family has always used it.

## The Night Mode That Wouldn't Stay On

The second thing was "night mode" for our bedroom. It's what tells the house we're settled in for the night. The bedroom motion lights, for one, stay off while it's on. It doesn't literally mean asleep. Getting ready for bed and a bathroom trip count.

My first version used a Bayesian sensor, one of Home Assistant's built-in helpers. Each "clue" gets two numbers: how likely is this clue **if** it's night mode, and how likely is it **if** it isn't. The sensor multiplies them all together and turns on when the answer is over a threshold. Mine had five clues:

| Clue | Likely if night mode | Likely if not |
|---|---|---|
| Jon or Lauren is home | 0.98 | 0.47 |
| Presence sensor has been on 15+ minutes | 0.94 | 0.02 |
| Presence sensor has been off 10+ minutes | 0.02 | 0.72 |
| Lights were turned off by a person, someone seen in the last 3 minutes | 0.95 | 0.04 |
| After 9 pm or before 7:30 am | 0.85 | 0.20 |

I didn't pick those numbers. A second replay script, `replay_night_mode.py`, learns them from the export. Here's the part I like: it learns from every night **except the one it's testing**, and does that for each night in turn. A rule that's only ever tested on the data it learned from will always look great.

(One number is deliberately not what the data said: the time-of-day clue learned 0.98, but I capped it at 0.85, so a nap at 2 pm can still count.)

{% raw %}
```yaml
- platform: template
  value_template: >
    {% set p = states.binary_sensor.master_bedroom_presence %}
    {{ is_state('light.master_bedroom_master', 'off') and p is not none
       and not is_state('input_select.master_bedroom_lights_by', 'house_off')
       and (p.state == 'on' or (p.state == 'off' and now() - p.last_changed < timedelta(minutes=3))) }}
  prob_given_true: 0.95
  prob_given_false: 0.04
```
{% endraw %}

That's the "lights out with someone in the room" clue. Notice the three-minute grace period. It's there because the presence sensor drops out for seconds to minutes while we're asleep. On October 22 it did that six times, the longest for 2 minutes 35 seconds.

### Why It Flickered

The first version turned on within a minute of lights-out every night, which was great. But it **turned off whenever the presence sensor blinked or a light came on**. In the three nights I could compare (October 21 to 24), it went off **8 times** before the last of us was up, for anywhere from 8 seconds to 16 minutes. Then it came back on 3 times after the morning was over.

Which is when I stopped trying to make the clues smarter and wrote down what I actually want:

> On when the first person goes to bed, off when the last person wakes up or leaves.

That isn't a probability. It's a latch. The clues decide when it *turns on*; after that, only one thing can turn it off: the whole suite (bedroom plus attached bath) being empty for 5 minutes. And between 9 pm and 5 am, an empty suite doesn't count, it waits until 5. A third rule keeps it from restarting before 10 am once the morning has ended.

![A two-state diagram, off and on, with the rule for each change, and two boxes comparing the clues alone (8 early drops in 3 nights) with the latch (one on and one off every night, on between 9:01 and 10:29 pm, off between 6:17 and 9:09 am)](/img/2026/10/tune-night-latch.png)
*The rules fit on a card. The replay on the right is October 14 to 24.*

I replayed the latch over October 14 to 24: **one on and one off every night.** On between 9:01 and 10:29 pm, off between 6:17 and 9:09 am, always five minutes after the last of us left. It was wrong once in the daytime: a Wednesday evening when someone lay down in the bedroom with the door closed. It cleared itself when the suite emptied.

### The Bug Only the Replay Could Find

One more story. On October 23 night mode switched on at **7:21 am**. That's not bedtime. What happened: the bedroom's motion lights had turned themselves off after the room emptied, and "lights off with someone in the room" is one of the clues. Night mode started, and then it kept the lights from coming back on for me while I was in the bath.

The fix was to give the clue a memory of who turned the lights off (a small `input_select` set to `house_off` when the *house* did it) and ignore those. The reason I trust that fix is that I could replay the morning against it.

## Things I'd Warn You About

- **The exports are in UTC.** At one point a "midnight shower" turned out to be 8 pm. Every replay script now converts to New York time before printing anything.
- **Ten days isn't much.** Thirty showers and three comparable nights is a small sample, and I wouldn't call any of this science. The numbers learned for my bathroom and my bed would be wrong for yours. The method is the part that travels.
- **Some sensors have no history yet.** Our bedroom door sensor was only fixed on October 21. I'm leaving it out of night mode until it has a week of nights behind it.
- **A replay only tests what you thought to record.** If a sensor you didn't export matters, the replay is quietly wrong.

## Where Claude Fit

I've written before about [cleaning up my whole Home Assistant setup with Claude](/cleaning-up-six-years-of-home-assistant-with-claude), and this was the same arrangement on a smaller scale.

**Claude did:**

- wrote the export and replay scripts, and ran them against my data
- told me when a number didn't add up
- wrote each change with a note in the commit saying what the replay showed

**I did:**

- decided what "good" meant. A fan that starts a minute late is fine to me. A fan next to a sleeping kid's wall is not.
- knew things the data couldn't, like the dog sets off the bedroom sensor when I'm not there
- wrote the rule that fixed the flicker (the sentence in the quote above, and not a line of YAML)
- pasted the commands on the server. It never touches the house directly.

Honestly, the replay scripts are the part I'll keep. I used to be afraid to touch the fan because every change was a few days of "did that help?" Now I change the rule, run the replay, and know in a minute.

## If You Want to Try This

You don't need any of my scripts. The recipe is short:

1. Pick one automation that annoys you and list the entities it depends on.
2. Export their history for the last week or so. Home Assistant's history API will do it, or you can ask an AI to write the script (`end_time` is required, or you only get one day).
3. Write the rule you have now as a plain Python function of "what the sensors said at this moment." Replay the export through it and count what it did.
4. Do the same for the rule you *want*. Compare. If the new one only wins on paper, you'll see that too.
5. Keep the script. It becomes the test you run next time.

My scripts live in the same repo as my config. If a future automation breaks, the replay is the first place I'll look.
