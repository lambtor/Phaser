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
IS_TYPE_ONE_PHASER = True
SETTING_LED_PIN = board.A1
BEAM_LED_PIN = board.A0
# if using stemma speaker board, this MIGHT use pin SDA1?
# only 3 pins connected when using stemma speaker board, so maybez
SETTING_SND_FILE = "adjust.wav"
FIRELOOP_SND_FILE = "firingloop.wav"
FIREWARM_SND_FILE = "warmup.wav"
BTN_LEFT = board.TX
BTN_RIGHT = board.RX
BTN_TRIGGER = board.BUTTON
# number from 0-1 (you'd never want 1, as that'd be ALWAYS OFF
BEAM_FLICKER_RATE = 0.2
BEAM_FPS = 60

# --------
# current active device settings - do these need to persist across power cycles?

mnIntensitySetting = 0
# this needs to be 1 more than the total number of actual setting LEDs you have
if IS_TYPE_ONE_PHASER:
    mnSettingLEDMax = 9
else:
    mnSettingLEDMax = 17
mnBeamLEDCount = 4

# try:
#    from audioio import AudioOut
# except ImportError:
#    try:
#        from audiopwmio import PWMAudioOut as AudioOut
#    except ImportError:
#        pass
moI2SAudio = audiobusio.I2SOut(board.SDA, board.SCL, board.SCK)

moSettingSoundFile = open(SETTING_SND_FILE, "rb")
moFiringLoopFile = open(FIRELOOP_SND_FILE, "rb")
moFireWarmFile = open(FIREWARM_SND_FILE, "rb")
moSettingSnd = audiocore.WaveFile(moSettingSoundFile)
moFireLoopSnd = audiocore.WaveFile(moFiringLoopFile)
moFireWarmSnd = audiocore.WaveFile(moFireWarmFile)
mnFireWarmSndLength = 2.0
mnFireWarmStep = 0

moRGBRed = (128, 0, 0)
moRGBBlack = (0, 0, 0)
moRGBStrength = 128

# all comments are done via pound sign,
# and MUST have a space immediately after the pound sign - this is some vb6 shit.
# gtfo with your variable types! this is PYTHON! everything's interpolated!
# long-term: left handed mode that can be toggled on/off via both setting button press?
# mpinBoardLed = digitalio.DigitalInOut(board.LED)
# board.BUTTON
mpinBoardLed = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.3, auto_write=True)
# mpinBoardLed = neopixel.NeoPixel(board.NEOPIXEL, 1)
# mpinBoardLed.brightness = 0.3
mpinBoardLed.fill((112, 128, 0))
mpinBoardLed.write()

# 6-8 status leds in a single row, or 16 split across 2 rows
# setting lowest value is 0, max is count of setting LEDs?
moSettingRow = neopixel.NeoPixel(SETTING_LED_PIN, mnSettingLEDMax - 1)
moSettingRow.brightness = 0.1
moSettingRow.auto_write = False

# a laser pointer driven by 5v, with 1 neopixel on each side.
# these are going to be mounted on a custom pcb with a hole to fit pointer
moBeamRow = neopixel.NeoPixel(BEAM_LED_PIN, mnBeamLEDCount)
moBeamRow.brightness = 0.5
moBeamRow.auto_write = False

# time function returns everything as seconds.
# all comparisons for delay less than 1 second need to use decimals
mbIsCharging = False
mbInMenu = False
mbIsFiring = False
mbIsWarming = False
mnChargingFrame = 0
mnChargingFrameDelay = 0.25
mnChargingLastTime = 0
mnLastBattCheck = 0
mnBattCheckInterval = 1
mnFiringLastTime = 0

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
    global mbInMenu

    if mbIsCharging or mbInMenu:
        return

    print(mnIntensitySetting)
    if mnIntensitySetting == 0:
        # moSettingRow.fill(moRGBBlack)
        # moSettingRow.write()
        WarningShotMode()
        return

    # to-do: set intensity according to user-selected max brightness
    # update beam brightness to reflect intensity setting
    moBeamRow.brightness = (1 / (mnSettingLEDMax - mnIntensitySetting))
    moBeamRow.write()

    # canon behavior for settings with 8 leds
    if (IS_TYPE_ONE_PHASER is True):
        # transition entire row from green to red as it marches from 0-7
        for nIterator2 in range(mnSettingLEDMax - 1):
            # 0 128 0 to 128 0 0
            if nIterator2 < mnIntensitySetting:
                nRed = int((mnIntensitySetting - 1) * 16)
                nGreen = 128 - nRed
                moSettingRow[nIterator2] = (nRed, nGreen, 0)
            else:
                moSettingRow[nIterator2] = moRGBBlack
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
    moSettingRow.write()

def WarningShotMode():
    global moSettingRow
    moSettingRow.fill(moRGBBlack)
    moSettingRow[0] = (255, 64, 64)
    moSettingRow.write()

def DisableWarningShotMode():
    global moSettingRow
    moSettingRow.fill(moRGBBlack)
    moSettingRow.write()

def StartFiring(mbIsInit):
    global mbIsFiring
    global moBeamRow
    global mbIsWarming
    global mnFireWarmStep
    global mnFiringLastTime
    global mnFireWarmSndLength
    nFadeSteps = 4
    if not mbIsWarming and not mbIsInit:
        return
    # kick out if it's too soon to step to next frame
    if (time.monotonic() - mnFiringLastTime) < (mnFireWarmSndLength / nFadeSteps):
        return
    # fade from black up to full red - this is non-blocking
    if mnFireWarmStep < nFadeSteps:
        oRedColor = (int(255 / (nFadeSteps - mnFireWarmStep)), 0, 0)
        moBeamRow.fill(oRedColor)
        moBeamRow.write()
        mnFireWarmStep += 1
    elif mnFireWarmStep == nFadeSteps:
        oRedColor = (255, 0, 0)
        moBeamRow.fill(oRedColor)
        moBeamRow.write()
        mnFireWarmStep += 1
    # warming over, set isFiring flag on to hand over to that animation
    if mnFireWarmStep > nFadeSteps:
        mbIsWarming = False
        mnFireWarmStep = 0
        mbIsFiring = True

def RunFiring():
    global mbIsFiring
    global BEAM_FPS
    global BEAM_FLICKER_RATE
    # depending on "refresh rate" and "flicker rate" values at top,
    # occasionally turn off beam neopixels uniformly?
    if not mbIsFiring or mbInMenu is True or mbIsCharging is True:
        return

def StopFiring():
    global moBeamRow
    global mbIsFiring
    global moI2SAudio
    moBeamRow.fill(moRGBBlack)
    moBeamRow.write()
    mbIsFiring = False
    moI2SAudio.stop()

def RunOverloadMode():
    pass

def DisableOverload():
    pass

def CheckCharging():
    # if charging mode is active, run charging mode
    global mbIsCharging
    pass

def DisableCharging():
    global moSettingRow
    moSettingRow.brightness = 0.1
    moSettingRow.fill(moRGBBlack)
    moSettingRow.write()
    UpdateSetting()

def RunChargingMode():
    global mbIsCharging
    global mnChargingFrame
    global mnChargingFrameDelay
    global moSettingRow
    global moRGBStrength
    global mnSettingLEDMax
    global mnChargingLastTime
    global IS_TYPE_ONE_PHASER
    nFade = 2
    nBattPercentage = 70
    nMaxFrames = mnSettingLEDMax + 4
    nCurrentTime = time.monotonic()

    if not mbIsCharging or ((nCurrentTime - mnChargingLastTime) < mnChargingFrameDelay):
        return

    if mbIsCharging:
        # set brightness for settings chain to 0.4
        # to allow brightness for animation
        if (moSettingRow.brightness != 0.4):
            moSettingRow.brightness = 0.4

        if mnChargingFrame >= 0 and mnChargingFrame <= mnSettingLEDMax:
            # draw current "frame" on settings pixels
            for nIterator3 in range(mnSettingLEDMax - 1):
                nTemp = int(nBattPercentage / (100 / (mnSettingLEDMax - 1)))
                if nIterator3 == mnChargingFrame:
                    if nIterator3 <= nTemp:
                        moSettingRow[nIterator3] = (0, 0, moRGBStrength)
                        if not IS_TYPE_ONE_PHASER:
                            moSettingRow[nIterator3 + 8] = (0, 0, moRGBStrength)
                # elif (mnChargingFrame - nIterator3) == 1:
                #    if nIterator3 <= nTemp:
                #        moSettingRow[nIterator3] = (0, 0, int(moRGBStrength / nFade))
                # elif (nIterator3 - mnChargingFrame) == 1:
                #    if nIterator3 <= nTemp:
                #        moSettingRow[nIterator3] = (0, 0, int(moRGBStrength / nFade))
                elif nIterator3 <= int(nBattPercentage / (100 / (mnSettingLEDMax - 1))):
                    nBlueStrength = int((moRGBStrength / nFade) / nFade)
                    moSettingRow[nIterator3] = (0, 0, nBlueStrength)
                    if not IS_TYPE_ONE_PHASER:
                        moSettingRow[nIterator3 + 8] = (0, 0, moRGBStrength)
            moSettingRow.write()
        mnChargingLastTime = nCurrentTime
        mnChargingFrame += 1
        print(mnChargingFrame)
        if (mnChargingFrame > nMaxFrames):
            mnChargingFrame = 0

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
btnTriggerDown = 0
# boot this into warning mode initially
WarningShotMode()

# arduino equivalent of loop()
while True:
    btn1.update()
    btn2.update()
    btnTrigger.update()

    # run battery check once per second to determine if charging
    # if (time.monotonic() - mnLastBattCheck) > mnBattCheckInterval:
    #    CheckCharging()
    # need way to determine if both setting buttons held down for 3 seconds,
    # to invoke NON-CANON settings interface
    # while not btn1.value & not btn2.value:
    # pass
    # eventually need way to keep trigger from causing
    # firing if in a setting adj menu
    if btnTrigger.fell:
        btnTriggerDown = time.monotonic()
        # start firing sound, warmup beam leds
        if not mbIsCharging and not mbInMenu:
            moI2SAudio.play(moFireWarmSnd)
            # while moI2SAudio.playing:
            StartFiring(True)
    if btnTrigger.rose:
        btnTriggerTime = time.monotonic() - btnTriggerDown
        if not mbInMenu:
            StopFiring()
        # stop firing sound
        # if btnTriggerTime > 2:
        #    mbIsCharging = True
            # print(mbIsCharging, " charging")
        # else:
        #    mbIsCharging = False
        #    DisableCharging()
            # print(mbIsCharging, " charging")

    if mbIsWarming is True:
        StartFiring(False)
    RunFiring()

    # handle each button's actions. btn1 needs different between long and short press
    if btn1.fell:
        btn1Down = time.monotonic()
    if btn1.rose:
        nBtn1DownTime = time.monotonic() - btn1Down
        if nBtn1DownTime < 2:
            # DisableWarningShotMode()
            DisableOverload()
            # decrement setting if under 2 sec press
            # moAudioPlay.play(moSettingSnd)
            # while moAudioPlay.playing:
            #   pass
            moI2SAudio.play(moSettingSnd)
            # while moI2SAudio.playing():
            #    pass
            SettingDecrease(1)
            # print(mnIntensitySetting)
        # else:
        #    if mnIntensitySetting == 0:
        #        WarningShotMode()

    if btn2.fell:
        btn2Down = time.monotonic()
    if btn2.rose:
        nBtn2DownTime = time.monotonic() - btn2Down
        if nBtn2DownTime < 2:
            DisableOverload()
            # probably want to not do anything if already at max or min setting?
            # or different sound for NO?
            # decrement setting if under 2 sec press
            # Plays the sample once when loop=False,
            # and continuously when loop=True. Does not block
            # moAudioPlay.play(moSettingSnd)
            # while moAudioPlay.playing:
            #    pass
            moI2SAudio.play(moSettingSnd)
            # while moI2SAudio.playing:
            #    pass
            SettingIncrease(1)
            # print(mnIntensitySetting)
        else:
            if not IS_TYPE_ONE_PHASER and mnIntensitySetting == 15:
                RunOverloadMode()
            elif IS_TYPE_ONE_PHASER is True and mnIntensitySetting == 8:
                RunOverloadMode()
    RunChargingMode()
