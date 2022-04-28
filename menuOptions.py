# all lists of options are arrays of RGB colors
class MenuOptions:
	Frequency = [(255, 0, 0), (255, 32, 0), (255, 64, 0), (255, 0, 32), (255, 0, 64), (255, 64, 64)]
	Autofire = (255, 48, 0)
	Volume = [(0, 255, 0), (0, 204, 0), (0, 160, 0), (0, 96, 0), (0, 64, 0), (0, 32, 0)]
	Orientation = [(255, 255, 0), (0, 0, 255)]
	SettingBrightness = [(0, 0, 255), (0, 0, 204), (0, 0, 160), (0, 0, 96), (0, 0, 64), (0, 0, 32)]
	BeamBrightness = [(255, 0, 255), (204, 0, 204), (160, 0, 160), (96, 0, 96), (64, 0, 64), (32, 0, 32)]	
	Overload = (255, 0, 0)
	Exit = (160, 160, 160)
	# visible beam frequency should use the alternate color on "flicker"?
    # otherwise beam colors might look out of place?
	FreqSup = [(0, 0, 0), (0, 64, 0), (0, 128, 0), (0, 0, 64), (0, 0, 128), (0, 128, 128)]
