#!/usr/bin/env python3
"""
Mochi - a tiny, squishy desktop pet blob.

Pet it, feed it, throw it around, play ball, make it dance, tell jokes,
and play Star Catch. Mochi remembers you between runs.

Pure Python 3 + Tkinter, no other dependencies.
    Linux Mint / Ubuntu:  sudo apt install python3-tk   (usually already there)
    Run:                  python3 mochi.py
"""

import colorsys
import json
import math
import os
import random
import time
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, simpledialog

W, H = 880, 540
GROUND = 452
FRAME_MS = 33
R = 56  # Mochi's radius

SAVE_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "mochi")
SAVE_FILE = os.path.join(SAVE_DIR, "save.json")

COLORS = [  # (name, hue, saturation, value)
    ("Mint", 0.40, 0.45, 0.86),
    ("Bubblegum", 0.95, 0.38, 0.98),
    ("Sky", 0.56, 0.45, 0.95),
    ("Lemon", 0.14, 0.55, 0.98),
    ("Lavender", 0.74, 0.35, 0.93),
    ("Peach", 0.06, 0.45, 0.99),
]

JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs!",
    "I'd tell you a UDP joke, but you might not get it.",
    "Why was the computer cold? It left its Windows open. Good thing you use Linux!",
    "There are 10 kinds of people: those who understand binary and those who don't.",
    "How does a penguin build its house? Igloos it together!",
    "I told my computer a joke. It didn't laugh. It just said 'Segmentation fault'.",
    "Why did the developer go broke? They used up all their cache.",
    "What do you call a sleeping dinosaur? A dino-snore!",
    "I'm reading a book about anti-gravity. It's impossible to put down!",
    "Why don't eggs tell jokes? They'd crack each other up.",
    "What do you call a fake noodle? An impasta!",
    "Why did the scarecrow win an award? He was outstanding in his field!",
    "Why can't you trust atoms? They make up everything!",
    "What did the ocean say to the beach? Nothing, it just waved.",
    "What do you call a bear with no teeth? A gummy bear! ...a distant cousin of mine.",
    "My favourite exercise? Jumping to conclusions. And also just jumping. I'm a blob.",
    "Why did the math book look sad? It had too many problems.",
    "Parallel lines have so much in common. Shame they'll never meet.",
    "Knock knock! Who's there? Interrupting blob! Interrupting bl- BLOOP!",
    "Why do bees have sticky hair? Because they use honeycombs!",
    "What's a blob's favourite dessert? Jell- ...wait. Oh no. OH NO.",
    "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'",
    "!false  -- it's funny because it's true.",
    "Why did the functions stop calling each other? Too many arguments.",
]

CHATTER = [
    "Hi friend!", "Boing!", "Bloop.", "*happy wiggle*",
    "I'm 97% jelly and 3% love.",
    "Linux Mint is my favourite flavour.",
    "Psst... you can drag me and THROW me!",
    "Click anywhere and I'll hop over there!",
    "Have you had some water today?",
    "You're doing great, by the way.",
    "I wonder what's outside this window...",
    "Right-click me for more options!",
    "I heard there's a secret word... it rhymes with 'flux'.",
    "Squish level: optimal.",
]

GIGGLES = ["Hehe!", "That tickles!", "Eee!", "More pets pls", "I love you!",
           "*purrs in blob*", "Squishy!", "Yay!", "<3", "Best human ever!"]

NOMS = ["Nom nom!", "Yummy!", "Mmmm!", "Delicious!", "*chomp*", "Tasty!"]


# ----------------------------------------------------------------- helpers
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def hsv(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, clamp(s, 0, 1), clamp(v, 0, 1))
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def pick_font_family(root):
    available = set(tkfont.families(root))
    for fam in ("Ubuntu", "Noto Sans", "DejaVu Sans", "Liberation Sans", "Helvetica"):
        if fam in available:
            return fam
    return "TkDefaultFont"


# ----------------------------------------------------------------- the app
class MochiApp:
    def __init__(self, root):
        self.root = root
        self.fam = pick_font_family(root)
        root.title("Mochi - your pocket blob")
        root.resizable(False, False)
        root.configure(bg="#2b2d42")
        self._set_icon()

        self.canvas = tk.Canvas(root, width=W, height=H, highlightthickness=0, bg="#6ec6ff")
        self.canvas.pack()
        self._build_buttons()
        self._build_menu()

        # world state
        self.t = 0.0
        self.last_time = time.time()
        self.mouse = (W / 2, H / 2)
        self.mouse_moved_at = 0.0
        self.keys = set()
        self.typed = ""
        self.sky_override = None
        self.period = None
        self.particles = []
        self.food = []
        self.ball = None
        self.game = None
        self.tux = None
        self.disco = 0.0
        self.bubble = None  # (text, time_left)
        self.next_chatter = 12.0
        self.next_wander = 3.0
        self.clouds = [dict(x=random.uniform(0, W), y=random.uniform(40, 170),
                            s=random.uniform(0.7, 1.3), v=random.uniform(0.15, 0.45))
                       for _ in range(5)]
        self.fireflies = [dict(x=random.uniform(0, W), y=random.uniform(260, GROUND),
                               p=random.uniform(0, 6.28)) for _ in range(14)]
        rnd = random.Random(7)
        self.stars = [(rnd.uniform(0, W), rnd.uniform(0, 300), rnd.choice((1, 1, 1.5, 2)))
                      for _ in range(90)]
        self.flowers = [(rnd.uniform(10, W - 10), rnd.uniform(GROUND + 12, H - 8),
                         rnd.choice(("#ff6b8b", "#ffd166", "#ffffff", "#c77dff", "#ff9f1c")))
                        for _ in range(26)]

        self.m = dict(x=W / 2, y=GROUND, vx=0.0, vy=0.0, on_ground=True,
                      s=0.0, sv=0.0, target=None, dragged=False, sleeping=False,
                      dizzy=0.0, happy=0.0, eating=0.0, blink=0.0, next_blink=2.0,
                      hop_cd=0.0, beat=0.0, ball_cd=0.0)
        self.drag = None

        self.load()
        self._bind()
        self.draw_background()
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.after(FRAME_MS, self.tick)
        self.root.after(30000, self.autosave)

    # ------------------------------------------------------------ setup
    def _set_icon(self):
        img = tk.PhotoImage(width=32, height=32)
        body, dark = hsv(0.40, 0.45, 0.86), hsv(0.40, 0.6, 0.5)
        for y in range(32):
            for x in range(32):
                d = math.hypot(x - 15.5, (y - 17) * 1.15)
                if d < 13:
                    img.put(body, (x, y))
                elif d < 14.5:
                    img.put(dark, (x, y))
        for ex in (11, 20):
            img.put("#222222", to=(ex, 14, ex + 2, 18))
        img.put("#ff9fb0", to=(7, 19, 10, 21))
        img.put("#ff9fb0", to=(22, 19, 25, 21))
        self._icon = img
        self.root.iconphoto(True, img)

    def _build_buttons(self):
        bar = tk.Frame(self.root, bg="#2b2d42", pady=8)
        bar.pack(fill="x")
        spec = [
            ("Feed  [1]", "#ef476f", self.feed),
            ("Play  [2]", "#118ab2", self.play),
            ("Joke  [3]", "#f4a261", self.joke),
            ("Dance  [4]", "#9b5de5", self.dance),
            ("Sleep  [5]", "#3a0ca3", self.toggle_sleep),
            ("Star Catch  [6]", "#e9a100", self.start_game),
        ]
        self.buttons = []
        for text, color, cmd in spec:
            b = tk.Button(bar, text=text, command=cmd, bg=color, fg="white",
                          activebackground=mix(color, "#ffffff", 0.25), activeforeground="white",
                          relief="flat", bd=0, padx=14, pady=7, cursor="hand2",
                          font=(self.fam, 11, "bold"), highlightthickness=0)
            b.pack(side="left", padx=6, expand=True, fill="x")
            self.buttons.append(b)
        self.sleep_btn = self.buttons[4]

    def _build_menu(self):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Rename...", command=self.rename)
        menu.add_command(label="Change colour", command=self.recolor)
        sky = tk.Menu(menu, tearoff=0)
        sky.add_command(label="Automatic (real clock)", command=lambda: self.set_sky(None))
        sky.add_command(label="Day", command=lambda: self.set_sky("day"))
        sky.add_command(label="Sunset", command=lambda: self.set_sky("sunset"))
        sky.add_command(label="Night", command=lambda: self.set_sky("night"))
        menu.add_cascade(label="Sky", menu=sky)
        menu.add_separator()
        menu.add_command(label="How to play", command=self.about)
        menu.add_command(label="Quit", command=self.quit)
        self.menu = menu

    def _bind(self):
        c = self.canvas
        c.bind("<Motion>", self.on_motion)
        c.bind("<ButtonPress-1>", self.on_press)
        c.bind("<B1-Motion>", self.on_drag)
        c.bind("<ButtonRelease-1>", self.on_release)
        c.bind("<Button-3>", lambda e: self.menu.tk_popup(e.x_root, e.y_root))
        self.root.bind("<KeyPress>", self.on_key)
        self.root.bind("<KeyRelease>", lambda e: self.keys.discard(e.keysym))

    # ------------------------------------------------------------ save/load
    def load(self):
        data = {}
        try:
            with open(SAVE_FILE) as f:
                data = json.load(f)
        except (OSError, ValueError):
            pass
        now = time.time()
        self.first_run = not data
        self.name = data.get("name", "Mochi")
        self.color_idx = data.get("color", 0) % len(COLORS)
        self.born = data.get("born", now)
        self.best = data.get("best", 0)
        self.pets = data.get("pets", 0)
        self.food_lvl = data.get("food", 80.0)
        self.fun = data.get("fun", 80.0)
        self.energy = data.get("energy", 90.0)
        away = now - data.get("last_seen", now)
        if away > 0:
            hours = min(away, 8 * 3600) / 3600.0
            self.food_lvl = clamp(self.food_lvl - hours * 8, 15, 100)
            self.fun = clamp(self.fun - hours * 6, 20, 100)
            self.energy = clamp(self.energy + hours * 20, 0, 100)
        if self.first_run:
            self.root.after(700, self.ask_name)
        elif away > 90:
            self.root.after(800, lambda: (self.say("You're back!! I missed you!"), self.hearts(12)))
        else:
            self.root.after(800, lambda: self.say("Hi again!"))

    def save(self):
        data = dict(name=self.name, color=self.color_idx, born=self.born, best=self.best,
                    pets=self.pets, food=self.food_lvl, fun=self.fun, energy=self.energy,
                    last_seen=time.time())
        try:
            os.makedirs(SAVE_DIR, exist_ok=True)
            with open(SAVE_FILE, "w") as f:
                json.dump(data, f)
        except OSError:
            pass

    def autosave(self):
        self.save()
        self.root.after(30000, self.autosave)

    def quit(self):
        self.save()
        self.root.destroy()

    # ------------------------------------------------------------ menu actions
    def ask_name(self):
        self.say("A wild blob appeared!")
        name = simpledialog.askstring("A wild blob appeared!",
                                      "A squishy little blob has hatched on your desktop!\n\n"
                                      "What would you like to name it?",
                                      initialvalue="Mochi", parent=self.root)
        if name and name.strip():
            self.name = name.strip()[:18]
        self.say("Hi! I'm %s! Click me, feed me, throw me!" % self.name)
        self.hearts(10)
        self.save()

    def rename(self):
        name = simpledialog.askstring("Rename", "New name for your blob:",
                                      initialvalue=self.name, parent=self.root)
        if name and name.strip():
            self.name = name.strip()[:18]
            self.say("%s! I love it!" % self.name)
            self.hearts(8)

    def recolor(self):
        self.color_idx = (self.color_idx + 1) % len(COLORS)
        self.say("Ooh, %s suits me!" % COLORS[self.color_idx][0])
        self.sparkles(self.m["x"], self.m["y"] - R, 25)

    def set_sky(self, mode):
        self.sky_override = mode
        self.period = None

    def about(self):
        messagebox.showinfo("How to play", (
            "Meet %s, your pocket blob!\n\n"
            "Click %s  -  pet (hearts!)\n"
            "Drag & release  -  throw it around\n"
            "Click the ground  -  it hops there\n"
            "Click the ball  -  kick it\n\n"
            "1 Feed    2 Play ball    3 Joke\n"
            "4 Dance   5 Sleep        6 Star Catch\n"
            "Space  -  jump      Arrows  -  move in Star Catch\n\n"
            "Keep Food, Fun and Energy up to keep it happy.\n"
            "The sky follows your real clock.\n\n"
            "Psst... there are secret words you can type.\n"
            "Try: tux, party, sudo ...and maybe more." % (self.name, self.name)),
            parent=self.root)

    # ------------------------------------------------------------ actions
    def feed(self):
        if self.m["sleeping"]:
            return self.say("Zzz... (not now...)")
        if len(self.food) >= 5:
            return self.say("One at a time, hehe!")
        self.food.append(dict(x=random.uniform(80, W - 80), y=-20, vy=0.0,
                              kind=random.choice(("apple", "cookie", "donut", "cake")),
                              rot=random.uniform(0, 6.28), landed=False))
        if self.food_lvl > 95:
            self.say("I'm stuffed... but okay!")

    def play(self):
        if self.m["sleeping"]:
            return self.say("Zzz... ball... tomorrow...")
        if self.ball:
            self.ball["vy"] = -15
            self.ball["vx"] = random.uniform(-10, 10)
            return self.say("Wheee!")
        side = random.choice((-1, 1))
        self.ball = dict(x=W / 2 - side * (W / 2 - 40), y=120, vx=side * 9.0, vy=-4.0, r=24, rot=0.0)
        self.say("A BALL!!!")

    def joke(self):
        if self.m["sleeping"]:
            return self.say("Zzz... knock knock... zzz...")
        self.say(random.choice(JOKES), 7.0)
        self.m["happy"] = 2.0

    def dance(self):
        if self.m["sleeping"]:
            return self.say("Zzz... *dances in dreams*")
        if self.energy < 8:
            return self.say("Too tired to boogie...")
        self.disco = 10.0
        self.say(random.choice(("Let's DANCE!", "Drop the beat!", "Disco time!")))

    def toggle_sleep(self):
        m = self.m
        if m["sleeping"]:
            self.wake("Good morning!!")
        else:
            if self.game:
                return
            m["sleeping"] = True
            self.disco = 0
            self.sleep_btn.config(text="Wake  [5]")
            self.say("Nighty night...")

    def wake(self, text):
        self.m["sleeping"] = False
        self.sleep_btn.config(text="Sleep  [5]")
        self.jump(-11)
        self.say(text)

    def start_game(self):
        if self.game:
            return
        if self.m["sleeping"]:
            self.wake("Huh?! A game? I'm up!")
        self.disco = 0
        self.m["target"] = None
        self.game = dict(time=30.0, score=0, items=[], spawn=1.0, ended=0.0)
        self.say("Catch the stars! Mouse or arrow keys to move, Space to jump. Avoid storm clouds!", 4.0)

    def jump(self, power=-15):
        m = self.m
        if m["on_ground"] and not m["dragged"]:
            m["vy"] = power
            m["on_ground"] = False
            m["sv"] -= 0.12

    # ------------------------------------------------------------ particles/speech
    def say(self, text, secs=None):
        self.bubble = [text, secs or clamp(1.5 + len(text) * 0.06, 2.0, 6.0)]

    def add_particle(self, **kw):
        p = dict(vx=0.0, vy=0.0, g=0.0, life=1.0, color="#ffffff", text=None, size=14,
                 kind="text", rot=0.0, vr=0.0)
        p.update(kw)
        p["max"] = p["life"]
        self.particles.append(p)

    def hearts(self, n=6, x=None, y=None):
        x = self.m["x"] if x is None else x
        y = self.m["y"] - R * 1.6 if y is None else y
        for _ in range(n):
            self.add_particle(x=x + random.uniform(-30, 30), y=y + random.uniform(-10, 10),
                              vx=random.uniform(-1.5, 1.5), vy=random.uniform(-3.5, -1.5),
                              g=0.03, life=random.uniform(1.0, 1.8), text="♥",
                              color=random.choice(("#ff4d6d", "#ff758f", "#ff8fab", "#f72585")),
                              size=random.randint(14, 26))

    def sparkles(self, x, y, n=12, colors=("#fff3b0", "#ffd166", "#ffffff")):
        for _ in range(n):
            a = random.uniform(0, 6.28)
            sp = random.uniform(2, 6)
            self.add_particle(x=x, y=y, vx=math.cos(a) * sp, vy=math.sin(a) * sp, g=0.1,
                              life=random.uniform(0.5, 1.0), text="★",
                              color=random.choice(colors), size=random.randint(8, 16))

    def confetti(self, n=80, x=None, y=None):
        for _ in range(n):
            self.add_particle(kind="confetti",
                              x=random.uniform(0, W) if x is None else x,
                              y=random.uniform(-40, 0) if y is None else y,
                              vx=random.uniform(-3, 3), vy=random.uniform(-2, 4) if y is None
                              else random.uniform(-12, -4),
                              g=0.18, life=random.uniform(2.5, 4.0), rot=random.uniform(0, 6.28),
                              vr=random.uniform(-0.3, 0.3),
                              color=hsv(random.random(), 0.75, 1.0), size=random.randint(5, 9))

    def float_text(self, x, y, text, color="#ffffff", size=16):
        self.add_particle(x=x, y=y, vy=-1.6, life=1.0, text=text, color=color, size=size)

    # ------------------------------------------------------------ input
    def blob_center(self):
        m = self.m
        return m["x"], m["y"] - R * (1 - m["s"])

    def over_blob(self, x, y):
        cx, cy = self.blob_center()
        return math.hypot(x - cx, y - cy) < R * 1.1

    def on_motion(self, e):
        self.mouse = (e.x, e.y)
        self.mouse_moved_at = self.t

    def on_press(self, e):
        self.mouse = (e.x, e.y)
        b = self.ball
        if b and math.hypot(e.x - b["x"], e.y - b["y"]) < b["r"] + 8:
            b["vx"] = (b["x"] - e.x) * 0.5 + random.uniform(-4, 4)
            b["vy"] = -15
            self.float_text(b["x"], b["y"] - 30, "Kick!", "#ffffff")
            return
        if self.over_blob(e.x, e.y):
            cx, cy = self.blob_center()
            self.drag = dict(ox=self.m["x"] - e.x, oy=self.m["y"] - e.y, sx=e.x, sy=e.y,
                             active=False, hist=[(e.x, e.y, self.t)])
        elif not self.game and not self.m["sleeping"] and e.y > 200:
            self.m["target"] = clamp(e.x, R, W - R)

    def on_drag(self, e):
        self.mouse = (e.x, e.y)
        d = self.drag
        if not d:
            return
        if not d["active"] and math.hypot(e.x - d["sx"], e.y - d["sy"]) > 6:
            d["active"] = True
            m = self.m
            m["dragged"] = True
            m["target"] = None
            if m["sleeping"]:
                self.wake("WHOA! I'm awake!")
            else:
                self.say(random.choice(("Whoa!", "Where are we going?", "Hehe, up!", "Eek!")))
        if d["active"]:
            m = self.m
            nx = clamp(e.x + d["ox"], R, W - R)
            ny = clamp(e.y + d["oy"], R * 2, GROUND)
            m["sv"] += (nx - m["x"]) * 0.004 + (ny - m["y"]) * 0.006
            m["x"], m["y"] = nx, ny
            d["hist"].append((e.x, e.y, self.t))
            d["hist"] = d["hist"][-6:]

    def on_release(self, e):
        d = self.drag
        self.drag = None
        if not d:
            return
        m = self.m
        if d["active"]:
            m["dragged"] = False
            (x0, y0, t0), (x1, y1, t1) = d["hist"][0], d["hist"][-1]
            dt = max(t1 - t0, 0.02)
            scale = FRAME_MS / 1000.0
            m["vx"] = clamp((x1 - x0) / dt * scale, -32, 32)
            m["vy"] = clamp((y1 - y0) / dt * scale, -32, 32)
            m["on_ground"] = False
            if math.hypot(m["vx"], m["vy"]) > 12:
                self.say(random.choice(("Wheeeee!", "I'm flyiiiing!", "Yahoo!", "AAAAA!")))
                self.fun = clamp(self.fun + 4, 0, 100)
        else:
            self.pet()

    def pet(self):
        m = self.m
        if m["sleeping"]:
            if random.random() < 0.5:
                return self.say("Mmh... five more minutes...")
            return self.wake("Oh! Hi! *yawn*")
        self.pets += 1
        m["happy"] = 1.6
        m["sv"] += 0.15
        self.fun = clamp(self.fun + 3, 0, 100)
        self.hearts(random.randint(4, 8))
        if random.random() < 0.6:
            self.say(random.choice(GIGGLES))
        if self.pets % 100 == 0:
            self.say("That's %d pets! You're the best!" % self.pets)
            self.confetti(120)

    def on_key(self, e):
        k = e.keysym
        self.keys.add(k)
        actions = {"1": self.feed, "2": self.play, "3": self.joke,
                   "4": self.dance, "5": self.toggle_sleep, "6": self.start_game}
        if k in actions:
            return actions[k]()
        if k == "space":
            if self.m["sleeping"]:
                return self.wake("Huh? What? I'm up!")
            return self.jump(-16)
        if len(e.char) == 1 and e.char.isalpha():
            self.typed = (self.typed + e.char.lower())[-12:]
            self.check_secrets()

    def check_secrets(self):
        s = self.typed
        m = self.m
        if s.endswith("tux"):
            self.typed = ""
            if not self.tux:
                self.tux = dict(x=-50.0, t=0.0, greeted=False)
                self.say("Is that... could it be...?!")
        elif s.endswith("party"):
            self.typed = ""
            self.confetti(160)
            self.disco = max(self.disco, 6.0)
            self.say("PARTY!!!")
        elif s.endswith("sudo"):
            self.typed = ""
            self.say("sudo make me a sandwich? ...okay, okay. Permission granted.")
            self.food.append(dict(x=clamp(m["x"] + 90, 60, W - 60), y=-20, vy=0.0, kind="sandwich",
                                  rot=0.0, landed=False))
        elif s.endswith(self.name.lower().replace(" ", "")[:10]) and len(self.name) > 1:
            self.typed = ""
            self.say("That's me!! You spelled my name!")
            self.hearts(20)
        elif s.endswith("hello"):
            self.typed = ""
            self.say("Hello hello hello!")
            self.jump(-12)
        elif s.endswith("night"):
            self.typed = ""
            self.set_sky("night")
            self.say("Ooh, stars!")
        elif s.endswith("day"):
            self.typed = ""
            self.set_sky("day")
            self.say("Hello, sunshine!")

    # ------------------------------------------------------------ main loop
    def tick(self):
        now = time.time()
        dt = clamp(now - self.last_time, 0.0, 0.1)
        self.last_time = now
        self.t += dt
        try:
            self.update(dt)
            self.draw()
        finally:
            self.root.after(FRAME_MS, self.tick)

    def update(self, dt):
        m = self.m
        # --- stats
        if m["sleeping"]:
            self.energy += 2.2 * dt
            self.food_lvl -= 0.04 * dt
            if self.energy >= 100:
                self.wake("Good morning!! I feel GREAT!")
            if random.random() < dt * 1.3:
                self.add_particle(x=m["x"] + 30, y=m["y"] - R * 1.5, vx=0.6, vy=-0.9,
                                  life=2.2, text="z", color="#e0e7ff", size=random.randint(12, 22))
        else:
            self.energy -= (0.05 + (0.4 if self.disco > 0 else 0) + (0.2 if self.game else 0)) * dt
            self.food_lvl -= 0.11 * dt
            self.fun -= (0.09 if self.food_lvl > 25 else 0.2) * dt
            if self.energy < 6 and not self.game and not m["dragged"]:
                m["sleeping"] = True
                self.disco = 0
                self.sleep_btn.config(text="Wake  [5]")
                self.say("So... sleepy... zzz")
        self.energy = clamp(self.energy, 0, 100)
        self.food_lvl = clamp(self.food_lvl, 0, 100)
        self.fun = clamp(self.fun, 0, 100)

        # --- timers
        for k in ("dizzy", "happy", "eating", "hop_cd", "ball_cd"):
            m[k] = max(0.0, m[k] - dt)
        m["next_blink"] -= dt
        if m["next_blink"] <= 0:
            m["blink"] = 0.14
            m["next_blink"] = random.uniform(2.0, 5.5)
        m["blink"] = max(0.0, m["blink"] - dt)
        if self.bubble:
            self.bubble[1] -= dt
            if self.bubble[1] <= 0:
                self.bubble = None
        if self.disco > 0:
            self.disco -= dt
            if self.disco <= 0:
                self.say(random.choice(("Phew! What a workout!", "*pant pant* again?!")))
                self.fun = clamp(self.fun + 15, 0, 100)
            elif random.random() < dt * 4:
                self.add_particle(x=m["x"] + random.uniform(-70, 70), y=m["y"] - R * 2,
                                  vx=random.uniform(-1, 1), vy=-1.5, life=1.5,
                                  text=random.choice(("♪", "♫")),
                                  color=hsv(random.random(), 0.6, 1), size=random.randint(16, 26))

        # --- idle chatter
        self.next_chatter -= dt
        if self.next_chatter <= 0 and not self.bubble and not m["sleeping"] and not self.game:
            self.next_chatter = random.uniform(18, 35)
            if self.food_lvl < 30:
                self.say(random.choice(("I'm hungry...", "Tummy rumbling...", "Food pls? (press 1)")))
            elif self.fun < 30:
                self.say(random.choice(("I'm bored... play with me?", "Ball? Ball? BALL?", "Tell me a joke!")))
            elif self.energy < 25:
                self.say("*yaaawn*")
            else:
                hour = time.localtime().tm_hour
                if hour >= 23 or hour < 5:
                    self.say("It's late! Shouldn't you be in bed? :)")
                else:
                    self.say(random.choice(CHATTER))

        self.update_behaviour(dt)
        self.update_physics()
        self.update_food()
        self.update_ball()
        self.update_game(dt)
        self.update_tux()

        # --- particles
        alive = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] > 0:
                p["vy"] += p["g"]
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["rot"] += p["vr"]
                if p["kind"] == "confetti" and p["y"] > GROUND + 30:
                    p["vy"], p["vx"], p["g"], p["vr"] = 0, 0, 0, 0
                alive.append(p)
        self.particles = alive[-400:]

        for c in self.clouds:
            c["x"] += c["v"]
            if c["x"] > W + 120:
                c["x"] = -120
                c["y"] = random.uniform(40, 170)

    def update_behaviour(self, dt):
        m = self.m
        if m["dragged"] or m["sleeping"] or m["dizzy"] > 0 or self.game:
            return
        target = m["target"]
        if self.food:
            target = min(self.food, key=lambda f: abs(f["x"] - m["x"]))["x"]
        elif self.ball:
            target = self.ball["x"]
        elif self.disco > 0:
            target = None
            m["beat"] -= dt
            if m["beat"] <= 0 and m["on_ground"]:
                m["beat"] = 0.45
                m["vy"] = -7
                m["vx"] = random.choice((-2.5, 2.5, 0))
                m["on_ground"] = False
            return
        else:
            self.next_wander -= dt
            if self.next_wander <= 0 and target is None:
                self.next_wander = random.uniform(4, 10)
                r = random.random()
                if r < 0.55:
                    m["target"] = clamp(m["x"] + random.uniform(-260, 260), R, W - R)
                elif r < 0.75:
                    self.jump(random.uniform(-10, -15))
        if target is None:
            return
        dx = target - m["x"]
        if abs(dx) < 10:
            if target == m["target"]:
                m["target"] = None
            return
        if m["on_ground"] and m["hop_cd"] <= 0:
            m["vy"] = -6.5
            m["vx"] = math.copysign(min(5.0, abs(dx) / 10 + 1.5), dx)
            m["on_ground"] = False
            m["sv"] -= 0.06

    def update_physics(self):
        m = self.m
        # jelly spring
        m["sv"] += -0.22 * m["s"]
        m["sv"] *= 0.84
        m["s"] = clamp(m["s"] + m["sv"], -0.35, 0.5)
        if m["dragged"]:
            m["vx"] = m["vy"] = 0
            return
        if self.game and m["dizzy"] <= 0:
            tx = m["x"]
            if "Left" in self.keys:
                tx -= 60
            if "Right" in self.keys:
                tx += 60
            if tx == m["x"] and self.t - self.mouse_moved_at < 1.5:
                tx = self.mouse[0]
            m["x"] += clamp(tx - m["x"], -11, 11)
            m["vx"] = 0
        m["vy"] += 0.9
        m["x"] += m["vx"]
        m["y"] += m["vy"]
        if m["y"] >= GROUND:
            impact = m["vy"]
            m["y"] = GROUND
            if impact > 2:
                m["sv"] += impact * 0.018
            if impact > 18:
                m["dizzy"] = 1.8
                self.say(random.choice(("@_@", "Oof! Again!", "Everything's spinning...", "Boing... ow")))
                self.sparkles(m["x"], GROUND - 10, 10, ("#ffffff", "#dddddd"))
            if impact > 8:
                m["vy"] = -impact * 0.42
                m["on_ground"] = False
            else:
                m["vy"] = 0
                m["on_ground"] = True
            m["vx"] *= 0.7
            if abs(m["vx"]) < 0.2:
                m["vx"] = 0
        else:
            m["on_ground"] = False
            m["vx"] *= 0.995
        if m["x"] < R or m["x"] > W - R:
            m["x"] = clamp(m["x"], R, W - R)
            if abs(m["vx"]) > 6:
                m["sv"] += 0.1
                self.float_text(m["x"], m["y"] - R, "Boink!", "#ffffff", 13)
            m["vx"] = -m["vx"] * 0.6
        if m["y"] < R * 2:
            m["y"] = R * 2
            m["vy"] = abs(m["vy"]) * 0.5

    def update_food(self):
        m = self.m
        cx, cy = self.blob_center()
        for f in self.food[:]:
            if not f["landed"]:
                f["vy"] += 0.45
                f["y"] += f["vy"]
                f["rot"] += 0.08
                if f["y"] >= GROUND - 12:
                    f["y"] = GROUND - 12
                    if f["vy"] > 4:
                        f["vy"] = -f["vy"] * 0.35
                    else:
                        f["landed"] = True
            if (abs(f["x"] - m["x"]) < R * 0.8 and abs(f["y"] - cy) < R * 1.2
                    and not m["sleeping"] and not m["dragged"]):
                self.food.remove(f)
                m["eating"] = 0.7
                m["sv"] += 0.12
                self.food_lvl = clamp(self.food_lvl + (35 if f["kind"] == "sandwich" else 22), 0, 100)
                self.fun = clamp(self.fun + 4, 0, 100)
                self.say("*BURP* ...excuse me!" if self.food_lvl >= 100 else random.choice(NOMS))
                crumb = {"apple": "#e63946", "cookie": "#c68b59", "donut": "#ff8fab",
                         "cake": "#fff1e6", "sandwich": "#f4d35e"}[f["kind"]]
                for _ in range(10):
                    self.add_particle(kind="dot", x=f["x"], y=f["y"], vx=random.uniform(-3, 3),
                                      vy=random.uniform(-5, -1), g=0.35, life=0.8, color=crumb,
                                      size=random.randint(3, 6))

    def update_ball(self):
        b = self.ball
        if not b:
            return
        m = self.m
        b["vy"] += 0.45
        b["x"] += b["vx"]
        b["y"] += b["vy"]
        b["rot"] += b["vx"] * 2.5
        if b["y"] + b["r"] >= GROUND:
            b["y"] = GROUND - b["r"]
            b["vy"] = -abs(b["vy"]) * 0.72 if abs(b["vy"]) > 1.5 else 0
            b["vx"] *= 0.985
        if b["x"] < b["r"] or b["x"] > W - b["r"]:
            b["x"] = clamp(b["x"], b["r"], W - b["r"])
            b["vx"] = -b["vx"] * 0.8
        if b["y"] < b["r"]:
            b["y"] = b["r"]
            b["vy"] = abs(b["vy"])
        cx, cy = self.blob_center()
        d = math.hypot(b["x"] - cx, b["y"] - cy)
        if d < R + b["r"] and m["ball_cd"] <= 0 and not m["sleeping"]:
            nx, ny = (b["x"] - cx) / (d or 1), (b["y"] - cy) / (d or 1)
            b["x"], b["y"] = cx + nx * (R + b["r"] + 1), cy + ny * (R + b["r"] + 1)
            b["vx"] = nx * 9 + m["vx"] * 0.6 + random.uniform(-2, 2)
            b["vy"] = min(ny * 9 + m["vy"] * 0.3, -8)
            m["ball_cd"] = 0.25
            m["sv"] += 0.1
            m["happy"] = max(m["happy"], 0.6)
            self.fun = clamp(self.fun + 2.5, 0, 100)
            self.energy -= 0.4
            if random.random() < 0.35:
                self.float_text(b["x"], b["y"] - 30, random.choice(("Boing!", "Bonk!", "Yay!")), "#ffffff")

    def update_game(self, dt):
        g = self.game
        if not g:
            return
        m = self.m
        if g["ended"] > 0:
            g["ended"] -= dt
            if g["ended"] <= 0:
                self.game = None
            return
        g["time"] -= dt
        progress = 1 - g["time"] / 30.0
        g["spawn"] -= dt
        if g["spawn"] <= 0:
            g["spawn"] = 0.55 - progress * 0.3
            r = random.random()
            kind = "gold" if r < 0.08 else "storm" if r < 0.3 else "star"
            g["items"].append(dict(x=random.uniform(30, W - 30), y=-20, kind=kind,
                                   vy=random.uniform(3, 4.5) + progress * 3.5, rot=0.0))
        cx, cy = self.blob_center()
        for it in g["items"][:]:
            it["y"] += it["vy"]
            it["rot"] += 0.1
            if math.hypot(it["x"] - cx, it["y"] - cy) < R * 0.95 + 14:
                g["items"].remove(it)
                if it["kind"] == "star":
                    g["score"] += 1
                    self.float_text(it["x"], it["y"], "+1", "#ffe066")
                    self.sparkles(it["x"], it["y"], 6)
                elif it["kind"] == "gold":
                    g["score"] += 5
                    self.float_text(it["x"], it["y"], "+5!!", "#ffb703", 22)
                    self.sparkles(it["x"], it["y"], 18, ("#ffb703", "#fb8500", "#ffffff"))
                else:
                    g["score"] = max(0, g["score"] - 3)
                    m["dizzy"] = 0.9
                    self.float_text(it["x"], it["y"], "-3  blub!", "#a2d2ff", 18)
                    for _ in range(12):
                        self.add_particle(kind="dot", x=it["x"] + random.uniform(-20, 20), y=it["y"],
                                          vy=random.uniform(2, 5), g=0.3, life=0.6,
                                          color="#90e0ef", size=3)
            elif it["y"] > GROUND + 10:
                g["items"].remove(it)
        if g["time"] <= 0:
            g["items"] = []
            score = g["score"]
            self.fun = clamp(self.fun + 10 + score, 0, 100)
            if score > self.best:
                self.best = score
                self.say("NEW RECORD: %d stars!!! We're amazing!" % score, 5)
                self.confetti(180)
                self.hearts(15)
                self.save()
            else:
                self.say("%d stars! (best: %d) Again? Press 6!" % (score, self.best), 5)
                self.hearts(5)
            g["ended"] = 3.5

    def update_tux(self):
        tx = self.tux
        if not tx:
            return
        tx["x"] += 3.2
        tx["t"] += 1
        if not tx["greeted"] and abs(tx["x"] - self.m["x"]) < 140:
            tx["greeted"] = True
            self.say("TUX!!! It's really you! My hero!!")
            self.hearts(18)
            self.jump(-14)
        if tx["x"] > W + 60:
            self.tux = None
            self.say("Bye Tux! Keep the kernel warm!")

    # ------------------------------------------------------------ drawing
    def current_period(self):
        if self.sky_override:
            return self.sky_override
        hour = time.localtime().tm_hour
        if 7 <= hour < 17:
            return "day"
        if 5 <= hour < 7 or 17 <= hour < 20:
            return "sunset"
        return "night"

    def draw_background(self):
        c = self.canvas
        c.delete("bg")
        p = self.current_period()
        self.period = p
        top, bottom, hill1, hill2, ground = {
            "day": ("#5ab8f5", "#d4f1ff", "#98dc9a", "#72c77c", "#5fb865"),
            "sunset": ("#6a4c93", "#ffb38a", "#8f9b6a", "#6c8a5a", "#5b7c4e"),
            "night": ("#070b24", "#35295e", "#2c4656", "#223a47", "#1c3439"),
        }[p]
        bands = 48
        for i in range(bands):
            y0 = i * GROUND / bands
            c.create_rectangle(0, y0, W, y0 + GROUND / bands + 1, fill=mix(top, bottom, i / bands),
                               outline="", tags="bg")
        if p == "night":
            for x, y, s in self.stars:
                c.create_oval(x - s, y - s, x + s, y + s, fill="#ffffff", outline="", tags=("bg", "star"))
            c.create_oval(W - 170, 40, W - 100, 110, fill="#fff8dc", outline="", tags="bg")
            for (x, y, r) in ((W - 150, 62, 8), (W - 125, 88, 6), (W - 118, 58, 4)):
                c.create_oval(x - r, y - r, x + r, y + r, fill="#eee3b8", outline="", tags="bg")
        else:
            sx, sy = (W - 130, 80) if p == "day" else (W - 180, 300)
            for r, col in ((70, mix(bottom, "#fff6c2", 0.35)), (52, mix(bottom, "#fff0a0", 0.6)),
                           (38, "#ffe066" if p == "day" else "#ff9e5e")):
                c.create_oval(sx - r, sy - r, sx + r, sy + r, fill=col, outline="", tags="bg")
        # hills
        pts = [0, GROUND]
        for x in range(0, W + 41, 40):
            pts += [x, GROUND - 95 - 45 * math.sin(x / 150.0) - 20 * math.sin(x / 57.0)]
        pts += [W, GROUND]
        c.create_polygon(pts, fill=hill1, outline="", smooth=True, tags="bg")
        pts = [0, GROUND]
        for x in range(0, W + 41, 40):
            pts += [x, GROUND - 45 - 30 * math.sin(x / 110.0 + 2) - 10 * math.sin(x / 40.0)]
        pts += [W, GROUND]
        c.create_polygon(pts, fill=hill2, outline="", smooth=True, tags="bg")
        c.create_rectangle(0, GROUND, W, H, fill=ground, outline="", tags="bg")
        c.create_line(0, GROUND, W, GROUND, fill=mix(ground, "#ffffff", 0.2), width=3, tags="bg")
        rnd = random.Random(3)
        blade = mix(ground, "#000000", 0.2)
        for _ in range(140):
            x, y = rnd.uniform(0, W), rnd.uniform(GROUND + 6, H)
            c.create_line(x, y, x + rnd.uniform(-3, 3), y - rnd.uniform(4, 9), fill=blade, tags="bg")
        for x, y, col in self.flowers:
            if p == "night":
                col = mix(col, "#223344", 0.55)
            for a in range(5):
                ang = a * 1.2566
                px, py = x + math.cos(ang) * 4, y + math.sin(ang) * 4
                c.create_oval(px - 3, py - 3, px + 3, py + 3, fill=col, outline="", tags="bg")
            c.create_oval(x - 2, y - 2, x + 2, y + 2, fill="#ffcf33", outline="", tags="bg")
        c.tag_lower("bg")

    def draw(self):
        c = self.canvas
        if self.current_period() != self.period:
            self.draw_background()
        c.delete("dyn")
        night = self.period == "night"
        m = self.m
        T = ("dyn",)

        # twinkle
        if night and int(self.t * 10) % 3 == 0:
            for item in random.sample(c.find_withtag("star"), 6):
                c.itemconfig(item, fill=random.choice(("#ffffff", "#9fb4ff", "#fff3b0")))

        # clouds
        for cl in self.clouds:
            col = "#4b4f7a" if night else "#ffffff"
            x, y, s = cl["x"], cl["y"], cl["s"]
            for dx, dy, r in ((-38, 6, 22), (-12, -8, 30), (20, -2, 26), (44, 8, 18), (0, 10, 24)):
                r *= s
                c.create_oval(x + dx * s - r, y + dy * s - r, x + dx * s + r, y + dy * s + r,
                              fill=col, outline="", tags=T)

        # disco
        if self.disco > 0:
            c.create_rectangle(0, 0, W, GROUND, fill="#1a0b2e", outline="", tags=T)
            beat = int(self.t * 2.2)
            tw = W / 11
            for row in range(3):
                for col in range(11):
                    lit = (col + row + beat) % 3 == 0
                    c.create_rectangle(col * tw, GROUND + row * 30, (col + 1) * tw, GROUND + (row + 1) * 30,
                                       fill=hsv((col * 0.09 + row * 0.2 + beat * 0.13), 0.75,
                                                1.0 if lit else 0.35),
                                       outline="#0d0418", width=2, tags=T)
            bx, by = W / 2, 34
            for i in range(5):
                ang = math.pi / 2 + math.sin(self.t * 1.3 + i * 1.7) * 0.9
                col = hsv(self.t * 0.3 + i / 5, 0.8, 1)
                ex, ey = bx + math.cos(ang) * 600, by + math.sin(ang) * 600
                px, py = -math.sin(ang) * 55, math.cos(ang) * 55
                c.create_polygon(bx, by, ex + px, ey + py, ex - px, ey - py, fill=col,
                                 stipple="gray25", outline="", tags=T)
            c.create_line(bx, 0, bx, by - 20, fill="#bbbbbb", width=2, tags=T)
            c.create_oval(bx - 22, by - 22, bx + 22, by + 22, fill="#cfd8dc", outline="#90a4ae", tags=T)
            for i in range(10):
                a = self.t * 2 + i * 0.63
                if math.cos(a) > 0:
                    x = bx + math.sin(a) * 15
                    y = by - 14 + (i % 4) * 9
                    c.create_rectangle(x - 3, y - 3, x + 3, y + 3,
                                       fill=hsv(i / 10 + self.t, 0.3, 1), outline="", tags=T)

        # fireflies
        if night:
            for f in self.fireflies:
                f["p"] += 0.05
                f["x"] = (f["x"] + math.sin(f["p"] * 0.7) * 0.8) % W
                f["y"] = clamp(f["y"] + math.cos(f["p"]) * 0.6, 240, GROUND - 5)
                glow = (math.sin(f["p"] * 2) + 1) / 2
                if glow > 0.3:
                    r = 2 + glow * 2
                    c.create_oval(f["x"] - r * 2, f["y"] - r * 2, f["x"] + r * 2, f["y"] + r * 2,
                                  fill="#5c6b2e", outline="", stipple="gray50", tags=T)
                    c.create_oval(f["x"] - r, f["y"] - r, f["x"] + r, f["y"] + r,
                                  fill="#f4ff81", outline="", tags=T)

        for f in self.food:
            self.draw_food(f)
        if self.tux:
            self.draw_tux(self.tux)
        if self.ball:
            b = self.ball
            sh = clamp(1 - (GROUND - b["y"]) / 400, 0.3, 1)
            c.create_oval(b["x"] - 22 * sh, GROUND - 4, b["x"] + 22 * sh, GROUND + 5,
                          fill="#000000", stipple="gray25", outline="", tags=T)
            for i, col in enumerate(("#ef476f", "#ffffff", "#118ab2", "#ffffff",
                                     "#ffd166", "#ffffff")):
                c.create_arc(b["x"] - b["r"], b["y"] - b["r"], b["x"] + b["r"], b["y"] + b["r"],
                             start=b["rot"] + i * 60, extent=60, fill=col, outline="", tags=T)
            c.create_oval(b["x"] - b["r"], b["y"] - b["r"], b["x"] + b["r"], b["y"] + b["r"],
                          outline="#444444", width=2, tags=T)
            c.create_oval(b["x"] - 12, b["y"] - 16, b["x"] - 4, b["y"] - 9, fill="#ffffff",
                          outline="", tags=T)

        if self.game:
            for it in self.game["items"]:
                self.draw_game_item(it)

        self.draw_mochi()

        if m["sleeping"]:
            c.create_rectangle(0, 0, W, H, fill="#000022", stipple="gray50", outline="", tags=T)

        for p in self.particles:
            a = p["life"] / p["max"]
            if p["kind"] == "text":
                size = int(p["size"] * (0.6 + 0.4 * a))
                c.create_text(p["x"], p["y"], text=p["text"], fill=p["color"],
                              font=(self.fam, max(size, 6), "bold"), tags=T)
            elif p["kind"] == "dot":
                s = p["size"]
                c.create_oval(p["x"] - s, p["y"] - s, p["x"] + s, p["y"] + s, fill=p["color"],
                              outline="", tags=T)
            else:
                s = p["size"]
                ca, sa = math.cos(p["rot"]), math.sin(p["rot"])
                w, h = s, s * 0.5 * abs(math.sin(self.t * 5 + p["x"]))+1
                pts = []
                for dx, dy in ((-w, -h), (w, -h), (w, h), (-w, h)):
                    pts += [p["x"] + dx * ca - dy * sa, p["y"] + dx * sa + dy * ca]
                c.create_polygon(pts, fill=p["color"], outline="", tags=T)

        if self.bubble:
            cx, cy = self.blob_center()
            self.draw_bubble(self.bubble[0], cx, cy - R * (1 + m["s"]) - 18)
        self.draw_hud()

    def draw_food(self, f):
        c, T = self.canvas, ("dyn",)
        x, y, k = f["x"], f["y"], f["kind"]
        if k == "apple":
            c.create_oval(x - 13, y - 12, x + 13, y + 13, fill="#e63946", outline="#9d0208", width=2, tags=T)
            c.create_line(x, y - 11, x + 2, y - 20, fill="#6b3e26", width=3, tags=T)
            c.create_oval(x + 3, y - 22, x + 14, y - 15, fill="#52b788", outline="", tags=T)
            c.create_oval(x - 8, y - 6, x - 3, y, fill="#ffadad", outline="", tags=T)
        elif k == "cookie":
            c.create_oval(x - 14, y - 13, x + 14, y + 13, fill="#d4a373", outline="#a0643c", width=2, tags=T)
            for i in range(5):
                a = f["rot"] + i * 1.3
                px, py = x + math.cos(a) * 7, y + math.sin(a) * 6
                c.create_oval(px - 2.5, py - 2.5, px + 2.5, py + 2.5, fill="#5a3825", outline="", tags=T)
        elif k == "donut":
            c.create_oval(x - 11, y - 9, x + 11, y + 10, outline="#e9c46a", width=9, tags=T)
            c.create_oval(x - 11, y - 10, x + 11, y + 7, outline="#ff8fab", width=7, tags=T)
            for i in range(6):
                a = i * 1.05 + 0.3
                px, py = x + math.cos(a) * 9, y - 2 + math.sin(a) * 6
                c.create_line(px, py, px + 3, py + 1, fill=hsv(i / 6, 0.7, 1), width=2, tags=T)
        elif k == "cake":
            c.create_rectangle(x - 13, y - 6, x + 13, y + 12, fill="#fff1e6", outline="#c9ada7", width=2, tags=T)
            c.create_rectangle(x - 13, y - 9, x + 13, y - 3, fill="#ff8fab", outline="", tags=T)
            c.create_oval(x - 4, y - 18, x + 4, y - 10, fill="#e63946", outline="", tags=T)
        else:  # sandwich
            c.create_polygon(x - 18, y + 10, x + 18, y + 10, x, y - 16, fill="#f4d35e",
                             outline="#b08930", width=2, tags=T)
            c.create_line(x - 13, y + 4, x + 13, y + 4, fill="#52b788", width=4, tags=T)
            c.create_line(x - 9, y - 2, x + 9, y - 2, fill="#e63946", width=3, tags=T)

    def draw_game_item(self, it):
        c, T = self.canvas, ("dyn",)
        x, y = it["x"], it["y"]
        if it["kind"] == "storm":
            for dx, dy, r in ((-12, 2, 11), (0, -5, 14), (13, 2, 10)):
                c.create_oval(x + dx - r, y + dy - r, x + dx + r, y + dy + r, fill="#6c757d",
                              outline="", tags=T)
            c.create_polygon(x - 2, y + 8, x + 6, y + 8, x, y + 18, x + 4, y + 18, x - 4, y + 30,
                             x - 1, y + 20, x - 5, y + 20, fill="#ffd60a", outline="", tags=T)
            c.create_text(x, y - 2, text="> <", fill="#212529", font=(self.fam, 8, "bold"), tags=T)
        else:
            gold = it["kind"] == "gold"
            ro = 17 if gold else 13
            pts = []
            for i in range(10):
                a = it["rot"] + i * math.pi / 5 - math.pi / 2
                r = ro if i % 2 == 0 else ro * 0.45
                pts += [x + math.cos(a) * r, y + math.sin(a) * r]
            if gold:
                c.create_oval(x - 24, y - 24, x + 24, y + 24, fill="#ffb703", stipple="gray25",
                              outline="", tags=T)
            c.create_polygon(pts, fill="#ffb703" if gold else "#ffe066",
                             outline="#fb8500" if gold else "#f4a261", width=2, tags=T)

    def draw_tux(self, tx):
        c, T = self.canvas, ("dyn",)
        x = tx["x"]
        bob = abs(math.sin(tx["t"] * 0.25)) * 4
        lean = math.sin(tx["t"] * 0.25) * 4
        y = GROUND - bob
        c.create_oval(x - 16, GROUND + 1, x - 2, GROUND + 7, fill="#f8961e", outline="", tags=T)
        c.create_oval(x + 2, GROUND + 1, x + 16, GROUND + 7, fill="#f8961e", outline="", tags=T)
        c.create_oval(x - 24 + lean, y - 70, x + 24 + lean, y + 2, fill="#1b1b1b", outline="", tags=T)
        c.create_oval(x - 16 + lean, y - 50, x + 16 + lean, y, fill="#fafafa", outline="", tags=T)
        c.create_oval(x - 16 + lean, y - 92, x + 16 + lean, y - 60, fill="#1b1b1b", outline="", tags=T)
        for ex in (-6, 6):
            c.create_oval(x + ex - 5 + lean, y - 84, x + ex + 5 + lean, y - 72, fill="#ffffff",
                          outline="", tags=T)
            c.create_oval(x + ex - 1 + lean, y - 80, x + ex + 3 + lean, y - 75, fill="#000000",
                          outline="", tags=T)
        c.create_polygon(x - 7 + lean, y - 70, x + 7 + lean, y - 70, x + 12 + lean, y - 64,
                         x + lean, y - 60, fill="#f8961e", outline="", tags=T)
        wave = math.sin(tx["t"] * 0.4) * 12
        c.create_line(x + 20 + lean, y - 45, x + 34 + lean, y - 58 - wave, fill="#1b1b1b",
                      width=7, capstyle="round", tags=T)

    def draw_mochi(self):
        c, T, m = self.canvas, ("dyn",), self.m
        name, hue, sat, val = COLORS[self.color_idx]
        if self.disco > 0:
            hue = (self.t * 0.35) % 1
        body = hsv(hue, sat, val)
        edge = hsv(hue, sat + 0.25, val - 0.4)
        s = m["s"]
        breathe = 0.02 * math.sin(self.t * 2.4) if m["on_ground"] else 0
        sy = 1 - s + breathe
        sx = 1 + s * 0.7 - breathe * 0.5
        if m["sleeping"]:
            sy *= 0.88
            sx *= 1.06
        x, base = m["x"], m["y"]
        cx, cy = x, base - R * sy

        # shadow
        lift = clamp((GROUND - base) / 300, 0, 0.8)
        sw = R * sx * (1 - lift) * 1.05
        c.create_oval(x - sw, GROUND - 5, x + sw, GROUND + 7, fill="#000000", stipple="gray25",
                      outline="", tags=T)

        # body
        wob_amp = 0.06 if self.disco > 0 else 0.025
        pts = []
        for i in range(28):
            a = 2 * math.pi * i / 28
            wob = 1 + wob_amp * math.sin(3 * a + self.t * 4)
            px = cx + math.cos(a) * R * sx * wob
            py = cy + math.sin(a) * R * sy * wob * (1.0 if math.sin(a) < 0 else 0.92)
            pts += [px, min(py, base)]
        c.create_polygon(pts, fill=body, outline=edge, width=3, smooth=True, tags=T)
        c.create_oval(cx - R * 0.55 * sx, cy - R * 0.72 * sy, cx - R * 0.2 * sx, cy - R * 0.5 * sy,
                      fill=mix(body, "#ffffff", 0.6), outline="", tags=T)

        # expression
        if m["dizzy"] > 0:
            expr = "dizzy"
        elif m["sleeping"]:
            expr = "sleep"
        elif m["eating"] > 0:
            expr = "eat"
        elif m["dragged"]:
            expr = "surprised"
        elif m["happy"] > 0 or self.disco > 0 or (self.game and self.game["ended"] > 0):
            expr = "happy"
        elif self.food_lvl < 25 or self.fun < 20:
            expr = "sad"
        else:
            expr = "normal"

        ex_off, ey = R * 0.36 * sx, cy - R * 0.12 * sy
        mouth_y = cy + R * 0.22 * sy
        ink = "#2b2d42"

        # where to look
        lx, ly = self.mouse
        if self.game and self.game["items"]:
            it = min(self.game["items"], key=lambda i: math.hypot(i["x"] - cx, i["y"] - cy))
            lx, ly = it["x"], it["y"]
        elif self.food:
            lx, ly = self.food[0]["x"], self.food[0]["y"]
        elif self.ball:
            lx, ly = self.ball["x"], self.ball["y"]
        elif self.tux:
            lx, ly = self.tux["x"], GROUND - 60

        # cheeks
        blush = mix(body, "#ff5d8f", 0.55 if expr in ("happy", "surprised") else 0.35)
        for sgn in (-1, 1):
            bx = cx + sgn * R * 0.58 * sx
            c.create_oval(bx - 10, mouth_y - 9, bx + 10, mouth_y + 1, fill=blush, outline="", tags=T)

        for sgn in (-1, 1):
            ex = cx + sgn * ex_off
            if expr == "dizzy":
                for d in (-1, 1):
                    c.create_line(ex - 7, ey - 7 * d, ex + 7, ey + 7 * d, fill=ink, width=3, tags=T)
            elif expr in ("sleep",):
                c.create_arc(ex - 9, ey - 8, ex + 9, ey + 6, start=200, extent=140, style="arc",
                             outline=ink, width=3, tags=T)
            elif expr in ("happy", "eat"):
                c.create_arc(ex - 9, ey - 4, ex + 9, ey + 12, start=20, extent=140, style="arc",
                             outline=ink, width=3, tags=T)
            else:
                big = 1.25 if expr == "surprised" else 1.0
                ew, eh = 11 * big, 13 * big
                if m["blink"] > 0:
                    c.create_line(ex - ew, ey, ex + ew, ey, fill=ink, width=3, tags=T)
                    continue
                c.create_oval(ex - ew, ey - eh, ex + ew, ey + eh, fill="#ffffff", outline=ink,
                              width=2, tags=T)
                dx, dy = lx - ex, ly - ey
                dist = math.hypot(dx, dy) or 1
                k = min(dist / 60, 1) * 4.5
                px, py = ex + dx / dist * k, ey + dy / dist * k
                pr = 5 if expr == "surprised" else 6.5
                c.create_oval(px - pr, py - pr, px + pr, py + pr, fill=ink, outline="", tags=T)
                c.create_oval(px - pr * 0.2 - 2, py - pr * 0.6 - 2, px - pr * 0.2 + 2,
                              py - pr * 0.6 + 2, fill="#ffffff", outline="", tags=T)
                if expr == "sad":
                    c.create_line(ex - 9, ey - eh - 4 - sgn * 3, ex + 9, ey - eh - 4 + sgn * 3,
                                  fill=ink, width=2, tags=T)

        # mouth
        if expr == "eat":
            open_ = abs(math.sin(self.t * 18)) * 9 + 3
            c.create_oval(cx - 10, mouth_y - 3, cx + 10, mouth_y + open_, fill="#6a040f",
                          outline=ink, width=2, tags=T)
        elif expr in ("surprised",):
            c.create_oval(cx - 6, mouth_y - 3, cx + 6, mouth_y + 9, fill="#6a040f", outline=ink,
                          width=2, tags=T)
        elif expr == "happy":
            c.create_arc(cx - 13, mouth_y - 12, cx + 13, mouth_y + 12, start=180, extent=180,
                         style="chord", fill="#6a040f", outline=ink, width=2, tags=T)
            c.create_oval(cx - 6, mouth_y + 3, cx + 6, mouth_y + 11, fill="#ff758f", outline="", tags=T)
        elif expr == "sad":
            c.create_arc(cx - 10, mouth_y + 1, cx + 10, mouth_y + 15, start=30, extent=120,
                         style="arc", outline=ink, width=3, tags=T)
        elif expr == "dizzy":
            pts = []
            for i in range(9):
                pts += [cx - 12 + i * 3, mouth_y + 3 + (3 if i % 2 else -3)]
            c.create_line(pts, fill=ink, width=2, smooth=True, tags=T)
        elif expr == "sleep":
            c.create_oval(cx - 4, mouth_y, cx + 4, mouth_y + 6, fill="#6a040f", outline="", tags=T)
        else:
            c.create_arc(cx - 11, mouth_y - 9, cx + 11, mouth_y + 7, start=200, extent=140,
                         style="arc", outline=ink, width=3, tags=T)

        if expr == "dizzy":
            for i in range(3):
                a = self.t * 5 + i * 2.1
                c.create_text(cx + math.cos(a) * 40, cy - R * sy - 8 + math.sin(a) * 9,
                              text="★", fill="#ffd166", font=(self.fam, 14, "bold"), tags=T)
        if self.disco > 0:  # sunglasses, obviously
            c.create_rectangle(cx - ex_off - 15, ey - 9, cx - ex_off + 15, ey + 9, fill="#111111",
                               outline="", tags=T)
            c.create_rectangle(cx + ex_off - 15, ey - 9, cx + ex_off + 15, ey + 9, fill="#111111",
                               outline="", tags=T)
            c.create_line(cx - ex_off + 15, ey - 4, cx + ex_off - 15, ey - 4, fill="#111111",
                          width=3, tags=T)
            c.create_line(cx - ex_off - 9, ey - 5, cx - ex_off - 3, ey - 5, fill="#ffffff",
                          width=2, tags=T)

    def draw_bubble(self, text, x, y):
        c, T = self.canvas, ("dyn",)
        fnt = (self.fam, 12, "bold")
        f = tkfont.Font(root=self.root, family=self.fam, size=12, weight="bold")
        words, lines, cur = text.split(), [], ""
        for w_ in words:
            test = (cur + " " + w_).strip()
            if f.measure(test) > 280 and cur:
                lines.append(cur)
                cur = w_
            else:
                cur = test
        lines.append(cur)
        lh = f.metrics("linespace")
        bw = max(f.measure(l) for l in lines) + 28
        bh = lh * len(lines) + 18
        bx = clamp(x - bw / 2, 8, W - bw - 8)
        by = y - bh
        if by < 56:  # no room above Mochi: pop the bubble out to the side instead
            by = clamp(y + 20, 56, H - bh - 10)
            bx = x + R + 14 if x + R + 14 + bw < W - 8 else x - R - 14 - bw
            bx = clamp(bx, 8, W - bw - 8)
        r = 14
        x0, y0, x1, y1 = bx, by, bx + bw, by + bh
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1,
               x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        tail_x = clamp(x, x0 + 20, x1 - 20)
        if y1 < y + 20:
            c.create_polygon(tail_x - 9, y1 - 2, tail_x + 9, y1 - 2, tail_x + 2, y1 + 14,
                             fill="#ffffff", outline="#2b2d42", width=2, tags=T)
        c.create_polygon(pts, fill="#ffffff", outline="#2b2d42", width=2, smooth=True, tags=T)
        if y1 < y + 20:
            c.create_line(tail_x - 7, y1, tail_x + 7, y1, fill="#ffffff", width=3, tags=T)
        c.create_text(bx + bw / 2, by + bh / 2, text="\n".join(lines), fill="#2b2d42", font=fnt,
                      justify="center", tags=T)

    def draw_hud(self):
        c, T = self.canvas, ("dyn",)
        night = self.period == "night" or self.m["sleeping"] or self.disco > 0
        fg = "#ffffff" if night else "#1d3557"
        age = time.time() - self.born
        age_txt = ("%d days" % (age // 86400)) if age >= 86400 else (
            "%d h" % (age // 3600) if age >= 3600 else "%d min" % (age // 60))
        c.create_text(16, 14, text=self.name, anchor="nw", fill=fg, font=(self.fam, 20, "bold"), tags=T)
        c.create_text(17, 46, text="age %s  ·  %d pets  ·  best %d ★" % (age_txt, self.pets, self.best),
                      anchor="nw", fill=fg, font=(self.fam, 10), tags=T)
        x0 = W - 210
        for i, (label, v) in enumerate((("Food", self.food_lvl), ("Fun", self.fun),
                                        ("Energy", self.energy))):
            y = 16 + i * 22
            col = "#06d6a0" if v > 60 else "#ffd166" if v > 30 else "#ef476f"
            c.create_text(x0 - 8, y + 6, text=label, anchor="e", fill=fg, font=(self.fam, 10, "bold"), tags=T)
            c.create_rectangle(x0, y, x0 + 190, y + 13, fill="#ffffff", outline="#1d3557",
                               width=1, stipple="gray50", tags=T)
            if v > 1:
                c.create_rectangle(x0 + 1, y + 1, x0 + 1 + 188 * v / 100, y + 12, fill=col,
                                   outline="", tags=T)
        g = self.game
        if g:
            txt = "★ %d      %ds" % (g["score"], max(0, math.ceil(g["time"])))
            c.create_text(W / 2 + 2, 28, text=txt, fill="#3d2c00", font=(self.fam, 22, "bold"), tags=T)
            c.create_text(W / 2, 26, text=txt, fill="#ffe066", font=(self.fam, 22, "bold"), tags=T)


def main():
    root = tk.Tk()
    MochiApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
