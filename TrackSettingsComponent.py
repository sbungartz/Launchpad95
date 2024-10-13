import Live
from math import ceil
from _Framework.CompoundComponent import CompoundComponent
from _Framework.SubjectSlot import subject_slot
from _Framework.ButtonElement import ButtonElement
from _Framework.Util import find_if, clamp
from _Framework.Util import const, print_message
from _Framework.Dependency import depends

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
	def __init__(self, root, has_sub_items=True):
		self._root = root
		self._selected_sub_index = 0
		self._has_sub_items = has_sub_items
		self._selected_page_index = 0
	
	@property
	def name(self):
		return self._root.name
	
	@property
	def has_sub_items(self):
		return self._has_sub_items
	
	@property
	def sub_items(self):
		if self.has_sub_items:
			return self._root.children
		else:
			return []
	
	@property
	def selected_sub_index(self):
		return self._selected_sub_index
	
	@selected_sub_index.setter
	def selected_sub_index(self, value):
		self._selected_sub_index = value
		self._selected_page_index = 0
	
	@property
	def selected_sub_item(self):
		if self.has_sub_items:
			return self.sub_items[self.selected_sub_index]
		else:
			return self._root
	
	@property
	def num_sub_category_rows(self):
		return ceil(len(self.sub_items) / 8)
	
	@property
	def num_main_item_rows(self):
		return 8 - 1 - self.num_sub_category_rows
	
	@property
	def num_pages(self):
		return ceil(len(self.selected_sub_item.children) / 8 / self.num_main_item_rows)
	
	@property
	def selected_page_index(self):
		return self._selected_page_index

	def move_page(self, offset):
		next_page = self.selected_page_index + offset
		if 0 <= next_page < self.num_pages:
			self._selected_page_index = next_page

class VirtualBrowserSubItem:
	def __init__(self, name, children):
		self._name = name
		self._children = children
	
	@property
	def name(self):
		return self._name
	
	@property
	def children(self):
		return self._children

class SourceBasedBrowserTreeItem(BrowserTreeItem):
	def __init__(self, root):
		super(SourceBasedBrowserTreeItem, self).__init__(root)
		self._sources = sorted(list({item.source for item in root.children if item.is_loadable}))
		self._virtual_sub_items = [VirtualBrowserSubItem(source, [item for item in root.children if item.source == source and item.is_loadable]) for source in self._sources]
	
	@property
	def sub_items(self):
		return self._virtual_sub_items

	@property
	def selected_sub_item(self):
		return self._virtual_sub_items[self.selected_sub_index]

class TrackSettingsComponent(CompoundComponent):
	PAGE_COLORS = ["Browser.Page1", "Browser.Page2", "Browser.Page3", "Browser.Page4", "Browser.Page5", "Browser.Page6", "Browser.Page7", "Browser.Page8", "Browser.Page9"]

	def __init__(self, matrix, side_buttons, top_buttons, control_surface, note_repeat):
		super(TrackSettingsComponent, self).__init__()
		self._control_surface = control_surface
		self._matrix = None
		self._side_buttons = side_buttons
		self._remaining_buttons = []
		self._prev_page_button = None
		self._next_page_button = None
		self._track_controller = None
		self._browser = Live.Application.get_application().browser
		self._main_items = [
			SourceBasedBrowserTreeItem(self._browser.drums),
			BrowserTreeItem(self._browser.sounds),
			*[BrowserTreeItem(color, has_sub_items=False) for color in self._browser.colors],
		]
		self._selected_main_item_index = 0
		
		self._track_controller = self.register_component(TrackControllerComponent(control_surface = control_surface, implicit_arm = True))
		self._track_controller.set_enabled(False)
		
		#Clip navigation buttons
		self.set_prev_page_button(top_buttons[0])
		self.set_next_page_button(top_buttons[1])
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
	
	def set_next_page_button(self, button=None):
		assert isinstance(button, (ButtonElement, type(None)))
		if self._next_page_button != None:
			self._next_page_button.remove_value_listener(self._next_page_value)
		self._next_page_button = button
		if self._next_page_button != None:
			self._next_page_button.add_value_listener(self._next_page_value, identify_sender=True)
			self._next_page_button.turn_off()
		
	def _next_page_value(self, value, sender):
		assert (self._next_page_button != None)
		assert (value in range(128))
		if self.is_enabled():
			if not sender.is_momentary() or value is not 0:
				self.selected_main_item.move_page(1)
				self._control_surface.show_message(f"Showing page {self.selected_main_item.selected_page_index}")
				self.update()
	
	def set_prev_page_button(self, button=None):
		assert isinstance(button, (ButtonElement, type(None)))
		if self._prev_page_button != None:
			self._prev_page_button.remove_value_listener(self._prev_page_value)
		self._prev_page_button = button
		if self._prev_page_button != None:
			self._prev_page_button.add_value_listener(self._prev_page_value, identify_sender=True)
			self._prev_page_button.turn_off()
		
	def _prev_page_value(self, value, sender):
		assert (self._prev_page_button != None)
		assert (value in range(128))
		if self.is_enabled():
			if not sender.is_momentary() or value is not 0:
				self.selected_main_item.move_page(-1)
				self._control_surface.show_message(f"Showing page {self.selected_main_item.selected_page_index}")
				self.update()

	def update(self):
		if self.is_enabled():
			if self._track_controller != None:
				self._track_controller.set_enabled(True)

			self._update_page_buttons()
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
			elif y < self.selected_main_item.num_sub_category_rows + 1:
				sub_category_index = (y - 1) * 8 + x
				self.selected_main_item.selected_sub_index = sub_category_index
				self._control_surface.show_message(f"Selected {self.selected_sub_item.name}")
			else:
				page_offset = 8 * self.selected_main_item.num_main_item_rows * self.selected_main_item.selected_page_index
				leaf_item_index = page_offset + (y - 1 - self.selected_main_item.num_sub_category_rows) * 8 + x
				if leaf_item_index < len(self.selected_sub_item.children):
					item = self.selected_sub_item.children[leaf_item_index]
					self._control_surface.show_message(f"Selected {item.name} from {item.source}")
					#self._browser.preview_item(item)
					self._browser.load_item(item)
			self.update()

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
	
	def _get_current_device_name(self):
		device = self.song().view.selected_track.view.selected_device
		return device.name if device is not None else None

	@depends(log_message=(const(print_message)))
	def _update_matrix(self, log_message=None):
		current_device_name = self._get_current_device_name()
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
					page_offset = 8 * self.selected_main_item.num_main_item_rows * self.selected_main_item.selected_page_index
					leaf_item_index = page_offset + (y - 1 - self.selected_main_item.num_sub_category_rows) * 8 + x
					if leaf_item_index < len(self.selected_sub_item.children):
						item = self.selected_sub_item.children[leaf_item_index]
						button.set_enabled(True)
						colors = self.PAGE_COLORS[self.selected_main_item.selected_page_index % len(self.PAGE_COLORS)]
						button.set_on_off_values(colors)
						if item.name[:-4] == current_device_name: # item.name includes suffix .adv or .adg so we strip the last 4 characters
							button.turn_on()
						else:
							button.turn_off()
	
	def _update_page_buttons(self):
		if self.is_enabled() and self._next_page_button and self._prev_page_button:
			self._next_page_button.set_enabled(True)
			self._prev_page_button.set_enabled(True)
			self._next_page_button.set_on_off_values("DefaultButton")
			self._prev_page_button.set_on_off_values("DefaultButton")
			selected_page_index = self.selected_main_item.selected_page_index
			num_pages = self.selected_main_item.num_pages
			
			if selected_page_index > 0:
				self._prev_page_button.turn_on()
			else:
				self._prev_page_button.turn_off()
			
			if selected_page_index < num_pages - 1:
				self._next_page_button.turn_on()
			else:
				self._next_page_button.turn_off()
