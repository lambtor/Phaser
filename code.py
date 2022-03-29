import board
import digitalio
import neopixel
import audioio
import audiocore
# from audiocore import WaveFile
from adafruit_debouncer import Debouncer
import time

# this script is meant to be used with qt py rp2040
# this is for stemma speaker board. drop wav file on main directory of board
# from adafruit_circuitplayground import cp
# OK OMFG circuitpython has a max of 88 characters per line of code
# -------------------------------------------------------------------------------------

# User config settings - these should be set once for program
# to behave for your hardware
# true or false here. False means program is for a type 2
IS_TYPE_ONE_PHASER = False
SETTING_LED_PIN = board.A2
BEAM_LED_PIN = board.A1
# if using stemma speaker board, this MIGHT use pin SDA1?
# only 3 pins connected when using stemma speaker board, so maybez
SOUND_OUT_PIN = board.A0
SETTING_SND_FILE = "adjust.wav"
BTN_LEFT = board.TX
BTN_RIGHT = board.RX
BTN_TRIGGER = board.BUTTON

# --------
mnIntensitySetting = 0
# this needs to be 1 more than the total number of actual setting LEDs you have
if IS_TYPE_ONE_PHASER:
    mnSettingLEDMax = 9
else:
    mnSettingLEDMax = 17
mnBeamLEDCount = 1
moAudioPlay = audioio.AudioOut(SOUND_OUT_PIN)
moSettingSoundFile = open(SETTING_SND_FILE, "rb")
moSettingSound = audiocore.WaveFile(moSettingSoundFile)

moRGBRed = (128, 0, 0)
moRGBBlack = (0, 0, 0)
moRGBStrength = 128

# all comments are done via pound sign,
# and MUST have a space immediately after the pound sign - this is some vb6 shit.
# gtfo with your variable types! this is PYTHON! everything's interpolated!
# you're probably gonna want to use named pins for any declarations
# long-term: left handed mode that can be toggled on/off via both setting button press?
# mpinBoardLed = digitalio.DigitalInOut(board.LED)
# board.BUTTON
mpinBoardLed = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.3, auto_write=True)
# mpinBoardLed = neopixel.NeoPixel(board.NEOPIXEL, 1)
# mpinBoardLed.brightness = 0.3
mpinBoardLed.fill((112, 128, 0))
mpinBoardLed.show()

# 6-8 status leds in a single row, or 16 split across 2 rows
# setting lowest value is 0, max is count of setting LEDs?
moPixelRow = neopixel.NeoPixel(SETTING_LED_PIN, mnSettingLEDMax - 1)
moPixelRow.brightness = 0.3
moPixelRow.auto_write = False
moPixelRow.fill(moRGBBlack)
moPixelRow.show()

# a laser pointer driven by 5v, with 1 neopixel on each side.
# these are going to be mounted on a custom pcb with a hole to fit pointer
moBeamSet = neopixel.NeoPixel(BEAM_LED_PIN, mnBeamLEDCount)
moBeamSet.brightness = 0.5
moBeamSet.auto_write = True


def ButtonRead(pin):
    io = digitalio.DigitalInOut(pin)
    io.direction = digitalio.Direction.INPUT
    io.pull = digitalio.Pull.UP
    return lambda: io.value


def SettingDecrease(nAmount):
    global mnIntensitySetting
    if mnIntensitySetting > 0:
        mnIntensitySetting -= nAmount
    UpdateSetting()


def SettingIncrease(nAmount):
    global mnSettingLEDMax
    global mnIntensitySetting
    if mnIntensitySetting < (mnSettingLEDMax - 1):
        mnIntensitySetting += nAmount
    UpdateSetting()


# settings with 2 bars, bottom bar goes unlit to full green
# then from full green, for 8-15, this bar fades green to orange
# while top bar climbs up red. at 15, bottom bar is full orange
# and top bar is full red.
# need way to set phaser to overload from setting 15 (hold up btn 5 sec?)
# need way to set phaser to autofire (wesley) from zero (hold down btn 3 sec?)
# warning shot mode, set 1 LED pink & max sound min beam brightness

def UpdateSetting():
    global mnIntensitySetting
    global moPixelRow
    global moRGBRed
    global moRGBBlack
    global moRGBStrength
    global mnSettingLEDMax
    if mnIntensitySetting == 0:
        # moPixelRow.fill(moRGBBlack)
        # moPixelRow.show()
        WarningShotMode()
        return

    # canon behavior for settings with 8 leds

    # this will be 0 to number of setting LEDs - 1
    for nIterator in range(mnSettingLEDMax - 1):
        if nIterator > 7:
            if mnIntensitySetting >= 8:
                if mnIntensitySetting > nIterator:
                    moPixelRow[nIterator] = moRGBRed
                else:
                    moPixelRow[nIterator] = moRGBBlack
        else:
            if mnIntensitySetting > 8:
                # if mnIntensitySetting >= nIterator:
                nRed = int((mnIntensitySetting - 7) * 16)
                nGreen = int(moRGBStrength - (8 * (mnIntensitySetting - 7)))
                moPixelRow[nIterator] = (nRed, nGreen, 0)
            else:
                if nIterator < mnIntensitySetting:
                    # set any LED at or below current setting as green
                    moPixelRow[nIterator] = (0, moRGBStrength, 0)
                else:
                    moPixelRow[nIterator] = moRGBBlack
    moPixelRow.show()

def WarningShotMode():
    moPixelRow.fill(moRGBBlack)
    moPixelRow[0] = (255, 64, 64)
    moPixelRow.show()

def DisableWarningShotMode():
    moPixelRow.fill(moRGBBlack)
    moPixelRow.show()

def OVERLOADMODE():
    pass

def DisableOverload():
    pass

# sound effect output via mp3 or wav playback to a speaker.
# firing sound mapped to trigger press. split between "startup" and "active" sounds
# loop "active" for as long as trigger pressed
# "setting" sound plays on other 2 buttons
# need to convey charging state via setting LED row(s)
btn1 = Debouncer(ButtonRead(BTN_LEFT))
btn2 = Debouncer(ButtonRead(BTN_RIGHT))
# btnTrigger = Debouncer(ButtonRead(BTN_TRIGGER))
btn1Down = 0
btn2Down = 0

while True:
    btn1.update()
    btn2.update()
    # mnIntensitySetting
    # btnTrigger.update()

    # need way to determine if both setting buttons held down for 3 seconds,
    # to invoke NON-CANON settings interface
    # while not btn1.value & not btn2.value:
    # pass

    # handle each button's actions. btn1 needs different between long and short press
    if btn1.fell:
        btn1Down = time.monotonic()
    if btn1.rose:
        nBtn1DownTime = time.monotonic() - btn1Down
        if nBtn1DownTime < 2:
            DisableWarningShotMode()
            DisableOverload()
            # decrement setting if under 2 sec press
            moAudioPlay.play(moSettingSound)
            while moAudioPlay.playing:
                pass
            # cp.play_file("adjust.wav")
            SettingDecrease(1)
            # print(mnIntensitySetting)
        else:
            if mnIntensitySetting == 0:
                WarningShotMode()

    if btn2.fell:
        btn2Down = time.monotonic()
    if btn2.rose:
        nBtn2DownTime = time.monotonic() - btn2Down
        if nBtn2DownTime < 2:
            DisableOverload()
            # probably want to not do anything if already at max or min setting?
            # or different sound for NO!
            # decrement setting if under 2 sec press
            # Plays the sample once when loop=False,
            # and continuously when loop=True. Does not block
            moAudioPlay.play(moSettingSound)
            while moAudioPlay.playing:
                pass
            # cp.play_file("adjust.wav")
            SettingIncrease(1)
            # print(mnIntensitySetting)
        else:
            if mnIntensitySetting == 15:
                OVERLOADMODE()
