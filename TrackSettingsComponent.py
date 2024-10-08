import Live
from math import ceil
from _Framework.CompoundComponent import CompoundComponent
from _Framework.SubjectSlot import subject_slot
from _Framework.ButtonElement import ButtonElement
from _Framework.Util import find_if, clamp
try:
	from itertools import imap
except ImportError:
	# Python 3...
	imap=map
	
from .TrackControllerComponent import TrackControllerComponent
from .ScaleComponent import ScaleComponent,CIRCLE_OF_FIFTHS,MUSICAL_MODES,KEY_NAMES
try:
	from .Settings import Settings
except ImportError:
	from .Settings import *
	
#fix for python3
try:
	xrange
except NameError:
	xrange = range

from _Framework.ButtonMatrixElement import ButtonMatrixElement
KEY_MODE = 0
SCALE_TYPE_MODE = 1

class BrowserTreeItem:
	def __init__(self, root):
		self._root = root
		self._selected_sub_index = 0
	
	@property
	def name(self):
		return self._root.name
	
	@property
	def sub_items(self):
		return self._root.children
	
	@property
	def selected_sub_index(self):
		return self._selected_sub_index
	
	@selected_sub_index.setter
	def selected_sub_index(self, value):
		self._selected_sub_index = value
	
	@property
	def selected_sub_item(self):
		return self.sub_items[self.selected_sub_index]
	
	@property
	def num_sub_category_rows(self):
		return ceil(len(self.sub_items) / 8)

class TrackSettingsComponent(CompoundComponent):

	def __init__(self, matrix, side_buttons, top_buttons, control_surface, note_repeat):
		super(TrackSettingsComponent, self).__init__()
		self._control_surface = control_surface
		self._matrix = None
		self._side_buttons = side_buttons
		self._remaining_buttons = []
		self._track_controller = None
		self._browser = Live.Application.get_application().browser
		self._main_items = [
			BrowserTreeItem(self._browser.sounds),
		]
		self._selected_main_item_index = 0
		
		self._track_controller = self.register_component(TrackControllerComponent(control_surface = control_surface, implicit_arm = True))
		self._track_controller.set_enabled(False)
		
		#Clip navigation buttons
		self._track_controller.set_prev_track_button(top_buttons[2])
		self._track_controller.set_next_track_button(top_buttons[3])
		
		#Clip edition buttons
		self._track_controller.set_undo_button(side_buttons[1])
		#self._track_controller.set_start_stop_button(side_buttons[4])
		#self._track_controller.set_lock_button(side_buttons[5])
		#self._track_controller.set_solo_button(side_buttons[6])
		#self._track_controller.set_session_record_button(side_buttons[7])
		
		self.set_matrix(matrix)		

	def set_enabled(self, enabled):
		CompoundComponent.set_enabled(self, enabled)
		if self._track_controller != None:
			self._track_controller.set_enabled(enabled)
			#self._track_controller._do_implicit_arm(enabled)
			self._track_controller.set_enabled(enabled)
			
		if enabled:
			self.on_selected_track_changed()
		else:
			self._browser.stop_preview()

	def update(self):
		if self.is_enabled():
			if self._track_controller != None:
				self._track_controller.set_enabled(True)

			self._update_matrix()  

	# Refresh matrix and its listener
	def set_matrix(self, matrix):
		self._matrix = matrix
		if matrix:
			matrix.reset()
		if (matrix != self._matrix):
			if (self._matrix != None):
				self._matrix.remove_value_listener(self._on_matrix_value)
		self._matrix = matrix
		if (self._matrix != None):
			self._matrix.add_value_listener(self._on_matrix_value)
		self._update_matrix()
	
	def _on_matrix_value(self, value, x, y, is_momentary):
		if self.is_enabled() and value > 0:
			self._control_surface.show_message(f"Clicked on {x}, {y}")
			if y == 0:
				if x < len(self._main_items):
					self._selected_main_item_index = x
					self._control_surface.show_message(f"Selected {self.selected_main_item.name}")
					self.update()
			elif y < self.selected_main_item.num_sub_category_rows + 1:
				sub_category_index = (y - 1) * 8 + x
				self.selected_main_item.selected_sub_index = sub_category_index
				self._control_surface.show_message(f"Selected {self.selected_sub_item.name}")
				self.update()
			else:
				leaf_item_index = (y - 1 - self.selected_main_item.num_sub_category_rows) * 8 + x
				if leaf_item_index < len(self.selected_sub_item.children):
					item = self.selected_sub_item.children[leaf_item_index]
					self._control_surface.show_message(f"Selected {item.name}, selected = {item.is_selected}")
					#self._browser.preview_item(item)
					self._browser.load_item(item)

	#Listener, setup drumrack scale mode and load the selected scale for Track/Cip (Disabled)
	def on_selected_track_changed(self):
		self._browser.filter_type = Live.Browser.FilterType.midi_track_devices
		self.update()
	
	@property
	def selected_main_item(self):
		return self._main_items[self._selected_main_item_index]
	
	@property
	def selected_sub_item(self):
		return self.selected_main_item.selected_sub_item

	def _update_matrix(self):
		if self.is_enabled() and self._matrix:
			for button, (x, y) in self._matrix.iterbuttons():
				button.set_enabled(False)
				button.set_light("DefaultButton.Disabled")
				if y == 0:
					if x < len(self._main_items):
						main_item = self._main_items[y]
						button.set_enabled(True)
						button.set_on_off_values("QuickScale.Quant.On", "QuickScale.Quant.Off")
						if x == self._selected_main_item_index:
							button.turn_on()
						else:
							button.turn_off()
				elif y - 1 < self.selected_main_item.num_sub_category_rows:
					sub_category_index = (y - 1) * 8 + x
					if sub_category_index < len(self.selected_main_item.sub_items):
						button.set_enabled(True)
						button.set_on_off_values("Mode.Session.On", "Mode.Session.Off")
						if sub_category_index == self.selected_main_item.selected_sub_index:
							button.turn_on()
						else:
							button.turn_off()
				else:
					leaf_item_index = (y - 1 - self.selected_main_item.num_sub_category_rows) * 8 + x
					if leaf_item_index < len(self.selected_sub_item.children):
						button.set_enabled(True)
						button.set_on_off_values("Mode.Drum.On", "Mode.Drum.Off")
						button.turn_off()