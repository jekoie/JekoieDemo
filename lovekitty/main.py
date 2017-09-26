#coding:utf-8
from __future__ import division
from asciimatics.effects import *
from asciimatics.renderers import *
from asciimatics.particles import  *
from asciimatics.sprites import Arrow
from asciimatics.exceptions import *
from asciimatics.widgets import *
from asciimatics.scene import Scene
from asciimatics.screen import Screen
from asciimatics.paths import Path
from random import randint, choice
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

jett_data = {
    'id': '--can not tell you--',
    'nickname': u'单色凌',
    'desc': 'Right here waiting for you.',
    'self': u'男 0岁 九月廿七 属羊 天蝎座 未知血型',
    'home': u'--',
    'addr': u'--',
    'phone': '1314520',
    'page': '--',
    'mail': '--',
    'code': '520',
    'film':  u'幼儿园',
    'school': u'幼儿园小学',
    'job': u'幼儿园小朋友',
    'career': u'学生',
    'edu': u'小学及以下'
}

# Tree definition
tree = r"""
       ${3,1}*
      / \
     /${1}o${2}  \
    /_   _\
     /   \${4}b
    /     \
   /   ${1}o${2}   \
  /__     __\
  ${1}d${2} / ${4}o${2}   \
   /       \
  / ${4}o     ${1}o${2}.\
 /___________\
      ${3}|||
      ${3}|||
""", r"""
       ${3}*
      / \
     /${1}o${2}  \
    /_   _\
     /   \${4}b
    /     \
   /   ${1}o${2}   \
  /__     __\
  ${1}d${2} / ${4}o${2}   \
   /       \
  / ${4}o     ${1}o${2} \
 /___________\
      ${3}|||
      ${3}|||
"""

def _speak(screen, text, pos, start):
    return Print(screen, SpeechBubble(text, "L", uni=screen.unicode_aware),
                 x=pos[0]+4, y=pos[1]-4, colour=Screen.COLOUR_GREEN, clear=True,
                 start_frame=start, stop_frame=start+50)

class ProfileFrame(Frame):
    def __init__(self, screen):
        Frame.__init__(self, screen, screen.height, screen.width*2//3, data=jett_data, title='About Jekoie')

        layout = Layout([1, 18, 1])
        self.add_layout(layout)
        layout.add_widget( Text(u'账号:', 'id',  self._on_change), 1 )
        layout.add_widget( Text(u'昵称:', 'nickname', self._on_change),  1)
        layout.add_widget( Text(u'个人说名:', 'desc', self._on_change), 1)

        layout.add_widget( Divider(height=2), 1)
        layout.add_widget( Text(u'个人', 'self', self._on_change), 1 )
        layout.add_widget(Text(u'故乡', 'home', self._on_change), 1)
        layout.add_widget(Text(u'所在地', 'addr', self._on_change), 1)

        layout.add_widget( Divider(height=2), 1)
        layout.add_widget( Text(u'电话', 'phone', self._on_change), 1 )
        layout.add_widget(Text(u'主页', 'page', self._on_change), 1)
        layout.add_widget(Text(u'邮箱', 'mail', self._on_change), 1)
        layout.add_widget(Text(u'邮编', 'code', self._on_change), 1)

        layout.add_widget(Divider(height=2), 1)
        layout.add_widget(Text(u'公司', 'film', self._on_change), 1)
        layout.add_widget(Text(u'学校', 'school', self._on_change), 1)
        layout.add_widget(Text(u'职位', 'job', self._on_change), 1)
        layout.add_widget(Text(u'职业', 'career', self._on_change), 1)
        layout.add_widget(Text(u'学历', 'edu', self._on_change), 1)

        layout.add_widget(Divider(height=1), 1)
        layout2 = Layout([1, 1 , 1])
        self.add_layout(layout2)
        layout2.add_widget(Button(u'Deny', self._deny), 0  )
        layout2.add_widget(Button(u'Watch', self._watch), 1 )
        layout2.add_widget(Button(u'Invite', self._invite), 2)

        self.add_effect(Matrix(self._screen) )
        self.fix()

    def _on_change(self):
        pass

    def _deny(self):
        raise  NextScene('Begin')

    def _invite(self):
        raise NextScene('Begin')

    def _watch(self):
        raise NextScene('Begin')

def kitty(screen, scene):
    scenes = []
    effects = [
        ProfileFrame(screen),
    ]
    scenes.append(Scene(effects, -1, name='Main'))

   # scene
    cell = ColourImageFile(screen, 'img/4.jpg', screen.height)
    effects = [
        RandomNoise(screen, signal=cell),
        Print(screen, Rainbow(screen, FigletText('Kitty', font='banner')), screen.height - 6, start_frame= 200, bg=0 ),
        Print(screen, Rainbow(screen, FigletText('Kitty', font='banner')), screen.height - 6, start_frame= 200, bg=0)
    ]
    scenes.append(Scene(effects, 380, name='Begin'))

   # scene
    effects = [
        ShootScreen(screen , screen.width//2, screen.height//2, 100)
    ]
    scenes.append(Scene(effects, 60, clear=False))

    #scene
    centre = ((screen.width // 2) - 20 , (screen.height // 2) - 3)
    podium = (8, 5)
    path = Path()
    path.jump_to(-20, centre[1])
    path.move_straight_to(centre[0], centre[1], 10)
    path.wait(30)
    path.move_straight_to(podium[0], podium[1], 10)
    path.wait(180)

    effects = [
        Arrow(screen, path, colour=Screen.COLOUR_GREEN),
        Snow(screen),
        Rain(screen, 340),
        Print(screen, StaticRenderer(images=tree), screen.height-15, screen.width-15, colour=Screen.COLOUR_GREEN),
        _speak(screen, u'This program write for the girl that i like, hope she will be happy!', centre, 30),
        _speak(screen, u'I like her at the first sight when i met her last year.', podium, 110),
        _speak(screen, u'I really like to chat with her, but afraid that she will be boring. ', podium, 180),
        Cycle(screen, Rainbow(screen, FigletText('Lovely', 'banner') ), screen.height//2 -6, start_frame=220 ),
        Cycle(screen, Rainbow(screen, FigletText('Kitty', 'banner') ), screen.height//2+1, start_frame=220)
    ]
    scenes.append(Scene(effects, duration=340 ))

   #scene
    cell = ColourImageFile(screen, 'img/10.jpg', screen.height, uni=screen.unicode_aware, dither=screen.unicode_aware)
    effects = [
        Wipe(screen),
        Print(screen, cell, 0),
        Stars(screen, screen.height+screen.width)
    ]

    # for _ in  range(20):
    #     effects.append(
    #         Explosion(screen, randint(0, screen.width), randint(screen.height//8, screen.height*3//4), randint(20, 150) )
    #     )

    scenes.append(Scene(effects, 150, clear=False))

    #scene
    cell = ColourImageFile(screen, 'img/3.jpg', screen.height, uni=screen.unicode_aware, dither=screen.unicode_aware)
    effects = [
        DropScreen(screen, 100),
        BannerText(screen, cell, 0, Screen.COLOUR_YELLOW),
        Snow(screen)
    ]

    for _ in range(120):
        fireworks = [
            (PalmFirework, randint(25, 35) ),
            (RingFirework, randint(25, 30) ),
            (StarFirework, randint(30, 35) ),
            (SerpentFirework, randint(28, 35))
        ]
        firework, lifetime = choice(fireworks)
        effects.append(
            firework(screen, randint(0, screen.width), randint(screen.height//8, screen.height*3//4), lifetime, start_frame=randint(20, 250) )
        )
    scenes.append(Scene(effects, 280, clear=False))

    #scene
    cell = ColourImageFile(screen, 'img/1.jpg', screen.height, uni=screen.unicode_aware, dither=screen.unicode_aware)
    effects = [
        Print(screen, cell, 0, speed=1),
        Scroll(screen, rate=10),
        Rain(screen, 200)
    ]
    scenes.append(Scene(effects, 180) )

    #scene
    text = Figlet(font="banner", width=200).renderText("Pretty Girl")
    width = max([len(x) for x in text.split("\n")])
    effects = [
        Print(screen,  Fire(screen.height, 80, text, 0.4, 40, screen.colours), 0, speed=1),
        Print(screen, FigletText("Pretty Girl", 'banner'), screen.height - 9, x=(screen.width - width) // 2 + 1, colour=0, bg=0, speed=1 ),
        Print(screen, FigletText("Pretty Girl", 'banner'), screen.height - 9, x=(screen.width - width) // 2 + 1, colour=7, bg=7, speed=1)
    ]
    scenes.append(Scene(effects, 80) )

    #scene
    effects = [
        Print(screen, Plasma(screen.height, screen.width, screen.colours), 0, speed=1, start_frame=50),
        Print(screen, Rainbow(screen, FigletText('Thats All') ), screen.height//2-5 ),
        Print(screen, Rainbow(screen, FigletText('My Kitty!')), screen.height // 2 + 5),
    ]
    scenes.append(Scene(effects, -1) )

    screen.play(scenes, stop_on_resize=True, start_scene=scene)

last_scene = None
while True:
    try:
        Screen.wrapper(kitty, catch_interrupt=False,arguments=[last_scene])
        sys.exit()
    except ResizeScreenError as e:
        last_scene = e.scene