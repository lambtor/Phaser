Purpose of this project is to code a phaser prop from star trek TNG / DS9 / VOY / LD.<br>
This will try to support both the 2 row, 16 intensity setting type 2 phaser and the 1 row, 8 intensity setting type 1.<br>
This is coded in circuitpython and initially intended to use the adafruit rp2040 board with a battery backpack. Settings and beam neopixels, buttons used will be on a custom designed PCB.
<br>
Project scope / intended features<br>
<ul>
	<li>
3 buttons: 2 for settings and 1 main trigger</li>
<li>firing sound mapped to button press. keep firing sound playing in loop while trigger held down.  need 2 sound files to do this, with warmup sound separate from active firing.  active firing sound must be loopable.</li>
<li>have setting buttons cause setting change sound to play</li>
<li>2 chains of neopixels: 1 for settings and 1 for beam</li>
<li>have neopixels for beam flicker slightly during firing</li>
<li>display current battery level in setting neopixel row when battery is charging - animated blue?</li>
<li>support a "warning shot" mode, where a single white led is lit in setting bar, and firing in this mode has beam at its dimmest with sound at its loudest</li>
<li>for type 2 (16 setting leds), have settings 1-8 light only 1 row from left to right as all green. for settings 9-16, light top row red while also fading bottom row from green to orange.<br>
	for type 1 (8 setting leds), have settings 1-8 fade from green (at 1) to red (at 8).</li>
<li>ability to set phaser to overload - hold down setting increase button for 3 seconds while setting is already at maximum. play "overload" sound and have all setting LEDs flashing red at a gradually increasing rate over 10 seconds before playing an "overload explosion" sound. after overload routine finishes, set phaser to sleep mode.</li>
<li>ability to activate wesley crusher's "autofire" mode - hold setting decrease button for 3 seconds.  this mode, when active, should have current intensity setting leds flash. this mode should be deactivated when either setting button has been pressed, and setting leds should return to solid on to reflect that.</li>
<li>sleep mode. when no buttons on the phaser have been pressed for a certain amount of time (2 minutes - this is a constant defined at the top of the code), all lights turn off and power use is minimized until a button has been pressed to wake again.</li>
</ul><br>
potential functions:<br>
"grime washing mode"?  not sure what this would be, or how it could be displayed in settings bar.<br>
method of changing phaser from "left handed" to "right handed" mode.  this would change how setting buttons behave and order of setting led pattern<br>
<br>
potential non-canon settings: (need to figure out if these should persist between full powercycles)<br>
beam brightness - including an "off" option, if anybody uses this for filming and wanted to add beam in post prod?<br>
setting led row brightness<br>
sound effect volume level<br>
reset all settings to default<br>
<br>References:<br>
https://learn.adafruit.com/mp3-playback-rp2040
