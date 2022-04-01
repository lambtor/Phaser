import board
import digitalio
import neopixel
# import audioio
import audiocore
# from audiocore import WaveFile
from adafruit_debouncer import Debouncer
import time

# this script is meant to be used with qt py rp2040
# this is for stemma speaker board. drop wav file on main directory of board
import audiobusio
# OK OMFG circuitpython has a max of 88 characters per line of code
# -------------------------------------------------------------------------------------

# User config settings - these should be set once for program
# to behave for your hardware
# true or false here. False means program is for a type 2
# A3 is for laser itself. TX might need to be used for beam neopixels.
IS_TYPE_ONE_PHASER = False
SETTING_LED_PIN = board.A1
BEAM_LED_PIN = board.A3
# if using stemma speaker board, this MIGHT use pin SDA1?
# only 3 pins connected when using stemma speaker board, so maybez
SETTING_SND_FILE = "adjust.wav"
BTN_LEFT = board.TX
BTN_RIGHT = board.RX
BTN_TRIGGER = board.BUTTON
# BUTTON

# --------
# current active device settings - do these need to persist across power cycles?

mnIntensitySetting = 0
# this needs to be 1 more than the total number of actual setting LEDs you have
if IS_TYPE_ONE_PHASER:
    mnSettingLEDMax = 9
else:
    mnSettingLEDMax = 17
mnBeamLEDCount = 1

# try:
#    from audioio import AudioOut
# except ImportError:
#    try:
#        from audiopwmio import PWMAudioOut as AudioOut
#    except ImportError:
#        pass
moI2SAudio = audiobusio.I2SOut(board.SDA, board.SCL, board.SCK)

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
moSettingRow = neopixel.NeoPixel(SETTING_LED_PIN, mnSettingLEDMax - 1)
moSettingRow.brightness = 0.1
moSettingRow.auto_write = False

# a laser pointer driven by 5v, with 1 neopixel on each side.
# these are going to be mounted on a custom pcb with a hole to fit pointer
moBeamSet = neopixel.NeoPixel(BEAM_LED_PIN, mnBeamLEDCount)
moBeamSet.brightness = 0.5
moBeamSet.auto_write = True

mbIsCharging = False
mnChargingFrame = 0
mnChargingFrameDelay = 750
mnChargingLastTime = 0

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
    global moSettingRow
    global moRGBRed
    global moRGBBlack
    global moRGBStrength
    global mnSettingLEDMax
    global IS_TYPE_ONE_PHASER
    global mbIsCharging

    if mbIsCharging:
        return

    if mnIntensitySetting == 0:
        # moSettingRow.fill(moRGBBlack)
        # moSettingRow.show()
        WarningShotMode()
        return

    # canon behavior for settings with 8 leds
    if IS_TYPE_ONE_PHASER:
        # transition entire row from green to red as it marches from 0-7
        for nIterator in range(mnSettingLEDMax - 1):
            # 0 128 0 to 128 0 0
            nRed = int((mnIntensitySetting - 1) * 16)
            nGreen = 128 - nRed
            moSettingRow[nIterator] = (nRed, nGreen, 0)
    else:
        # this will be 0 to number of setting LEDs - 1
        for nIterator in range(mnSettingLEDMax - 1):
            if nIterator > 7:
                if mnIntensitySetting >= 8:
                    if mnIntensitySetting > nIterator:
                        moSettingRow[nIterator] = moRGBRed
                    else:
                        moSettingRow[nIterator] = moRGBBlack
            else:
                if mnIntensitySetting > 8:
                    # if mnIntensitySetting >= nIterator:
                    nRed = int((mnIntensitySetting - 7) * 16)
                    nGreen = int(moRGBStrength - (8 * (mnIntensitySetting - 7)))
                    moSettingRow[nIterator] = (nRed, nGreen, 0)
                else:
                    if nIterator < mnIntensitySetting:
                        # set any LED at or below current setting as green
                        moSettingRow[nIterator] = (0, moRGBStrength, 0)
                    else:
                        moSettingRow[nIterator] = moRGBBlack
    moSettingRow.show()

def WarningShotMode():
    moSettingRow.fill(moRGBBlack)
    moSettingRow[0] = (255, 64, 64)
    moSettingRow.show()

def DisableWarningShotMode():
    moSettingRow.fill(moRGBBlack)
    moSettingRow.show()

def RunOverloadMode():
    pass

def DisableOverload():
    pass

def RunChargingMode():
    global mbIsCharging
    global mnChargingFrame
    global mnChargingFrameDelay
    global moSettingRow
    global moRGBStrength
    global mnSettingLEDMax
    global mnChargingLastTime
    nFadeFactor = 2
    nBattPercentage = 70
    # nMaxFrames = mnSettingLEDMax * 2
    nCurrentTime = time.monotonic()

    if (nCurrentTime - mnChargingLastTime) < mnChargingFrameDelay:
        return

    if mbIsCharging:
        # set brightness for settings chain to 0.4
        # to allow brightness for animation
        if moSettingRow.brightness != 0.4:
            moSettingRow.brightness = 0.4

        if mnChargingFrame > 0 and mnChargingFrame <= mnSettingLEDMax:
            # draw current "frame" on settings pixels
            for nIterator in range(mnSettingLEDMax - 1):
                if nIterator == mnChargingFrame:
                    moSettingRow[nIterator] = (0, 0, moRGBStrength)
                elif (mnChargingFrame - nIterator) == 1:
                    moSettingRow[nIterator] = (0, 0, int(moRGBStrength / nFadeFactor))
                elif (nIterator - mnChargingFrame) == 1:
                    moSettingRow[nIterator] = (0, 0, int(moRGBStrength / nFadeFactor))
                elif nIterator < int(nBattPercentage / (100 / (mnSettingLEDMax - 1))):
                    nBlueStrength = int((moRGBStrength / nFadeFactor) / nFadeFactor)
                    moSettingRow[nIterator] = (0, 0, nBlueStrength)
            moSettingRow.show()

        mnChargingFrame += 1
    else:
        if moSettingRow.brightness != 0.1:
            moSettingRow.brightness = 0.1

# sound effect output via mp3 or wav playback to a speaker.
# firing sound mapped to trigger press. split between "startup" and "active" sounds
# loop "active" for as long as trigger pressed
# "setting" sound plays on other 2 buttons
# need to convey charging state via setting LED row(s)
btn1 = Debouncer(ButtonRead(BTN_LEFT))
btn2 = Debouncer(ButtonRead(BTN_RIGHT))
btnTrigger = Debouncer(ButtonRead(BTN_TRIGGER))
btn1Down = 0
btn2Down = 0
btnTrigger = 0
# boot this into warning mode initially
WarningShotMode()

# arduino equivalent of loop()
while True:
    btn1.update()
    btn2.update()
    # mnIntensitySetting
    btnTrigger.update()

    # need way to determine if both setting buttons held down for 3 seconds,
    # to invoke NON-CANON settings interface
    # while not btn1.value & not btn2.value:
    # pass
    if btnTrigger.fell:
        btnTrigger = time.monotonic()
    # to determine if ALL have been held down for 2 seconds or more,
    # check if NOW - MAX(all 3 button DOWN timestamps) > 2

    # handle each button's actions. btn1 needs different between long and short press
    if btn1.fell:
        btn1Down = time.monotonic()
    if btn1.rose:
        nBtn1DownTime = time.monotonic() - btn1Down
        if nBtn1DownTime < 2:
            DisableWarningShotMode()
            DisableOverload()
            # decrement setting if under 2 sec press
            # moAudioPlay.play(moSettingSound)
            # while moAudioPlay.playing:
            #   pass
            moI2SAudio.play(moSettingSound)
            # while moI2SAudio.playing():
            #    pass
            SettingDecrease(1)
            # print(mnIntensitySetting)
        else:
            pass
            # if mnIntensitySetting == 0:
            #    WarningShotMode()

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
            # moAudioPlay.play(moSettingSound)
            # while moAudioPlay.playing:
            #    pass
            moI2SAudio.play(moSettingSound)
            # while moI2SAudio.playing:
            #    pass
            SettingIncrease(1)
            # print(mnIntensitySetting)
        else:
            if mnIntensitySetting == 15:
                RunOverloadMode()

    RunChargingMode()
