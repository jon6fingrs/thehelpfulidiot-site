+++
title = "Is the Parking Spot Free? Training My Own AI to Recognize My Cars"
date = 2026-10-20
path = "is-the-parking-spot-free-custom-ai-car-detection-home-assistant"
description = "I trained a small YOLOv5 model on photos from my alley camera so Home Assistant can tell my three cars apart, and so my phone can say whether the parking spot behind the house is free before I get home."

[taxonomies]
category = ["Smart Home"]
tag = ["home assistant", "ai", "camera", "codeproject.ai", "yolo"]
+++

I live in a row home. There's no driveway in front, just a single parking pad behind the house, off the alley. If a car is already on it, the next one has to find a spot on the street. So the question I ask the most when I'm driving home is: **is the spot free?**

Now my phone answers it before I get there. As I pull up to the house, I get a voice message saying whether parking is available, and a notification with a picture from the alley camera so I can check it myself. In Apple CarPlay the parking pad even shows up as a garage door: open means free, closed means a car is on it.

Under it all is a small AI model I trained to recognize my three cars. By my own estimate it's right more than 95% of the time.

![The alley at night in infrared: a dark SUV on the parking pad with the charger cable on the ground beside it](/img/2026/10/parking-pad-night.jpg)
*The Hyundai on the pad at night, in infrared. This is the real picture the model works from.*

## Why a Generic Model Wasn't Enough

I run [CodeProject.AI](https://www.codeproject.com/Articles/5322557/CodeProject-AI-Server-AI-the-easy-way) in Docker on my home server. It's a free object detection server that runs on your own hardware, and Home Assistant can send it pictures over a simple HTTP call. Out of the box it knows what a "car" is. I started there, using the ready-made `ipcam-combined` model that comes with it.

That did not go well. My alley camera is a wide-angle view looking down on the pad from above, so the cars aren't seen from the side the way they are in most training photos. The generic model often found nothing at all. It also couldn't do the one thing I actually cared about, which was to tell *my* cars from anyone else's.

I only wanted one question answered: *which of my three cars is on the pad, if any?* That's three possible answers, from one camera that never moves. (I set all of this up about two years ago, with a lot of help from ChatGPT on the training side.)

Two things turned it around:

1. **Cropping.** When I cut the picture down to just the area where the car parks, the model suddenly saw cars it had missed in the full picture. The car only takes up part of the frame, and a small object in a large picture is hard to detect.
2. **Training my own model on my three cars.** Not "car", but `hyundai`, `mercedes` and `subaru`.

## Step 1: Collect Pictures

The camera is a Ring camera. [`ring-mqtt`](https://github.com/tsightler/ring-mqtt) gives Home Assistant a fresh snapshot about every 30 seconds, and an automation saves it over the same file each time. That one file is the input for everything else.

To build a training set, I wrote a small Python script and ran it from cron every few minutes. It takes the current snapshot, shrinks it to fit in 640×640 pixels (the size the model trains on), pads it with black bars so the shape isn't distorted, and saves it under the next free number: `0001.jpg`, `0002.jpg` and so on. That gathers pictures in different light and weather, including night in infrared.

```python
from PIL import Image
import os

source_image = "/path/to/www/ring-snapshot/alley-snapshot.jpg"
destination_dir = "/home/me/training-images/"
os.makedirs(destination_dir, exist_ok=True)
target_size = 640

def resize_and_pad(image_path, output_path, size=640):
    """Resize an image to fit within a square with padding, preserving aspect ratio."""
    try:
        img = Image.open(image_path)
        img.thumbnail((size, size), Image.LANCZOS)
        padded_img = Image.new("RGB", (size, size), (0, 0, 0))
        padded_img.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
        padded_img.save(output_path)
        print(f"Processed and saved: {output_path}")
    except Exception as e:
        print(f"Error processing {image_path}: {e}")

def copy_and_save_sequentially():
    # Find the highest existing file number and use the next one
    existing_files = [f for f in os.listdir(destination_dir) if f.endswith(".jpg")]
    if existing_files:
        latest_num = max([int(f.split('.')[0]) for f in existing_files])
        new_num = latest_num + 1
    else:
        new_num = 1
    new_image_path = os.path.join(destination_dir, f"{new_num:04d}.jpg")
    if os.path.exists(source_image):
        resize_and_pad(source_image, new_image_path, target_size)
    else:
        print(f"No image found at {source_image}")

copy_and_save_sequentially()
```

I used almost the same function once more to standardize the pictures I had already collected by hand: it loops over a whole folder and writes the 640×640 padded copies into another one.

I only let it run for a few days, then commented the cron line out. Because the lighting changes slowly and the cars sit still, a few days already covered a lot.

One thing I worried about at first was overfitting: a model that has memorized its pictures instead of learning what a car looks like. For a general-purpose model that's a real problem. For mine it turned out to help. The camera never moves, there are only three answers, and the cars park in nearly the same places every time, so a model that knows exactly what *these* cars look like from *this* spot is just what I want. It's a very narrow job, and I wouldn't claim the same thing works for a camera that sees strangers' cars.

Even so, hundreds of near-identical pictures of one parked car don't teach much. Variety (different light, weather, parking positions, and the empty pad) is what helps.

![The alley in daylight: a dark SUV with bikes on the roof parked on the pad](/img/2026/10/parking-pad-day.jpg)
*The Mercedes in daylight, with bikes on the roof.*

![A car parked toward the right edge of the pad at night, the charger cable lying across the ground](/img/2026/10/parking-pad-charging.jpg)
*The Subaru parked toward one side at night, charging. It still needs to count as "taken".*

![The empty parking pad at night in infrared](/img/2026/10/parking-pad-empty.jpg)
*The empty pad at night.*

## Step 2: Label Them

A model learns from examples where a person has drawn a box around each car and said which car it is. I used [LabelImg](https://github.com/HumanSignal/labelImg), a free desktop tool: open a picture, drag a box around the car, type its name, next picture. It saves a small text file with each picture in YOLO format (one line per box: the class, then the box's position and size).

The first training set was small:

| Car | Pictures |
|---|---:|
| Hyundai | 77 |
| Mercedes | 87 |
| Subaru | 98 |
| **Total** | **262** |

I named the files after the car (`hyundai-0001.jpg`) so I could keep track of which was which. LabelImg also keeps a `classes.txt`, one name per line, and the order is the number each class gets in the label files:

```text
hyundai
mercedes
subaru
```

Along the way I also tried different framings of the same scene. An early test folder of mine has files like `hyundai-full-1.jpg`, `hyundai-cropped-1.jpg`, `hyundai-left-1.jpg` and `hyundai-right-1.jpg`: the whole frame, a crop, and the left or right half. I also went back and labeled the images a second time after resizing them to 640×640, because the boxes from the original size were no longer in the right place.

Labeling didn't take long, and that's the nice thing about a fixed camera. Once a car is parked it doesn't move, so a whole run of pictures has the same car in the same place, with only the light and shadows changing. I labeled one picture by hand, then automated copying that box to the rest of the pictures of that parked car.

## Step 3: Train

I used [YOLOv5](https://github.com/ultralytics/yolov5), the version CodeProject.AI's detector understands, and started from the small pretrained `yolov5s.pt` model instead of from scratch. It already knows what edges, wheels and windows look like, so my 262 pictures only have to teach it *my* cars.

The training machine is an old laptop (an Intel i7-8750H and a GTX 1060 with 6 GB of memory), so the settings are modest. This was the command:

```bash
python3 train.py \
  --img 640 \
  --batch 1 \
  --epochs 5000 \
  --patience 300 \
  --data dataset.yaml \
  --weights yolov5s.pt \
  --cache \
  --hyp hyp.scratch-low.yaml \
  --device 0
```

A few of those choices:

- `--batch 1`: all the 6 GB of video memory would allow.
- `--epochs 5000 --patience 300`: a ceiling, not a target. Training stops by itself when the score hasn't improved for 300 rounds.
- `hyp.scratch-low.yaml`: the settings that control how much training pictures get randomly changed. I turned the changes that don't make sense for a fixed camera down to zero: no flipping, no rotating, no zooming, no mosaic. The camera never moves, so the cars always appear from the same angle, and a flipped car is a view I'll never see.

The dataset file is only a few lines:

```yaml
train: /path/to/dataset/images/train
val: /path/to/dataset/images/train

nc: 3
names: ['hyundai', 'mercedes', 'subaru']
```

Look at the second line. **The validation folder is the same as the training folder.** That means the model was "tested" on pictures it had already studied, so the scores below say how well it learned the training set, not how well it will do on new pictures. I'll come back to this.

The first full run stopped on its own after about 5 hours. It found its best result at epoch 69, then went 300 rounds without beating it:

| | Precision | Recall |
|---|---:|---:|
| All cars | 0.912 | 0.910 |
| Hyundai | 0.942 | 0.961 |
| Mercedes | 0.938 | 0.863 |
| Subaru | 0.855 | 0.906 |

(Precision is how often a "Subaru" call was right. Recall is how many of the real Subarus it found.)

I should be honest about one thing: I trained several versions along the way and didn't keep good notes. The folder on my server holds a few of them (`custom-model-276.pt`, `custom-model-370.pt` and so on), and I can't tell you for certain which training run the live model came from. So treat the numbers above as one early run, not a measurement of the model running today. What I can say is that the method is the same, and the live model has done the job well for a long time.

## Step 4: Put the Model in CodeProject.AI

The trained model has to go where CodeProject.AI looks for custom ones. Its YOLOv5 detector looks in a `custom-models` folder inside its module. Any `.pt` file you drop in becomes its own endpoint, named after the file. My file is `custom-model.pt`, so my endpoint is `/v1/vision/custom/custom-model`.

Because it runs in Docker, I mount the file into the container in my compose file:

```yaml
services:
  ai-server:
    container_name: codeproject-ai
    image: codeproject/ai-server
    restart: unless-stopped
    ports:
      - 32168:32168
    volumes:
      - ./ai:/etc/codeproject/ai
      - ./modules:/app/modules
      - ./custom-model.pt:/app/preinstalled-modules/ObjectDetectionYOLOv5-6.2/custom-models/custom-model.pt
```

After a restart, the model shows up. You can test it from a terminal by sending any picture with `curl`:

```bash
curl -s -X POST -F "image=@alley.jpg" -F "min_confidence=0.2" \
  http://AI_SERVER_IP:32168/v1/vision/custom/custom-model | jq
```

The answer comes back as JSON, with a `message` (like "Found hyundai"), a `count`, and a list of `predictions`, each with a label, a confidence and a box.

I trained on the GPU, but I run detection on the CPU, and it's fast enough: one picture every 30 seconds is easy work. As far as I remember, the trained weights went in exactly as they came out of training, with no conversion.

Home Assistant keeps the server's reply as attributes on the sensor, so you can see the timing for yourself. With an empty pad, mine currently says:

```yaml
count: 0
predictions: []
inferenceDevice: CPU
inferenceMs: 97
analysisRoundTripMs: 105
success: true
moduleName: Object Detection (YOLOv5 6.2)
command: custom
```

That's about a tenth of a second to look at the picture, on a CPU, including the round trip.

One small thing that bit me: from inside the Home Assistant container, the AI server's container name would not resolve reliably, so my config uses the Docker network's gateway address instead. That's a private address and could change if the network is recreated.

## Step 5: Home Assistant Asks the Model

A [command-line sensor](https://www.home-assistant.io/integrations/command_line/) does the work. It crops the latest snapshot, sends it to the model, and keeps the answer as its state.

{% raw %}
```yaml
command_line:
  - sensor:
      name: alley_car_detection
      command: >
        python3 /config/crop_image.py /config/www/ring-snapshot/alley-snapshot.jpg |
        curl --silent -X POST -F "image=@-;type=image/jpeg" -F "min_confidence=0.2"
        http://AI_SERVER_IP:32168/v1/vision/custom/custom-model
      value_template: >
        {% set response = value | from_json %}
        {{ response.message if response.message is defined else 'No message' }}
      scan_interval: 300
      json_attributes:
        - count
        - predictions
        - inferenceMs
```
{% endraw %}

The crop is a few lines of Python with Pillow. It cuts the bottom two-thirds of the 640×360 snapshot and doubles its size:

```python
import sys
from PIL import Image

img = Image.open(sys.argv[1])
cropped = img.crop((0, 120, 640, 360))
scaled = cropped.resize((cropped.width * 2, cropped.height * 2), Image.LANCZOS)
scaled.save(sys.stdout.buffer, format="JPEG")
```

Writing to `stdout` lets the whole thing be one pipe straight into `curl`, with no temporary files.

![The night picture cropped to the lower part of the frame and enlarged to twice its size, so the car fills most of it](/img/2026/10/parking-pad-crop.jpg)
*What the model actually receives. The far end of the alley, including the neighbor's car, is cut off, and the car is big.*

I'll be honest again: I'm not sure how much the crop still matters. I found that cropping helped *before* I had my own model, and I labeled my training pictures as whole frames. The crop stayed in the pipeline because it works, and I never took it out. Sending the uncropped picture to the model and comparing the results would be an easy experiment, but I haven't done it.

The sensor refreshes in two ways. One is a slow timer every 5 minutes, as a safety net. The faster way is an automation that runs every time a new snapshot arrives: it saves the picture, waits two seconds for the file to finish writing, then tells the sensor to update. So the answer is usually about 30 seconds old at most.

## Step 6: Don't Trust a Single Frame

A model answering every 30 seconds will sometimes be wrong for one frame: a headlight glare, a person walking past, a shadow. If a single wrong answer opened the "garage door" in CarPlay, nobody would trust it. So the sensor's answer feeds a second sensor that has to be sure:

{% raw %}
```yaml
template:
  - trigger:
      - trigger: template
        value_template: >-
          {{ 'mercedes' in states('sensor.alley_car_detection')
             or 'hyundai' in states('sensor.alley_car_detection')
             or 'subaru' in states('sensor.alley_car_detection') }}
        for: "00:00:34"
        id: "on"
      - trigger: template
        value_template: >-
          {{ not ('mercedes' in states('sensor.alley_car_detection')
             or 'hyundai' in states('sensor.alley_car_detection')
             or 'subaru' in states('sensor.alley_car_detection')) }}
        for: "00:01:04"
        id: "off"
    binary_sensor:
      - name: alley_car_occupancy
        state: "{{ trigger.id }}"
        device_class: occupancy
```
{% endraw %}

- It switches to **occupied** after one of my three cars has been seen for 34 seconds in a row.
- It switches to **free** only after 64 seconds with none.

A final sensor follows that one, and it also turns on if the car charger is plugged in. That's what everything else in the house reads.

I don't remember exactly how I picked those two numbers. They work out to roughly one and two snapshots, and they've held up, so I've left them alone. It's slower to say "free" than "taken", which suits this job.

## Step 7: Tell the Phone

This is the part I actually use.

**The garage door.** I made a template cover called "Alley Garage Door" whose state is simply "the pad is free". Home Assistant's HomeKit bridge shows it to Apple Home, and Apple's CarPlay shows garage doors, so the parking pad appears on the car's screen as a door: open means a free spot, closed means taken. Tapping it sends the notification below. Nothing is opened or closed, since there's no door.

**The notification.** A script sends my phone a message: "Parking Behind House is **AVAILABLE**" or "**NOT AVAILABLE**", with the latest snapshot attached. The picture matters, because it lets you check the AI at a glance. The script then waits ten minutes before it will run again, so tapping repeatedly can't spam anyone.

**The voice alert.** This is an iPhone Shortcuts automation that runs by itself when my phone arrives home. It runs a shortcut called "Alley Parking" (and another, unrelated one that sends my location):

![The arrival automation in Shortcuts: it runs the Alley Parking shortcut, then a second shortcut that sends my location](/img/2026/10/shortcut-arrive.jpg)
*The arrival automation, cropped to its two steps.*

"Alley Parking" only does anything when I'm driving. I have a "driving" flag, `jon_driving`, and a pair of small shortcuts that flip it: "Jon Driving On" and "Jon Driving Off". Shortcuts automations run them when the phone connects to or disconnects from CarPlay or the car's Bluetooth. "On" checks the flag and, if it isn't already on, sets it and also tells Home Assistant to turn on a matching input boolean (with the Home Assistant app's **Perform action**). "Off" does the reverse.

![The Jon Driving On shortcut: if the flag is not already on, it sets the jon_driving variable to On, builds a small dictionary with the input boolean's entity ID, and performs the Turn on input boolean action on the Home server](/img/2026/10/shortcut-driving-on.jpg)
*The "Driving On" shortcut. The first steps, not shown, read the flag and check it.*

The first thing "Alley Parking" does is read my flag. If it's on, it raises the volume with another small shortcut ("Vol Boost"), asks Home Assistant for the state of the parking pad sensor using the Home Assistant app's **Render template** action, and speaks the answer: "Alley Parking Is AVAILABLE." or "Alley Parking Is NOT AVAILABLE." If I'm walking up instead, it stays quiet.

![The top of the Alley Parking shortcut: it reads the jon_driving variable, runs Vol Boost, renders a Home Assistant template, and speaks AVAILABLE if the result is off](/img/2026/10/shortcut-alley-parking-1.jpg)

![The rest of the Alley Parking shortcut: the NOT AVAILABLE branch, Vol Boost again, and a run of a second shortcut called Alley parking is](/img/2026/10/shortcut-alley-parking-2.jpg)

When it's done talking, it puts the volume back with a second "Vol Boost" and runs another shortcut, "Alley parking is", which asks the Home Assistant app for a snapshot from the alley camera and shows it, attached, in a notification:

![The Alley parking is shortcut: it receives text, replaces part of it, gets a camera snapshot from the Alley Camera, and shows a notification](/img/2026/10/shortcut-alley-parking-is.jpg)

![The notification on the lock screen: Alley parking is AVAILABLE, with the camera picture of the empty parking pad underneath](/img/2026/10/shortcut-notification.jpg)
*What lands on my phone.*

So by the time I turn into the alley, I've heard the answer and I have a picture to glance at when I stop.

The family room tablet (one of the [wall tablets I wrote about before](/rewriting-my-home-assistant-dashboards-in-plain-html)) shows the alley camera in a card on its main page. The bar at the bottom names the car the model identified, along with what charging has cost this month, and a small badge shows what the charger is doing. A glance at the wall tells me which car is parked there.

![The alley camera card from the family room tablet: the night picture with a Subaru on the pad, a badge reading Charging 7.2 kW, 12.4 kWh, 2 h, and a bar reading Subaru, $24 of $61 this month on the left and Alley on the right](/img/2026/10/parking-pad-tablet.jpg)
*The alley card on the family room tablet. The real dashboard code, but running against a fake Home Assistant: the charging numbers and costs are made up, and the picture is one of the snapshots above.*

## Step 8: Keep the Camera Honest

A detector that's looking at a frozen picture will happily tell you the same wrong answer forever, and the Ring integration did freeze now and then. Every 5 minutes, a tiny Python script compares the latest snapshot to the one from 5 minutes before. If they're pixel-for-pixel identical for about 5 and a half minutes, the camera feed is stuck and Home Assistant restarts the `ring-mqtt` container to fix it.

## How Well Does It Work?

I haven't measured it with a stopwatch and a spreadsheet. But it's been running for a long time, I use it constantly, and my honest estimate is that it's right more than 95% of the time. The misses are rare. When it's wrong, it's almost always the same kind of mistake: it says a car is there when the pad is empty. A false "taken" is the safer error, since the notification includes the picture and you can see for yourself. I haven't tracked the exact rate.

The scores in the training table above are not an independent test, because the model was checked against the same pictures it learned from. The real test is the one I've been running ever since: living with it. If you build your own, keep some pictures out of training and check against those.

## What I'd Tell Someone Starting Out

- **Fix your camera view before collecting pictures.** A fixed camera is a big advantage. The model never has to cope with changing angles.
- **Match the effort to the job.** A general model needs lots of varied pictures. A fixed camera with three possible answers needs far fewer, and a model that has nearly memorized your scene can be exactly what you want.
- **Think about the empty scene.** A model that only knows your three cars has to answer "none" for an empty pad, and that's the case where mine still slips now and then.
- **Try cropping.** Cropping is what first got my generic model to see my cars at all. If your target is small in the frame, it's worth a try.
- **Use a held-out set.** Keep some pictures aside that the model never sees, and keep a copy of any model that works before you try to improve it. Also write down which training run each file came from. I didn't, and now I can't say.
- **Make the answer slow to change.** A little patience in the logic matters more than a better model.
