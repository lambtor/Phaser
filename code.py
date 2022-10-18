import board
import digitalio
import neopixel
# import audioio
import audiocore
# from audiocore import WaveFile
from adafruit_debouncer import Debouncer
import time
import random
import math
from userSettings import UserSettings
from menuOptions import MenuOptions
import alarm
# this script is meant to be used with qt py rp2040
# this is for MAX98357A speaker board. drop wav files in main directory of qt py board
import audiobusio
import audiomixer
from analogio import AnalogIn

# OK OMFG mu editor has a max of 88 characters per line of code
# ---------------------------------------------------------------------------------------
# User config settings - these should be set once for program
# to behave for your hardware
# true or false here. False means program is for a type 2
# A3 is for laser itself. TX might need to be used for beam neopixels.
IS_TYPE_ONE_PHASER = True
SETTING_LED_PIN = board.A1
BEAM_LED_PIN = board.A0
BATTERY_PIN = board.A2
BEAM_LASER_PIN = board.A3
# if using stemma speaker board, this MIGHT use pin SDA1?
# only 3 pins connected when using stemma speaker board, so maybez
SETTING_SND_FILE = "adjust.wav"
FIRELOOP_SND_FILE = "firingloop.wav"
FIREWARM_SND_FILE = "warmup.wav"
FIREDOWN_SND_FILE = "cooldown.wav"
OVERLOAD_SND_FILE = "overload.wav"
EXPLOSION_SND_FILE = "explosion.wav"
# 0 here is simple blink of highest level LED with rest solid
# 1 is a "wave" that flows left-right
CHARGING_STYLE = 0
BTN_LEFT = board.TX
BTN_RIGHT = board.RX
BTN_TRIGGER = board.MOSI
# menu settings. 8 total LEDs, so if you want these re-ordered,
# set their places here. ALL these need to be unique integers < 8
MENUIDX_FREQ = 0
MENUIDX_AUTO = 1
MENUIDX_VOL = 2
MENUIDX_SLEEP = 3
MENUIDX_ST = 4
MENUIDX_BEAM = 5
MENUIDX_OVLD = 6
MENUIDX_EXIT = 7

# number from 0-1 (you'd never want 1, as that'd be ALWAYS OFF
BEAM_FLICKER_RATE = 0.1
BEAM_FPS = 90

# --------
# current active device settings - do these need to persist across power cycles?

mnIntensitySetting = 0
# this needs to be 1 more than the total number of actual setting LEDs you have
if IS_TYPE_ONE_PHASER:
    mnSettingLEDMax = 9
else:
    mnSettingLEDMax = 17
mnBeamLEDCount = 7

# try:
#    from audioio import AudioOut
# except ImportError:
#    try:
#        from audiopwmio import PWMAudioOut as AudioOut
#    except ImportError:
#        pass
moI2SAudio = audiobusio.I2SOut(board.SDA1, board.SCL1, board.SCK)

moSettingSoundFile = open(SETTING_SND_FILE, "rb")
moFiringLoopFile = open(FIRELOOP_SND_FILE, "rb")
moFireWarmFile = open(FIREWARM_SND_FILE, "rb")
moFireDownFile = open(FIREDOWN_SND_FILE, "rb")
moExplosionFile = open(EXPLOSION_SND_FILE, "rb")
moOverloadFile = open(OVERLOAD_SND_FILE, "rb")
moSettingSnd = audiocore.WaveFile(moSettingSoundFile)
moFireLoopSnd = audiocore.WaveFile(moFiringLoopFile)
moFireWarmSnd = audiocore.WaveFile(moFireWarmFile)
moFireDownSnd = audiocore.WaveFile(moFireDownFile)
moOverloadSnd = audiocore.WaveFile(moOverloadFile)
moExplosionSnd = audiocore.WaveFile(moExplosionFile)
mnFireWarmSndLength = 1.25
mnOvldSndLength = 0.2
mdFireLEDLength = 0.18
mnFireWarmStep = 0

moRGBRed = (255, 0, 0)
moRGBFullRed = (255, 0, 0)
moRGBBlack = (0, 0, 0)
moRGBWarn = (128, 0, 128)
moRGBStrength = 128
moRGBBattery = (0, 0, 255)
moUser = UserSettings()

# user settings required for mixer definition of volume. all wav files are 22050 sample rate.
# if you use a different sample rate, use same one for all sound files and specify it here
moMixer = audiomixer.Mixer(voice_count=1, sample_rate=22050, channel_count=1, bits_per_sample=16, samples_signed=True)

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

moLaser = digitalio.DigitalInOut(BEAM_LASER_PIN)
moLaser.direction = digitalio.Direction.OUTPUT

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

# pin alarms. 3 separate ones to allow any button press to wake phaser
moPinAlarmL = alarm.pin.PinAlarm(BTN_LEFT, value=False, pull=True)
moPinAlarmR = alarm.pin.PinAlarm(BTN_RIGHT, value=False, pull=True)
moPinAlarmT = alarm.pin.PinAlarm(BTN_TRIGGER, value=False, pull=True)

# time function returns everything as seconds.
# all comparisons for delay less than 1 second need to use decimals
mbIsFiring = False
mbIsWarming = False
mnChargingFrame = 0
mdecChargingFrameDelay = 0.25
mnChargingLastTime = 0
mnLastBattCheck = 0
mnBattCheckInterval = 1
mdFiringLastTime = 0
mnWarmLastTime = 0
mdecStartFiringTime = 0.0
mdecLastBeamFrame = 0.0
# this is used in main loop to control button behavior
# 0 = normal, 1 = menu, 2 = charging
# 3 = autofire, 4 = overload
moActiveMode = 0
mdecModeTime = 0.0
mdecBtnTime = time.monotonic()
mdecSleepMax = 120
# seconds between check for current active mode
mnModeInterval = 1
mnMenuModeThreshold = 2.0
mbMenuBtn1Clear = False
mbMenuBtn2Clear = False
mnMenuIndex = 0
mdecMenuFlashDelay = 0.3
mdecMenuLastFlash = 0.0
mbMenuIndexLEDOff = True
mdecOverFrameDelay = 0.5
mnMaxOverFrame = 60
mnCurrOverFrame = 0
mnOverFrameSpeed = 0.3
mnOverFrameSpDef = 0.3
mdecOverMult = 1.25
mdecOverLastTime = 0
mdecAutoCoolTime = 0.0
mbAutoCooldown = False
mbAutoFlashing = False
mdecAutoFlashTime = 0.0
mdecAutoFlashDelay = 0.25
mdecAutoStart = 0.0
mdecAutoBeamStart = 0.0
mdecAutoBeamEnd = 0.0
moBatteryRead = AnalogIn(BATTERY_PIN)
mbBatteryShown = False

def ButtonRead(pin):
    io = digitalio.DigitalInOut(pin)
    io.direction = digitalio.Direction.INPUT
    io.pull = digitalio.Pull.UP
    return lambda: io.value

def SettingDecrease(nAmount):
    global mnIntensitySetting
    if mnIntensitySetting > 0:
        mnIntensitySetting -= nAmount
    UpdateIntensity()

def SettingIncrease(nAmount):
    global mnSettingLEDMax
    global mnIntensitySetting
    if mnIntensitySetting < (mnSettingLEDMax - 1):
        mnIntensitySetting += nAmount
    UpdateIntensity()

# settings with 2 bars, bottom bar goes unlit to full green
# then from full green, for 8-15, this bar fades green to orange
# while top bar climbs up red. at 15, bottom bar is full orange
# and top bar is full red.
# need way to set phaser to overload from setting 15 (hold up btn 5 sec?)
# need way to set phaser to autofire (wesley) from zero (hold down btn 3 sec?)
# warning shot mode, set 1 LED pink & max sound min beam brightness
def UpdateIntensity():
    global mnIntensitySetting
    global moSettingRow
    global moRGBRed
    global moRGBBlack
    global moRGBStrength
    global mnSettingLEDMax
    global IS_TYPE_ONE_PHASER

    # print(mnIntensitySetting)
    if mnIntensitySetting == 0:
        # moSettingRow.fill(moRGBBlack)
        # moSettingRow.write()
        WarningShotMode()
        return

    # to-do: flip orientation
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
    # set intensity according to user-selected max brightness
    # update beam brightness to reflect intensity setting
    # moBeamRow.brightness = (1 / (mnSettingLEDMax - mnIntensitySetting))
    decBeamLvBright = (1 / (mnSettingLEDMax - mnIntensitySetting))
    moBeamRow.brightness = decBeamLvBright * GetBeamBrightnessLevel()
    # moBeamRow.brightness = GetBeamBrightnessLevel()
    moBeamRow.write()

def WarningShotMode():
    global moSettingRow
    global moRGBBlack
    global moRGBWarn
    moSettingRow.fill(moRGBBlack)
    moSettingRow[0] = moRGBWarn
    moSettingRow.write()

def DisableWarningShotMode():
    global moSettingRow
    moSettingRow.fill(moRGBBlack)
    moSettingRow.write()

def StartFiring(bIsInit):
    global mbIsFiring
    global moBeamRow
    global mbIsWarming
    global mnFireWarmStep
    global mnWarmLastTime
    global mnFireWarmSndLength
    global mdecStartFiringTime
    global moUser
    global moRGBBlack
    global moRGBRed
    nFadeSteps = 4

    # need to fade in beam WAY faster than warmup sound
    if not mbIsWarming and not bIsInit:
        return
    if bIsInit is True:
        mbIsWarming = True
    # kick out if it's too soon to step to next frame
    if (time.monotonic() - mnWarmLastTime) < (mdFireLEDLength / nFadeSteps):
        return

    # oColor = MenuOptions.Frequency[moUser.Frequency]
    oColor = moRGBRed
    oColorAlt = MenuOptions.FreqSup[moUser.Frequency]
    oFreqR = oColor[0]
    oFreqG = oColor[1]
    oFreqB = oColor[2]

    # fade from black up to full red - this is non-blocking
    if (mnFireWarmStep < nFadeSteps):
        oFreqR = int(oColor[0] / (nFadeSteps - mnFireWarmStep))
        oFreqB = int(oColor[1] / (nFadeSteps - mnFireWarmStep))
        oFreqG = int(oColor[2] / (nFadeSteps - mnFireWarmStep))
        oColor = (oFreqR, oFreqG, oFreqB)
        moBeamRow.fill(oColor)
        moBeamRow.write()
        mnWarmLastTime = time.monotonic()
        # print(mnFireWarmStep, " | ", oColor)
        mnFireWarmStep += 1
        return
    # flicker during warmup
    if ((time.monotonic() - mnWarmLastTime) >= (1 / BEAM_FPS)):
        nRand = random.randint(0, 9)
        # nRand = int(math.modf(time.monotonic())[0] * 10)
        if (nRand < (BEAM_FLICKER_RATE * 10)):
            moBeamRow.fill(oColorAlt)
            moBeamRow.show()
            moLaser.value = False
        else:
            moLaser.value = True
            moBeamRow.fill(oColor)
            moBeamRow.show()
        mnWarmLastTime = time.monotonic()
    decTimeRef = time.monotonic() - mdecStartFiringTime
    # warming over, set isFiring flag on to hand over to that animation
    if mnFireWarmStep >= nFadeSteps and (decTimeRef > mnFireWarmSndLength):
        mbIsWarming = False
        mnFireWarmStep = 0
        mbIsFiring = True
        RunFiring(True)

def RunFiring(bInitLoop):
    global mbIsFiring
    global BEAM_FPS
    global BEAM_FLICKER_RATE
    global moI2SAudio
    global moBeamRow
    global moRGBBlack
    global moRGBRed
    global mnBeamLEDCount
    global mdFiringLastTime
    global moUser
    global moLaser
    if (bInitLoop is True):
        mbIsFiring = True
        # moI2SAudio.play(moFireLoopSnd, loop=True)
        PlaySound(moFireLoopSnd, False, True)
    # depending on "refresh rate" and "flicker rate" values at top,
    # occasionally turn off beam neopixels uniformly?
    # if (not mbIsFiring and not bInitLoop) or mbInMenu is True or mbIsCharging is True:
    if (not mbIsFiring and not bInitLoop):
        return
    if ((time.monotonic() - mdFiringLastTime) >= (1 / BEAM_FPS)):
        nRand = random.randint(0, 9)
        # nRand = int(math.modf(time.monotonic())[0] * 10)
        if (nRand < (BEAM_FLICKER_RATE * 10)):
            # moBeamRow.fill(moRGBBlack)
            moBeamRow.fill(MenuOptions.FreqSup[moUser.Frequency])
            moBeamRow.show()
            moLaser.value = False
        else:
            # moBeamRow.fill(MenuOptions.Frequency[moUser.Frequency])
            moBeamRow.fill(moRGBRed)
            moBeamRow.show()
            moLaser.value = True
        mdFiringLastTime = time.monotonic()

def StopFiring():
    global moBeamRow
    global mbIsFiring
    global mbIsWarming
    global moI2SAudio
    global mnFireWarmStep
    global moFireDownSnd
    global moLaser
    # run cooldown sound
    # moI2SAudio.stop()
    # moI2SAudio.play(moFireDownSnd, loop=False)
    PlaySound(moFireDownSnd)
    # block on cooldown sound
    # while moI2SAudio.playing:
    #    pass
    # moBeamRow.fill(moRGBBlack)
    # moBeamRow.show()
    mnFireWarmStep = 0
    if (mbIsWarming is True):
        time.sleep(0.2)
    else:
        time.sleep(0.1)
    mbIsFiring = False
    mbIsWarming = False
    moBeamRow.fill(moRGBBlack)
    moBeamRow.show()
    moLaser.value = False

def StartOverload():
    global moActiveMode
    global moSettingRow
    global moRGBRed
    global mnOverFrameSpeed
    moSettingRow.fill(moRGBRed)
    moSettingRow.show()
    time.sleep(3)
    moActiveMode = 4
    # play overload warmup sound non-blocking
    # pass

def RunOverload():
    global moSettingRow
    global moRGBRed
    global moRGBBlack
    global mnOverFrameSpeed
    global mdecOverLastTime
    global mdecOverMult
    global mnMaxOverFrame
    global mnOverFrameSpDef
    global moPinAlarmL
    global moPinAlarmR
    global moPinAlarmT
    global mnCurrOverFrame
    global moOverloadSnd
    global moExplosionSnd
    global mnOvldSndLength

    # global moActiveMode
    # need to flash all setting LEDs progressively faster
    # while warmup sound plays - track this with frame #
    nNow = time.monotonic()
    if ((nNow - mdecOverLastTime > mnOverFrameSpeed) and (mnCurrOverFrame <= mnMaxOverFrame)):
        if (mnCurrOverFrame % 2 == 0):
            moSettingRow.fill(moRGBRed)
            # play beep if frame speed is slower than length of beep sound file
            # if (mnOverFrameSpeed > mnOvldSndLength):
            PlaySound(moOverloadSnd, False, False, False)
        else:
            moSettingRow.fill(moRGBBlack)
        if (mnCurrOverFrame % 8 == 0):
            mnOverFrameSpeed = mnOverFrameSpeed / mdecOverMult
        mnCurrOverFrame += 1
        moSettingRow.write()
        mdecOverLastTime = nNow
        # print(mnCurrOverFrame)
    elif (mnCurrOverFrame > mnMaxOverFrame):
        # to-do:
        # play explosion sound
        moSettingRow.fill(moRGBRed)
        moSettingRow.write()
        time.sleep(0.2)
        mnCurrOverFrame = 0
        mnOverFrameSpeed = mnOverFrameSpDef
        mdecOverLastTime = nNow
        moSettingRow.fill(moRGBBlack)
        moSettingRow.write()
        time.sleep(0.2)
        # wait for sound to finish playing before sending board to sleep
        PlaySound(moExplosionSnd, True, False, True)
        # go to sleep mode
        alarm.exit_and_deep_sleep_until_alarms(moPinAlarmL, moPinAlarmR, moPinAlarmT)

def StopOverload():
    global moActiveMode
    global moSettingRow
    moActiveMode = 0
    moSettingRow.fill(moRGBBlack)
    moSettingRow.show()
    time.sleep(0.2)
    # play wind-down sound?
    UpdateIntensity()

def StartAutofire():
    global moActiveMode
    global moSettingRow
    global mbAutoCooldown
    global mdecAutoCoolTime
    global mdecAutoFlashDelay
    moActiveMode = 3
    UpdateIntensity()
    mbAutoCooldown = True
    # set autofire cooldown timestamp as NOW
    mdecAutoCoolTime = time.monotonic()
    # print("cooldown start " + str(mdecAutoCoolTime))
    # time.sleep(mdecAutoFlashDelay * 2)

def RunAutofire():
    global mbIsWarming
    global mdecAutoCoolTime
    global mbAutoCooldown
    global mdecAutoStart
    # global mdecAutoBeamStart
    global mdecStartFiringTime
    global mdecAutoBeamEnd
    global mdecAutoFlashTime
    global mdecAutoFlashDelay
    global mbAutoFlashing
    global moSettingRow
    global moI2sAudio
    global moFireWarmSnd

    # need to animate settings to convey autofire
    # use current intensity as periodically flashing
    dtNow = time.monotonic()
    if (dtNow - mdecAutoFlashTime > mdecAutoFlashDelay):
        if mbAutoFlashing is True:
            UpdateIntensity()
        else:
            moSettingRow.fill(moRGBBlack)
            moSettingRow.show()
        mbAutoFlashing = not mbAutoFlashing
        mdecAutoFlashTime = time.monotonic()

    if mbAutoCooldown is True:
        if (time.monotonic() - mdecAutoCoolTime > 5):
            mbAutoCooldown = False
            # mdecAutoBeamStart = time.monotonic()
            # mdecStartFiringTime = mdecAutoBeamStart
            mdecStartFiringTime = time.monotonic()
            # moI2SAudio.play(moFireWarmSnd)
            PlaySound(moFireWarmSnd)
            # print("start firing " + str(mdecStartFiringTime))
            StartFiring(True)
    else:
        if mbIsWarming is True:
            # print("warming " + str(time.monotonic()))
            StartFiring(False)
        else:
            RunFiring(False)
        if (dtNow - mdecStartFiringTime >= 3):
            StopFiring()
            mdecAutoCoolTime = time.monotonic()
            mbAutoCooldown = True

def StopAutofire():
    global moActiveMode
    global moSettingRow
    moActiveMode = 0
    moSettingRow.fill(moRGBBlack)
    moSettingRow.show()
    time.sleep(0.3)
    # play cancel sound?
    UpdateIntensity()

def CheckCharging():
    # if charging mode is active, run charging mode
    global moActiveMode
    # moBatteryRead
    # voltage over threshold means connected to usb
    # anytime usb connected, battery is charging
    # if (voltage > maximum)
    # moActiveMode = 2
    # set brightness for settings chain to 0.4
    # to allow brightness for animation
    # if (moSettingRow.brightness != GetSettingBrightnessLevel()):
    #    moSettingRow.brightness = GetSettingBrightnessLevel()
    # change mode to normal and update setting row
    # elif (moActiveMode == 2)
    # moActiveMode = 0
    # DisableCharging()
    pass

def ShowBattery():
    global moSettingRow
    global moRGBBlack
    global moRGBBattery
    blinkLength = 0.4
    blinkCount = 10
    # print(GetVoltage())
    decCurrentVoltage = min(max(GetVoltage(), 3.2), 4.2)
    # print(decCurrentVoltage)
    nCurrentPower = int(map_range(decCurrentVoltage, 3.2, 4.2, 0.0, 8.0))
    print(nCurrentPower)
    bIsBlinking = False
    for nCount in range(blinkCount):
        if (not bIsBlinking):
            for nSettingLED in range(nCurrentPower):
                moSettingRow[nSettingLED] = moRGBBattery
        else:
            moSettingRow.fill(moRGBBlack)
        moSettingRow.write()
        time.sleep(blinkLength)
        bIsBlinking = not bIsBlinking

def GetVoltage():
    global moBatteryRead
    # this should be an approx 3.2 - 4.8
    # print((moBatteryRead.value * 6.6) / 65536)
    # apparently, previous versions used 3.3 as battery reference, but now this is 3.6
	# for this reason, if you use 3.3 with a newer version of firmware,
    # batt % will show 60 when it should be 100. 3.6 * 2 = 7.2
    return ((moBatteryRead.value * 7.2) / 65536)

def map_range(s, a1, a2, b1, b2):
    return  math.ceil(b1 + ((s - a1) * (b2 - b1) / (a2 - a1)))

def DisableCharging():
    global moSettingRow
    global moRGBBlack
    moSettingRow.brightness = GetSettingBrightnessLevel()
    moSettingRow.fill(moRGBBlack)
    moSettingRow.show()
    UpdateIntensity()

def RunChargingMode():
    # global mbIsCharging
    global mnChargingFrame
    global mdecChargingFrameDelay
    global moSettingRow
    global moRGBStrength
    global moRGBBlack
    global mnSettingLEDMax
    global mnChargingLastTime
    global IS_TYPE_ONE_PHASER
    nFade = 2
    # change this to pull from a2 pin
    nBattPercentage = 0
    # GetBatteryPercent()
    nMaxFrames = mnSettingLEDMax + 4
    nCurrentTime = time.monotonic()
    nLEDTier = 0

    # use setting to change charging animation style?
    if ((nCurrentTime - mnChargingLastTime) < mdecChargingFrameDelay):
        return

    # to do: modify animation to all solid up to floor(battlvl / leds)
    # and next one above it to flashing or pulsing
    # when charging style is 0, simple blink of highest led w/
    # lower all solid
    # otherwise, all leds for a "tier" are lit with a pulsing animation
    if (CHARGING_STYLE == 0):
        nLEDTier = int(nBattPercentage / (100 / (mnSettingLEDMax - 1)))
        for nLED in range(mnSettingLEDMax - 1):
            if nLED == nLEDTier:
                if (mnChargingFrame % 2 == 0):
                    moSettingRow[nLED] = (0, 0, moRGBStrength)
                else:
                    moSettingRow[nLED] = moRGBBlack
            elif nLED < nLEDTier:
                # nBlueStrength = moRGBStrength
                moSettingRow[nLED] = (0, 0, moRGBStrength)
                if not IS_TYPE_ONE_PHASER:
                    moSettingRow[nLED + 8] = (0, 0, moRGBStrength)
    else:
        if mnChargingFrame >= 0 and mnChargingFrame <= mnSettingLEDMax:
            # draw current "frame" on settings pixels
            for nIterator3 in range(mnSettingLEDMax - 1):
                nLEDTier = int(nBattPercentage / (100 / (mnSettingLEDMax - 1)))
                if nIterator3 == mnChargingFrame:
                    if nIterator3 <= nLEDTier:
                        moSettingRow[nIterator3] = (0, 0, moRGBStrength)
                        if not IS_TYPE_ONE_PHASER:
                            moSettingRow[nIterator3 + 8] = (0, 0, moRGBStrength)
                # elif (mnChargingFrame - nIterator3) == 1:
                #    if nIterator3 <= nLEDTier:
                #        moSettingRow[nIterator3] = (0, 0, int(moRGBStrength / nFade))
                # elif (nIterator3 - mnChargingFrame) == 1:
                #    if nIterator3 <= nLEDTier:
                #        moSettingRow[nIterator3] = (0, 0, int(moRGBStrength / nFade))
                elif nIterator3 <= nLEDTier:
                    nBlueStrength = int((moRGBStrength / nFade) / nFade)
                    moSettingRow[nIterator3] = (0, 0, nBlueStrength)
                    if not IS_TYPE_ONE_PHASER:
                        moSettingRow[nIterator3 + 8] = (0, 0, moRGBStrength)

    moSettingRow.show()
    mnChargingLastTime = nCurrentTime
    mnChargingFrame += 1
    # print(mnChargingFrame)
    if (mnChargingFrame > nMaxFrames):
        mnChargingFrame = 0

# def GetBatteryPercent():
# global BATTERY_PIN
# return ((6.6 * AnalogIn(BATTERY_PIN)) / 4095)

def ShowMenu():
    # init setting colors using current values
    # only bottom 8 leds used for menu
    global moActiveMode
    global moRGBBlack
    global moUser
    global moSettingRow
    global mbMenuBtn1Clear
    global mbMenuBtn2Clear
    global mnMenuIndex

    for nInt in range(len(moSettingRow) - 1):
        if nInt == mnMenuIndex:
            moSettingRow[nInt] = GetMenuIndexColor(mnMenuIndex)
        else:
            moSettingRow[nInt] = moRGBBlack
    # moSettingRow[5] = moRGBBlack
    moSettingRow[MENUIDX_EXIT] = MenuOptions.Exit
    moSettingRow.brightness = GetSettingBrightnessLevel()
    # highlight current hovered option
    moSettingRow.show()
    mbMenuBtn1Clear = False
    mbMenuBtn2Clear = False
    moActiveMode = 1
    NavMenu(0)

def RunMenu():
    global mdecMenuFlashDelay
    global mdecMenuLastFlash
    global mnMenuIndex
    global mbMenuIndexLEDOff
    global moSettingRow
    global moRGBBlack
    global moActiveMode
    if (moActiveMode != 1):
        return

    if (time.monotonic() - mdecMenuLastFlash > mdecMenuFlashDelay):
        if mbMenuIndexLEDOff is True:
            moSettingRow[mnMenuIndex] = GetMenuIndexColor(mnMenuIndex)
        else:
            moSettingRow[mnMenuIndex] = moRGBBlack
        moSettingRow.show()
        mbMenuIndexLEDOff = not mbMenuIndexLEDOff
        mdecMenuLastFlash = time.monotonic()

def ExitMenu():
    global moActiveMode
    moActiveMode = 0
    UpdateIntensity()

def NavMenu(nIndex):
    global mnMenuIndex
    global moI2SAudio
    global moSettingSnd
    global moSettingRow
    global moRGBBlack

    # undo previous "highlight"
    # moSettingRow[mnMenuIndex] = GetMenuIndexColor(mnMenuIndex)
    # cycle around if you try to go beyond edges
    if (mnMenuIndex == 7 and nIndex == 1):
        mnMenuIndex = 0
    elif (mnMenuIndex == 0 and nIndex == -1):
        mnMenuIndex = 7
    else:
        mnMenuIndex += nIndex

    for nInt in range(len(moSettingRow) - 1):
        if nInt == mnMenuIndex:
            moSettingRow[nInt] = GetMenuIndexColor(mnMenuIndex)
        else:
            moSettingRow[nInt] = moRGBBlack
    # moSettingRow[5] = moRGBBlack
    moSettingRow[MENUIDX_EXIT] = MenuOptions.Exit
    moSettingRow.show()
    time.sleep(0.1)
    # moI2SAudio.play(moSettingSnd)
    PlaySound(moSettingSnd)

def UpdateMenuSetting():
    global mnMenuIndex
    global moUser
    global moSettingSnd
    # most menu selections need to hide all other columns
    # flash current value, change color to "NEW" value
    # set new value, flash "NEW" value twice
    # then return to menu
    if (mnMenuIndex == MENUIDX_EXIT):
        mnMenuIndex = 0
        ExitMenu()
        return
    elif (mnMenuIndex == MENUIDX_AUTO):
        StartAutofire()
        return
    elif (mnMenuIndex == MENUIDX_OVLD):
        StartOverload()
        return
    elif (mnMenuIndex == MENUIDX_FREQ):
        nFreq = moUser.Frequency
        # freq for modulation uses different flicker backup color
        if (nFreq < (len(MenuOptions.Frequency) - 1)):
            moUser.Frequency += 1
            moUser.FreqSup += 1
        else:
            moUser.Frequency = 0
            moUser.FreqSup = 0
        AnimateSettingChange(MenuOptions.Frequency[nFreq], MenuOptions.Frequency[moUser.Frequency])
        # play acknowledge sound
    elif (mnMenuIndex == MENUIDX_SLEEP):
        nTimeout = moUser.SleepTimer
        if (nTimeout < (len(MenuOptions.SleepTimer) - 1)):
            moUser.SleepTimer = 1
        else:
            moUser.SleepTimer = 0
        AnimateSettingChange(MenuOptions.SleepTimer[nTimeout], MenuOptions.SleepTimer[moUser.SleepTimer])
    elif (mnMenuIndex == MENUIDX_VOL):
        nCurrVol = moUser.Volume
        if (nCurrVol < (len(MenuOptions.Volume) - 1)):
            moUser.Volume += 1
        else:
            moUser.Volume = 0
        # play acknowledge sound at old volume
        AnimateSettingChange(MenuOptions.Volume[nCurrVol], MenuOptions.Volume[moUser.Volume])
        # play acknowledge sound at new volume
        UpdateVolume()
        # PlaySound(moSettingSnd)
    elif (mnMenuIndex == MENUIDX_BEAM):
        nBeam = moUser.BeamBrightIndex
        if (nBeam < (len(MenuOptions.BeamBrightness) - 1)):
            moUser.BeamBrightIndex += 1
        else:
            moUser.BeamBrightIndex = 0
        AnimateSettingChange(MenuOptions.BeamBrightness[nBeam], MenuOptions.BeamBrightness[moUser.BeamBrightIndex])
        # update brightness for beam row - fade in beam row?
    elif (mnMenuIndex == MENUIDX_ST):
        nSetting = moUser.SettingBrightIndex
        if (nSetting < (len(MenuOptions.SettingBrightness) - 1)):
            moUser.SettingBrightIndex += 1
        else:
            moUser.SettingBrightIndex = 0
        moSettingRow.brightness = GetSettingBrightnessLevel()
        AnimateSettingChange(MenuOptions.SettingBrightness[nSetting], MenuOptions.SettingBrightness[moUser.SettingBrightIndex])
        # update brightness for setting row to new factor
    # return to menu
    ShowMenu()

def AnimateSettingChange(oColorOld, oColorNew):
    global mnMenuIndex
    global moSettingRow
    global moRGBBlack
    global moI2SAudio
    global moSettingSnd
    # this is blocking - it NEEDS to be for stability
    moSettingRow.fill(moRGBBlack)
    moSettingRow.show()
    time.sleep(0.1)
    moSettingRow[mnMenuIndex] = oColorOld
    moSettingRow.show()
    time.sleep(0.2)
    moSettingRow[mnMenuIndex] = oColorNew
    moSettingRow.show()
    time.sleep(0.5)
    moSettingRow.fill(moRGBBlack)
    moSettingRow.show()
    time.sleep(0.2)
    moSettingRow[mnMenuIndex] = oColorNew
    moSettingRow.show()
    # moI2SAudio.play(moSettingSnd)
    time.sleep(0.1)

def GetMenuIndexColor(nIndex):
    global moUser
    arMenu = [0, 0, 0, 0, 0, 0, 0, 0]
    arMenu[MENUIDX_FREQ] = MenuOptions.Frequency[moUser.Frequency]
    arMenu[MENUIDX_AUTO] = MenuOptions.Autofire
    arMenu[MENUIDX_VOL] = MenuOptions.Volume[moUser.Volume]
    arMenu[MENUIDX_SLEEP] = MenuOptions.SleepTimer[moUser.SleepTimer]
    arMenu[MENUIDX_BEAM] = MenuOptions.BeamBrightness[moUser.BeamBrightIndex]
    arMenu[MENUIDX_ST] = MenuOptions.SettingBrightness[moUser.SettingBrightIndex]
    arMenu[MENUIDX_OVLD] = MenuOptions.Overload
    arMenu[MENUIDX_EXIT] = MenuOptions.Exit
    return arMenu[nIndex]

def GetSettingBrightnessLevel():
    # this should go 1/2, 1/4, 1/8, 1/12, 1/16, 1/20
    global moUser
    # return (1 / (moUser.SettingBrightIndex == 0 ? 2 : 4 * moUser.SettingBrightIndex))
    return 0.5 if moUser.SettingBrightIndex == 0 else (1 / (4 * moUser.SettingBrightIndex))

def GetBeamBrightnessLevel():
    # this should go 1/2, 1/4, 1/8, 1/12, 1/16, 1/20
    # if 4 is changed to 2, this could be 1, 1/2, 1/6, 1/8, 1/10
    global moUser
    # return (1 / (moUser.BeamBrightIndex == 0 ? 1 : 2 * moUser.BeamBrightIndex))
    if moUser.BeamBrightIndex > 4:
        return 0.1
    return 1 if moUser.BeamBrightIndex == 0 else (1 - (0.2 * moUser.BeamBrightIndex))

def UpdateVolume():
    global moUser
    global moMixer
    if (moUser.Volume == 0):
        decLevel = 1
    # this ensures last setting causes full mute
    elif (moUser.Volume == (len(MenuOptions.Volume) - 1)):
        decLevel = 0
    else:
        decLevel = 1 - ((1 / (len(MenuOptions.Volume) - 1)) * moUser.Volume)
    # for nInt in range(len(moMixer.voice) - 1):
    #    moMixer.voice[nInt].level = decLevel
    moMixer.voice[0].level = decLevel

def PlaySound(oSound, bStop=False, bLoop=False, bBlock=False):
    global moMixer
    global moI2SAudio
    if bStop is True:
        moI2SAudio.stop()
        moMixer.voice[0].stop()
    moI2SAudio.play(moMixer)
    moMixer.voice[0].play(oSound, loop=bLoop)
    if bBlock is True:
        while moMixer.playing:
            pass

def CheckSleep():
    # need to write current settings to a file
    # and modify startup to pull from this file
    # otherwise setting changes will be lost on deep sleep
    global moPinAlarmL
    global moPinAlarmR
    global moPinAlarmT
    global mdecSleepMax
    global mdecBtnTime
    global moSettingRow
    global moRGBBlack
    global moI2SAudio
    global moMixer
    if ((time.monotonic() - mdecBtnTime) > mdecSleepMax):
        # fade these to black?
        moSettingRow.fill(moRGBBlack)
        moSettingRow.write()
        print("sleep mode triggered: " + str(time.monotonic()))
        # play shutdown sound?
        moMixer.voice[0].stop()
        moI2SAudio.stop()
        alarm.exit_and_deep_sleep_until_alarms(moPinAlarmL, moPinAlarmR, moPinAlarmT)

def GoToSleep():
    global moPinAlarmL
    global moPinAlarmR
    global moPinAlarmT
    global moSettingRow
    global moRGBBlack
    global moI2SAudio
    global moMixer
    # fade these to black?
    moSettingRow.fill(moRGBBlack)
    moSettingRow.write()
    print("sleep mode forced: " + str(time.monotonic()))
    # play shutdown sound?
    moMixer.voice[0].stop()
    moI2SAudio.stop()
    alarm.exit_and_deep_sleep_until_alarms(moPinAlarmL, moPinAlarmR, moPinAlarmT)

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
UpdateVolume()

# arduino equivalent of loop()
while True:
    btn1.update()
    btn2.update()
    btnTrigger.update()

    if (not mbBatteryShown):
        ShowBattery()
        mbBatteryShown = True
        UpdateIntensity()

    # logic to determine mode here
    # if ((time.monotonic() - mdecModeTime) > mnModeInterval):
    #    CheckCharging()
    if (moUser.SleepTimer == 1 and not any(moActiveMode == y for y in (2, 3)) and (time.monotonic() - mdecBtnTime) > mnModeInterval):
        CheckSleep()

    # check btn timers for menu invocation
    # do NOT allow menu entry if charging
    if (not btn1.value and not btn2.value and moActiveMode == 0):
        if ((time.monotonic() - max(btn1Down, btn2Down)) > mnMenuModeThreshold):
            # play sound for menu entry? picard monitor chirp?
            mdecBtnTime = time.monotonic()
            ShowMenu()

    # charging
    if moActiveMode == 2:
        RunChargingMode()
    # menu
    elif moActiveMode == 1:
        # handle initial button lifts after menu invoked
        # this prevents buttons from moving selection until they're
        # pressed down and risen again
        if btn1.rose:
            mdecBtnTime = time.monotonic()
            if not mbMenuBtn1Clear:
                mbMenuBtn1Clear = True
            else:
                NavMenu(-1)
        if btn2.rose:
            mdecBtnTime = time.monotonic()
            if not mbMenuBtn2Clear:
                mbMenuBtn2Clear = True
            else:
                NavMenu(1)
        if btnTrigger.rose:
            mdecBtnTime = time.monotonic()
            UpdateMenuSetting()
        # need blink or pulse animation for "highlighted" index
        RunMenu()
    # autofire
    elif moActiveMode == 3:
        if btn1.fell or btn2.fell or btnTrigger.fell or btn1.rose or btn2.rose or btnTrigger.rose:
            mdecBtnTime = time.monotonic()
            StopFiring()
            # moI2SAudio.stop()
            # time.sleep(0.2)
            # moI2SAudio.play(moSettingSnd)
            PlaySound(moSettingSnd, True)
            StopAutofire()
        RunAutofire()
    # overload
    elif moActiveMode == 4:
        if btn1.rose or btn2.rose or btnTrigger.rose:
            mdecBtnTime = time.monotonic()
            # moI2SAudio.play(moSettingSnd)
            PlaySound(moSettingSnd, True)
            StopOverload()
        RunOverload()
    # default to normal
    else:
        if btnTrigger.fell:
            mdecBtnTime = time.monotonic()
            btnTriggerDown = time.monotonic()
            # disable overload mode if this is pressed?
            # start firing sound, warmup beam leds
            mdecStartFiringTime = time.monotonic()
            # moI2SAudio.play(moFireWarmSnd)
            PlaySound(moFireWarmSnd)
            StartFiring(True)
        if btnTrigger.rose:
            mdecBtnTime = time.monotonic()
            btnTriggerTime = time.monotonic() - btnTriggerDown
            StopFiring()

        if mbIsWarming is True:
            StartFiring(False)
        RunFiring(False)

        # handle each button's actions. need long and short press support
        if btn1.fell:
            btn1Down = time.monotonic()
        if btn1.rose:
            mdecBtnTime = time.monotonic()
            nBtn1DownTime = time.monotonic() - btn1Down
            if nBtn1DownTime < 2:
                # decrement setting if under 2 sec press
                PlaySound(moSettingSnd)
                # moI2SAudio.play(moSettingSnd)
                # while moI2SAudio.playing():
                #    pass
                SettingDecrease(1)
                # print(mnIntensitySetting)
            elif nBtn1DownTime >= 3:
                GoToSleep()
        if btn2.fell:
            btn2Down = time.monotonic()
        if btn2.rose:
            mdecBtnTime = time.monotonic()
            nBtn2DownTime = time.monotonic() - btn2Down
            if nBtn2DownTime < 2:
                # moI2SAudio.play(moSettingSnd)
                PlaySound(moSettingSnd)
                SettingIncrease(1)
            else:
                if not IS_TYPE_ONE_PHASER and mnIntensitySetting == 15:
                    StartOverload()
                elif IS_TYPE_ONE_PHASER is True and mnIntensitySetting == 8:
                    StartOverload()
    # need way to keep trigger from causing
    # firing if in a setting adj menu
