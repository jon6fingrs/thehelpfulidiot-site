+++
title = "My Home Assistant Wall Tablets, Part 3: Alerts, Swipes and a Thermostat That Knows About the Attic"
date = 2026-10-21
path = "home-assistant-wall-tablets-part-3-alerts-swipes-thermostat"
description = "The family room tablet learned to show what matters right now: one banner for everything that needs attention, a swipe to peek at what's hidden, and a thermostat card that also controls the attic AC and the basement heater."

[taxonomies]
category = ["Smart Home"]
tag = ["home assistant", "claude", "dashboard"]
+++

Almost everything that changed on my wall tablets since the last post happened on one of them: the Fire HD 10 in the family room. It's the tablet everyone walks past, so it's the one that has to be right at a glance.

The idea behind all of it is simple. **A tablet on the wall should show what matters right now, and everything else should be one swipe away.** The catch is that it also must never make it easy to do something by accident, like unlocking a door with a stray swipe.

Same deal as the last two posts: Claude wrote the code, I lived with it on the real tablet and reported what annoyed me, and every screenshot here is the real dashboard code running against a fake Home Assistant with made-up data.

![The family room tablet: weather and forecast, upcoming calendar events, four door locks, a thermostat dial with room temperatures and a flame and snowflake on two of them, a clock, light controls by floor, and the alley camera with a charging badge](/img/2026/10/dash3-family-room.jpg)
*The family room tablet today. Everything on it is made up, and the clock is stuck at 8:40 PM.*

## One Banner for Everything That Needs Attention

Back in the first post, the row of door locks had one trick: if the garage door was open, the whole row turned into a big red "Garage open, tap to close" button. So that became a general alerts banner in the same spot, filling the same row.

There are two colors:

- **Red** is something to deal with now: the garage is open (tap closes it, as before), a smoke or carbon monoxide alarm, a water leak (water heater, HVAC, washer), or the basement door open for 3 minutes.
- **Amber** is something to look at soon: the basement or garage door unlocked for 10 minutes (or at any time between 10 pm and 6 am, and tapping locks it), a lock that jammed, a UPS running on battery, the alley camera frozen, or the car charger reporting a fault.

With more than one alert at once, the most urgent shows first (red before amber) and a small counter says how many there are:

![The alerts banner in four states: a red garage-open alert reading 1 of 3, an amber basement door unlocked alert reading 2 of 3, an amber power out alert reading 3 of 3, and the normal lock row with one unlocked door](/img/2026/10/dash3-alerts.jpg)
*Swipe up for the next alert, down for the previous one. The last picture is the lock row, which is one tap on the dots away.*

- **Swipe up** for the next alert and **down** for the previous one. It stops at the ends instead of looping.
- **Tap the counter** ("1 of 3") to step forward. That one does wrap around.
- **Tap the banner** to run that alert's fix, like closing the garage or locking the basement door. A swipe never counts as a tap on the banner.
- **Peek at the locks.** While an alert is up, two small dots in the corner show you can look at the lock row instead. Swipe sideways or tap the dots and the locks show for 2 minutes, then the banner comes back. A new alert, or one clearing, brings it back right away.

When nothing is wrong, the lock row is exactly what it was before: no dots, nothing to swipe.

Each alert is just an entry in a list: a color, an icon, a function that returns the message (or nothing when the alert isn't active), and an optional fix to run when you tap it. The garage one looks like this:

```javascript
{ id: 'garage', level: 'red', icon: 'garage-open-variant',
  tap: { svc: 'cover.close_cover', e: 'cover.garage_door' },
  text: () => (Dash.st('cover.garage_door') === 'open' ? 'Garage open, tap to close' : null) }
```

### Taking Alerts Away

The first version alerted for every door: open for 3 minutes, unlocked for 10. The same day, it was obvious that was too much.

The front and back doors are in plain view of this tablet, and they're often standing open or unlocked while someone is home. The doors lock themselves anyway, and the lock row already shows their state. So the banner was just noise, and a banner that cries wolf teaches everyone to ignore the red.

All of the tuning is a small table, with two flags per door:

```javascript
const DOORS = [
  { name: 'Front door',    openAlert: false, unlockAlert: false },
  { name: 'Back door',     openAlert: false, unlockAlert: false },
  { name: 'Basement door', openAlert: true,  unlockAlert: true  },
  { name: 'Garage door',   openAlert: false, unlockAlert: true  },
];
```

(The real table also lists each door's sensor and lock. A jammed lock still alerts on any door.)

## Swipe to Peek

A lot of this tablet works by showing one thing automatically and hiding another that sits in the same spot. That's good until the hidden one is what you want.

The spot in the bottom corner is the clearest example. It shows the kids' faces while they're asleep and the alley camera the rest of the time, which meant that at night **the car was hidden**. I wanted to see the car at night. Now:

![The two faces card with green and red faces and "since" times under their names, above the alley camera card with a charging badge and a car name, each with two small dots in the corner](/img/2026/10/dash3-kids-alley.jpg)
*Top: the faces at night. Bottom: a swipe sideways shows the alley camera. (The names are made up.)*

- **Swipe sideways** to see the other card. Two small dots in the corner say which one is up. You can also tap the dots.
- It's a **peek**, not a setting. It goes back to the automatic choice by itself when the kids' state changes, or after 5 minutes without a touch. Nobody has to remember to put the tablet back.
- **Taps and long presses work as before.** A tap opens the camera, and a long press on a face still toggles that sound machine.
- While a sound machine is on, a small "since 8:12 PM" now sits under the name, so you can see when it came on.

The spot above it works the same way. It shows a map while someone is away and the calendar otherwise. Now each has a small button in its corner that shows the other for a while: a calendar button above the map's zoom buttons, and a map button next to the calendar's title. It comes back after 2 minutes without a touch, or as soon as someone leaves or comes home.

![The map card with two people's pins, a calendar button above the zoom buttons, and a name list with where each person is and since when](/img/2026/10/dash3-map.jpg)
*The map, with the calendar button at the top right. The locations are made up, and the map is real OpenStreetMap.*

### A Swipe Is Never a Tap

The part I care about most is invisible. On every spot that can be swiped, any drag of more than a short distance no longer counts as a tap when you let go. That means **a stray swipe can't lock a door or open the camera**. On a touch screen the finger lifting after a drag is the easiest way to press something you didn't mean to, and this closes that door.

## The Thermostat Learned About the Other Two

My house has one central air zone, run by a Nest. It also has a window AC in the attic and a plug-in heater in the basement. The thermostat card only knew about the Nest, so the attic and basement were just two temperatures in a row at the bottom.

Now they're part of the card:

- A little **flame** appears on the Basement tile while the heater is on.
- A little **snowflake** appears on the Attic tile while the AC's compressor is running. The window unit can't tell me what it's doing, so a smart plug on it measures power: about 100 watts is just the fan, and over 300 watts means the compressor is on.
- **Tap Basement or Attic** and that room's thermostat takes over the dial. It's named at the top ("Attic AC"), its tile gets an outline, and it has its own modes and setpoint. Tap it again, or tap Hallway, to go back. It also goes back after 2 minutes without a touch.

![The thermostat card showing the Attic AC: a cooling dial set to 74, mode buttons for cool and off, and four temperature tiles with a flame on the basement and a snowflake on the attic, which has a white outline](/img/2026/10/dash3-thermo-attic.jpg)
*The Attic tile tapped. The flame and snowflake are on the tiles even when the dial shows something else.*

One detail worth knowing: if you change a setpoint and it hasn't been sent yet when the dial flips back, it still goes to the thermostat it was made on. Adjusting the attic can never change the downstairs by accident.

Both are mostly automatic anyway. The attic cools to a set temperature when someone is up there and relaxes when it's empty, and the basement heats while someone is down there and turns off a while after they leave. So the dial is mostly for looking, and for the times you want to override.

## The Alley Card, and What Each Car Costs

You can see the alley camera in the corner of the full-page picture above. Its bar names the car the AI sees on the parking pad, and a small badge shows what the charger is doing. (How I trained that model and got it running in CodeProject.AI is in [its own post](/is-the-parking-spot-free-custom-ai-car-detection-home-assistant).)

The newest thing in that bar is a number: **what charging that car has cost this month, out of everything charged this month.** Here it is for each of my three cars, on the days each one is in the alley:

![Three alley camera bars: Mercedes, $28 of $61 this month; Hyundai, $9.50 of $61 this month; Subaru, $24 of $61 this month](/img/2026/10/dash3-car-costs.jpg)
*Each car's share of the month. All the numbers are made up. (Under $10 it shows cents.)*

It only shows a cost once that car has charged this month. Until then, it's just the car's name, like before.

### Where the Numbers Come From

This is why it matters that the model can tell my cars apart. Here's the whole chain:

- **The charger reports energy.** The charger says how much energy each charging session has used. A sensor adds up how much that number grew, so a new session starts counting from zero.
- **Each bit of energy is priced when it's used.** The price is my electric utility's own rate for the current bill (from the utility's integration in Home Assistant), once there's enough usage to trust it. Before that it falls back to a fixed default, and I can type in an exact price if I ever want to. Because it's priced at the moment, a price change never rewrites the past.
- **The camera picks the car.** When the charger gets plugged in, an automation looks at which car the parking pad AI is most confident about, and points a set of monthly meters at that car for the whole session. There are meters for each of the three cars, plus an "other" for anything else, and a total.
- **A wrong guess is fixable.** If it ever picks the wrong car, I can pick the right one in a selector, and the other selector follows.
- **A report on the 1st.** On the first of each month, Home Assistant emails a summary of last month's energy and cost for each car.

None of this needed anyone to do anything new. The car gets plugged in like always, and the meters follow.

## Smaller Things

- **A fix I took back.** The Wall Tablets menu page shows the family room page in a smaller window, and there the map zoomed out to most of the continent, because its margins didn't shrink along with everything else. Claude fixed it. Then we reverted it, because it could also have changed the zoom on the real tablet, and a nicer preview isn't worth changing what's on the wall. So the preview still zooms out too far.
- **Every change reaches the tablets by itself.** Each change re-stamps the page versions, and the tablets reload when nobody is touching them, like in the last post.

## About Those Screenshots (Once More)

The fake Home Assistant got a few more tricks for this post. It has a fake clock, so everything reads 8:40 PM, and fake people with made-up names and locations. The map tiles are real OpenStreetMap, with pins dropped in a random spot. The alley pictures are my own snapshots from the parking pad post, with a person blurred out. The charger numbers and costs are invented.

The swipes in the screenshots are simulated touches. It's the same events a finger would send, so the real swipe code runs, but it isn't a recording of anyone's hand.

## How It Went

The rule I gave Claude in the first post still holds: every way a person already uses the house must keep working, and changes may only add something to learn. Everything here is optional. You can ignore the dots, never swipe, and the tablet still does what it always did. The lock row is still there, one tap under the banner.

The change I'm happiest with is the one that removed alerts. A banner that goes off all the time is worse than no banner.

If you want the details on any of these cards, let me know in the comments.

Thanks for reading.
