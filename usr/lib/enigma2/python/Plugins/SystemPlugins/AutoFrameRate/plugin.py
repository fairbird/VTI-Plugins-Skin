# -*- coding: utf-8 -*-
from Components.ServiceEventTracker import ServiceEventTracker
from enigma import iPlayableService, iServiceInformation, eTimer
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.config import config
from Tools.HardwareInfoVu import HardwareInfoVu

class AutoFrameRate(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.lockTimer = eTimer()
		self.lockTimer.callback.append(self.unlockFramerateChange)
		self.framerate_change_is_locked = False
		self.locktimer_timeout = 60
		self.lastService = None
		self.__event_tracker = ServiceEventTracker(screen = self, eventmap = {iPlayableService.evVideoFramerateChanged: self.VideoFramerateChanged})

	def VideoFramerateChanged(self):
		if config.av.videoport.value in config.av.videomode:
			if config.av.videomode[config.av.videoport.value].value in config.av.videorate:
				service = session.nav.getCurrentService()
				cur_service_str = self.session.nav.getCurrentlyPlayingServiceReference().toString()
				if not (cur_service_str and self.lastService):
					self.lastService = cur_service_str
				if cur_service_str != self.lastService:
					self.lockTimer.stop()
					self.lastService = cur_service_str
					self.framerate_change_is_locked = False
				info = service and service.info()
				framerate = info and info.getInfo(iServiceInformation.sFrameRate)
				print "[AutoFramerate] got framerate: %i" % framerate
				if config.av.videorate[config.av.videomode[config.av.videoport.value].value].value == "multi":
					if framerate in  (59940, 60000):
						self.setVideoFrameRate('60')
					elif framerate in (23976, 24000):
						self.setVideoFrameRate('24')
					elif framerate in (29970, 30000):
						self.setVideoFrameRate('30')
					else:
						self.setVideoFrameRate('50')

	def setVideoFrameRate(self, rate):
		if self.framerate_change_is_locked:
			return
		try:
			f = open("/proc/stb/video/videomode", "r")
			videomode = f.read()
			f.close()
			f = open("/proc/stb/video/videomode_choices", "r")
			videomode_choices = f.read()
			f.close()
			videomode_choices = videomode_choices.split()
			if rate in ('24', '30'):
				multi_videomode = videomode
				if not videomode.endswith(rate):
					resolutions = ('1080', '2160', '720')
					for resolution in resolutions:
						if videomode.startswith(resolution):
							new_mode = resolution + 'p' + rate
							if new_mode in videomode_choices:
								multi_videomode = new_mode
								break
							else:
								for alternative_resolution in resolutions:
									if alternative_resolution != resolution:
										new_mode = alternative_resolution + 'p' + rate
										if new_mode in videomode_choices:
											multi_videomode = new_mode
											break
			else:
				f = open("/proc/stb/video/videomode_%shz" % rate, "r")
				multi_videomode = f.read()
				f.close()
			if videomode != multi_videomode:
				f = open("/proc/stb/video/videomode", "w")
				f.write(multi_videomode)
				f.close()
				print "[AutoFramerate] set resolution/framerate: %s" % multi_videomode
				self.framerate_change_is_locked = True
				self.lockTimer.startLongTimer(self.locktimer_timeout)
				self.doSeekRelative(2 * 9000)
		except IOError:
			print "error at reading/writing /proc/stb/video.. files"

	def unlockFramerateChange(self):
		self.lockTimer.stop()
		self.framerate_change_is_locked = False

	def getSeek(self):
		service = self.session.nav.getCurrentService()
		if service is None:
			return None
		seek = service.seek()
		if seek is None or not seek.isCurrentlySeekable():
			return None
		return seek

	def doSeekRelative(self, pts):
		seekable = self.getSeek()
		if seekable is None:
			return
 		seekable.seekRelative(pts<0 and -1 or 1, abs(pts))

def autostart(reason, **kwargs):
	global session
	if kwargs.has_key("session") and reason == 0:
		session = kwargs["session"]
		AutoFrameRate(session)

def Plugins(**kwargs):
	return [PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc = autostart)]
