+++
title = "Is the Parking Spot Free? Training My Own AI to Recognize Our Cars"
date = 2026-10-20
path = "is-the-parking-spot-free-custom-ai-car-detection-home-assistant"
description = "I trained a small YOLOv5 model on photos from my alley camera so Home Assistant can tell our three cars apart, and so my phone can say whether the parking spot behind the house is free before I get home."

[taxonomies]
category = ["Smart Home"]
tag = ["home assistant", "ai", "camera", "codeproject.ai", "yolo"]
+++

> **DRAFT: not ready to merge.** Every `TODO(Jon)` note below is a fact only the owner knows. Delete this box and every TODO before publishing.

We live in a row home. There's no driveway in front, just a single parking pad behind the house, off the alley. If a car is on it, the other car parks on the street, sometimes a few blocks away. So the question I ask the most when I'm driving home is: **is the spot free?**

Now my phone answers it before I get there. When my wife or I get close to home, we get a voice message saying whether parking is available, and a notification with a picture from the alley camera so we can check it ourselves. In Apple CarPlay the parking pad even shows up as a garage door: open means free, closed means a car is on it.

Under it all is a small AI model I trained to recognize our three cars. By my own count it's right more than 95% of the time.

![The alley at night in infrared: a dark SUV on the parking pad with the charger cable on the ground beside it](/img/2026/10/parking-pad-night.jpg)
*The Hyundai on the pad at night, in infrared. This is the real picture the model works from.*

## Why a Generic Model Wasn't Enough

I run [CodeProject.AI](https://www.codeproject.com/Articles/5322557/CodeProject-AI-Server-AI-the-easy-way) in Docker on my home server. It's a free object detection server that runs on your own hardware, and Home Assistant can send it pictures over a simple HTTP call. Out of the box it knows what a "car" is. I started there, using the ready-made `ipcam-combined` model that comes with it.

That did not go well. Our alley camera is a wide-angle view looking down on the pad from above, so the cars aren't seen from the side the way they are in most training photos. The generic model often found nothing at all. It also couldn't do the one thing I actually cared about, which was to tell *our* cars from anyone else's.

I only wanted one question answered: *which of our three cars is on the pad, if any?* That's three possible answers, from one camera that never moves. (I set all of this up about two years ago, with a lot of help from ChatGPT on the training side.)

Two things turned it around:

1. **Cropping.** When I cut the picture down to just the area where the car parks, the model suddenly saw cars it had missed in the full picture. The car only takes up part of the frame, and a small object in a large picture is hard to detect.
2. **Training my own model on our three cars.** Not "car", but `hyundai`, `mercedes` and `subaru`.

## Step 1: Collect Pictures

The camera is a Ring camera. [`ring-mqtt`](https://github.com/tsightler/ring-mqtt) gives Home Assistant a fresh snapshot about every 30 seconds, and an automation saves it over the same file each time. That one file is the input for everything else.

To build a training set, I wrote a small Python script and ran it from cron every few minutes. It takes the current snapshot, shrinks it to fit in 640×640 pixels (the size the model trains on), pads it with black bars so the shape isn't distorted, and saves it under the next free number: `0001.jpg`, `0002.jpg` and so on. Over time that collects every kind of light and weather: sun, rain, snow, dusk, and night in infrared.

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

> **TODO(Jon):** your crontab line, if you'd like it shown (`crontab -l | grep photo-save`), and roughly how many weeks it ran. The numbers in the training-images folder went past 3,800.

One thing I worried about at first was overfitting: a model that has memorized its pictures instead of learning what a car looks like. For a general-purpose model that's a real problem. For mine it turned out to help. The camera never moves, there are only three answers, and the cars park in nearly the same places every time, so a model that knows exactly what *these* cars look like from *this* spot is just what I want. It's a very narrow job, and I wouldn't claim the same thing works for a camera that sees strangers' cars.

Even so, hundreds of near-identical pictures of one parked car don't teach much. Variety (different light, weather, parking positions, and the empty pad) is what helps.

![The alley in daylight: a dark SUV with bikes on the roof parked on the pad](/img/2026/10/parking-pad-day.jpg)
*The Mercedes in daylight, with bikes on the roof.*

![A car parked toward the right edge of the pad at night, the charger cable lying across the ground](/img/2026/10/parking-pad-charging.jpg)
*The Subaru parked toward one side at night, charging. It still needs to count as "taken".*

![The empty parking pad at night in infrared](/img/2026/10/parking-pad-empty.jpg)
*The empty pad. Pictures with no car matter just as much.*

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

A few of my example files are named for how the picture is framed: `hyundai-full-1.jpg`, `hyundai-cropped-1.jpg`, `hyundai-left-1.jpg`, `hyundai-right-1.jpg`. Each is a different view of the same scene: the whole frame, the cropped area, and the left or right half. I also went back and labeled the images a second time after resizing them to 640×640, because the boxes from the original size were no longer in the right place.

> **TODO(Jon):** how long did labeling take? How did you tell the model "this is an empty pad": images with no label file, or something else?

## Step 3: Train

I used [YOLOv5](https://github.com/ultralytics/yolov5), the version CodeProject.AI's detector understands, and started from the small pretrained `yolov5s.pt` model instead of from scratch. It already knows what edges, wheels and windows look like, so my 262 pictures only have to teach it *our* cars.

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

| | Precision | Recall | mAP@50 |
|---|---:|---:|---:|
| All cars | 0.912 | 0.910 | 0.971 |
| Hyundai | 0.942 | 0.961 | 0.985 |
| Mercedes | 0.938 | 0.863 | 0.969 |
| Subaru | 0.855 | 0.906 | 0.958 |

(Precision is how often a "Subaru" call was right. Recall is how many of the real Subarus it found.)

> **TODO(Jon):** the model running today may **not** be that first one. The server's `custom-model.pt` (56.8 MB, Nov 2024) is the same size as `custom-model-276.pt`, and the 14 MB `custom-model-370.pt` matches the first run (it stopped at epoch 370). These two commands will tell us which file is which. The first one runs on the server and shows which files are byte-for-byte the same:
>
> ```bash
> cd ~/codeproject && md5sum custom-model.pt custom-model-*.pt best.pt
> ```
>
> The second runs on the training machine inside the `yolov5` folder (it prints the epoch, the date, the model size and the class names stored in the file; a depth of 0.33 is the small model, 0.67 medium, 1.0 large). Please run it for `custom-model.pt` and paste the output:
>
> ```bash
> python3 -c "import torch; c=torch.load('/path/to/custom-model.pt', map_location='cpu', weights_only=False); print(c.get('epoch'), c.get('date'), c['model'].yaml.get('depth_multiple'), c['model'].names)"
> ```
>
> Also, how many pictures are in each dataset folder (`dataset/image-collections`, `dataset/multiple-vehicles`, `dataset/car`)? `ls dataset/multiple-vehicles/images/train | wc -l` works for each. If you retrained with a separate validation set, I'll replace the caveat above with real numbers.

## Step 4: Put the Model in CodeProject.AI

This was the part with the least documentation. CodeProject.AI's YOLOv5 detector looks in a `custom-models` folder inside its module. Any `.pt` file you drop in becomes its own endpoint, named after the file. My file is `custom-model.pt`, so my endpoint is `/v1/vision/custom/custom-model`.

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

> **TODO(Jon):** did `best.pt` load as it was, or did you have to convert or rename anything? Does the server use the GTX 1060 now? (The `inferenceDevice` in the old notes said CPU.) What's the usual `inferenceMs`?

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
*What the model actually receives. The distant buildings, bins and the neighbor's car are cut off, and the car is big.*

> **TODO(Jon):** your example folder has cropped and left/right-half versions as well as whole frames, so I think the model was trained on crops too, which would explain why the crop works so well in production. Is that right? And did the crop also help by hiding the far end of the alley, where other cars sit?

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

- It switches to **occupied** after one of our three cars has been seen for 34 seconds in a row.
- It switches to **free** only after 64 seconds with none.

Those odd numbers are roughly one and two snapshots. It's deliberately slower to say "free" than "taken".

A final sensor follows that one, and it also turns on if the car charger is plugged in. That's what everything else in the house reads.

> **TODO(Jon):** why 34 and 64? Were they tuned from real data, or picked by feel?

## Step 7: Tell the Phone

This is the part my family actually uses.

**The garage door.** I made a template cover called "Alley Garage Door" whose state is simply "the pad is free". Home Assistant's HomeKit bridge shows it to Apple Home, and Apple's CarPlay shows garage doors, so the parking pad appears on the car's screen as a door: open means a free spot, closed means taken. Tapping it sends the notification below. Nothing is opened or closed, since there's no door.

**The notification.** A script sends both of our phones a message: "Parking Behind House is **AVAILABLE**" or "**NOT AVAILABLE**", with the latest snapshot attached. The picture matters, because it lets you check the AI at a glance. The script then waits ten minutes before it will run again, so tapping repeatedly can't spam anyone.

**The voice alert.** On the iPhone, a Shortcuts automation runs when we get near home. It reads the sensor through the Home Assistant app, says the answer out loud, and sends the picture notification. It works while driving, without touching anything.

![The family room tablet's alley view with the camera picture and the name of the car the model identified](/img/2026/10/parking-pad-day.jpg)

> **TODO(Jon):** I need real screenshots for these, since I can't take them: (1) the CarPlay tile or the Apple Home tile, (2) the "Parking Behind House is…" notification with its picture, (3) the Shortcuts automation, and (4) the family room tablet's alley view. Blur anything private. I'll replace the placeholder above (it's the day picture again) once they arrive.

## Step 8: Keep the Camera Honest

A detector that's looking at a frozen picture will happily tell you the same wrong answer forever, and the Ring integration did freeze now and then. Every 5 minutes, a tiny Python script compares the latest snapshot to the one from 5 minutes before. If they're pixel-for-pixel identical for about 5 and a half minutes, the camera feed is stuck and Home Assistant restarts the `ring-mqtt` container to fix it.

## How Well Does It Work?

I haven't measured it with a stopwatch and a spreadsheet. But it's been running for a long time, we use it constantly, and my honest estimate is that it's right more than 95% of the time. The failures I know of:

> **TODO(Jon):** what do the misses look like (a particular night, snow on the car, someone else's car, a delivery truck, the Mercedes in the dark)? Any fix you made? If you want a real number, run this on the server and I'll turn it into a chart:
>
> ```bash
> docker exec homeassistant python3 /config/scripts/ha_check.py --changes=binary_sensor.alley_car_occupancy
> ```

The scores in the training table above are not an independent test, because the model was checked against the same pictures it learned from. The real test is the one I've been running ever since: living with it. If you build your own, keep some pictures out of training and check against those.

## What I'd Tell Someone Starting Out

- **Fix your camera view before collecting pictures.** A fixed camera is a big advantage. The model never has to cope with changing angles.
- **Variety beats volume.** A thousand copies of the same parked car are worth less than fifty different situations.
- **Include the empty scene.** The model has to know what "nothing" looks like too.
- **Crop and enlarge.** If your target is small in the frame, this may help more than any training setting.
- **Use a held-out set.** Keep some pictures aside that the model never sees, and keep a copy of any model that works before you try to improve it.
- **Make the answer slow to change.** A little patience in the logic matters more than a better model.

> **TODO(Jon):** I can also write a follow-up about the other thing this feeds: the EV charger's monthly cost split by car, using this model to know which car is plugged in. Say the word. If it's a follow-up, it would become a two-part series with this post, so I'll ask you before moving anything.
