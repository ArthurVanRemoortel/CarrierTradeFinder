from abc import ABC

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.layout import Layout
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.animation import Animation
from kivy.uix.scrollview import ScrollView
from kivy.properties import *
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.uix.textinput import TextInput
from time import sleep
from threading import Thread
from pathlib import Path
from tracker import TradeTracker
from kivy.clock import Clock
from kivy.uix.behaviors import ButtonBehavior
from collections import OrderedDict
from data_manager import DataManager
from tradedangerous import tradedb, tradeenv, commands, tradeexcept, tradecalc, prices

ROW_HEIGHT = 28


class BorderWidget(Widget):
    border_color = ListProperty([1, 0.5, 0, 1])
    border_size = NumericProperty(1)

    def __init__(self, **kwargs):
        super(BorderWidget, self).__init__(**kwargs)


class PaddedLayout:
    def __init__(self, **kwargs):
        super(PaddedLayout, self).__init__(**kwargs)


class BorderGridLayout(GridLayout, BorderWidget):
    def __init__(self, **kwargs):
        super(BorderGridLayout, self).__init__(**kwargs)


class BorderBoxLayout(BoxLayout, BorderWidget):
    def __init__(self, **kwargs):
        super(BorderBoxLayout, self).__init__(**kwargs)


class BorderBoxPaddedLayout(BoxLayout, BorderWidget, PaddedLayout):
    def __init__(self, **kwargs):
        super(BorderBoxPaddedLayout, self).__init__(**kwargs)


class ThemedPopup(BorderWidget, Popup):
    def __init__(self, **kwargs):
        super(ThemedPopup, self).__init__(**kwargs)


class BorderButton(BorderWidget, Button):
    def __init__(self, **kwargs):
        super(BorderButton, self).__init__(**kwargs)


class BorderLabel(BorderWidget, Label):
    def __init__(self, **kwargs):
        super(BorderLabel, self).__init__(**kwargs)


class BorderTextInput(BorderWidget, TextInput):
    def __init__(self, **kwargs):
        super(BorderTextInput, self).__init__(**kwargs)


class CopyButton(ButtonBehavior, Image, BorderWidget):
    def __init__(self, **kwargs):
        super(CopyButton, self).__init__(**kwargs)


class LeftAlign(Widget):
    offset = NumericProperty(10)

    def __init__(self, **kwargs):
        super(LeftAlign, self).__init__(**kwargs)


class LeftAlignLabel(Label, LeftAlign):
    def __init__(self, **kwargs):
        super(LeftAlignLabel, self).__init__(**kwargs)


class LeftAlignBorderLabel(Label, LeftAlign, BorderWidget):
    def __init__(self, **kwargs):
        super(LeftAlignBorderLabel, self).__init__(**kwargs)


class LeftAlignButton(Button, LeftAlign):
    def __init__(self, **kwargs):
        super(LeftAlignButton, self).__init__(**kwargs)


class CopyLabel(BoxLayout):
    label_text  = StringProperty("<<Default>>")
    font_size   = NumericProperty(12)

    def __init__(self, **kwargs):
        super(CopyLabel, self).__init__(**kwargs)


class Panel(BorderBoxLayout):
    def __init__(self, panel_index, **kwargs):
        super(Panel, self).__init__(**kwargs)
        self.body: BoxLayout = self.ids.body
        self.title_label: Label = self.ids.title_label
        self.close_button: Label = self.ids.close_button
        self.panel_index = panel_index

    def set_body(self, view):
        self.body.add_widget(view)

    def embed_commodity_tracker(self, commodity):
        CommodityTrackerView.make_embedded_tracker(commodity=commodity, panel=self)

    def embed_top_trades_view(self):
        TopTradesView.make_embedded_view(panel=self)

    def close(self):
        parent = self.parent
        self.parent.remove_widget(self)
        for other_panel in parent.children:
            if other_panel.panel_index == self.panel_index + 1:
                other_panel.panel_index -= 1

    def move_left(self):
        def do(_):
            if self.panel_index == len(self.parent.children) - 1:
                return
            parent = self.parent
            for other_panel in parent.children:
                if other_panel.panel_index == self.panel_index + 1:
                    other_panel.panel_index -= 1

            self.panel_index += 1
            parent.remove_widget(self)
            parent.add_widget(self, self.panel_index)
        Clock.schedule_once(do, 0.1)

    def move_right(self):
        def do(_):
            if self.panel_index == 0:
                return
            parent = self.parent
            for other_panel in parent.children:
                if other_panel.panel_index == self.panel_index - 1:
                    other_panel.panel_index += 1

            self.panel_index -= 1
            parent.remove_widget(self)
            parent.add_widget(self, self.panel_index)
        Clock.schedule_once(do, 0.1)


class TrackerSummaryRow(BorderBoxLayout):
    # tracker    = ObjectProperty(None)
    best_buy   = NumericProperty(0)
    best_sell  = NumericProperty(0)
    max_profit = NumericProperty(0)

    def __init__(self, **kwargs):
        super(TrackerSummaryRow, self).__init__(**kwargs)

    def update(self, tracker):
        self.best_buy = tracker.best_buy_location.price
        self.best_sell = tracker.best_sell_location.price
        self.max_profit = tracker.max_profit


class TrackerRow(BorderBoxLayout):
    font_size  = NumericProperty(12)
    row        = ObjectProperty(None)
    mode       = StringProperty()

    def __init__(self, **kwargs):
        super(TrackerRow, self).__init__(**kwargs)
        #self.add_widget(CopyLabel(text=f"{self.row.station.name()}"))
        #self.add_widget(Label(text=f"{self.row.price} CR"))


class MakeTrackerPopup(ThemedPopup):
    def __init__(self, callback=lambda *args: None):
        super(MakeTrackerPopup, self).__init__(size_hint=(0.5, None))
        self.spacing = 20
        self.title = "Make Tracker"
        self.height = 140
        self.callback = callback

        self.body = BorderBoxLayout(orientation="vertical")
        self.add_widget(self.body)

        self.input = BorderTextInput(font_size=18)
        self.input.text = "Agronomic Treatment"  # Dev default
        self.body.add_widget(self.input)
        self.body.add_widget(BorderButton(text="Confirm", on_press=self.confirm))

    def confirm(self, *args):
        self.dismiss()
        self.callback(self.input.text)


class TopTradesRow(BorderBoxLayout):
    font_size  = NumericProperty(12)
    item = ObjectProperty()
    max_profit = NumericProperty(0)

    def __init__(self, **kwargs):
        super(TopTradesRow, self).__init__(**kwargs)


class TopTradesView(BorderBoxLayout):
    def __init__(self, panel: Panel, show_n=20, auto_start=True):
        super(TopTradesView, self).__init__()
        self.panel: Panel = panel
        self.show_n: int = show_n
        self.panel.title_label.text = "Top trades"
        self.items = []
        if auto_start:
            def do(*_):
                tdb = tradedb.TradeDB()
                self.items = DataManager().find_trade_candidates(tdb)
            Thread(target=do).start()

        self.setup()

    def setup(self, *_):
        if not self.items:
            # self.ids.body.add_widget(Label(text="Loading...", size_hint_y=None, height=ROW_HEIGHT + 20, font_size=19))
            Clock.schedule_once(self.setup, timeout=1)
        else:
            for item in self.items:
                r = TopTradesRow(item=item[0], max_profit=item[1])
                self.ids.body.add_widget(r)

    @classmethod
    def make_embedded_view(cls, panel):
        tv = TopTradesView(panel)
        panel.set_body(tv)


class CommodityTrackerView(BorderBoxLayout):
    # buyers_section   = ObjectProperty(None)
    # sellers_section  = ObjectProperty(None)

    def __init__(self, panel: Panel, commodity, show_n=10, auto_start=True):
        super(CommodityTrackerView, self).__init__()
        self.panel: Panel = panel
        self.commodity: str = commodity
        self.show_n: int = show_n
        self.body: GridLayout = self.ids.body
        self.panel.title_label.text = "Commodity Tracker: "+commodity
        self.tracker: TradeTracker = None

        #self.buyers_section = self.ids.buyers_section

        self.buy_rows = OrderedDict()
        self.sell_rows = OrderedDict()

        if auto_start:
            self.start_tracker()

        self.setup()

    @classmethod
    def make_embedded_tracker(cls, panel, commodity):
        tv = CommodityTrackerView(panel, commodity)
        panel.set_body(tv)

    def start_tracker(self):
        self.tracker = TradeTracker(commodity=self.commodity)
        self.tracker.load()

    def setup(self, *_):
        # self.ids.body.clear_widgets()
        if not self.tracker.is_loaded:
            # self.ids.body.add_widget(Label(text="Loading...", size_hint_y=None, height=ROW_HEIGHT + 20, font_size=19))
            Clock.schedule_once(self.setup, timeout=1)
        else:
            # self.update()
            # Clock.schedule_once(self.update, timeout=3)
            self.ids.summary_row.update(self.tracker)
            for buy_row in self.tracker.buyers.rows[:self.show_n]:
                tr = TrackerRow(row=buy_row, mode="buy")
                self.ids.buyers_section.add_widget(tr)
                self.buy_rows[buy_row.station.dbname] = tr

            for sell_row in self.tracker.sellers.rows[:self.show_n]:
                tr = TrackerRow(row=sell_row, mode="sell")
                self.ids.sellers_section.add_widget(tr)
                self.sell_rows[sell_row.station.dbname] = tr


class TradeHelperRoot(BoxLayout, PaddedLayout):
    def __init__(self):
        super(TradeHelperRoot, self).__init__(spacing=10)
        self.orientation = 'vertical'

        self.top_bar      = BorderBoxLayout(orientation="vertical",   size_hint_y=None, height=50)
        self.action_bar   = BorderBoxLayout(orientation="horizontal", size_hint_y=None, height=50)
        self.body         = BoxLayout(orientation="horizontal", spacing=15)

        self.action_bar.add_widget(BorderButton(text="FC Trade Tracker", on_press=self.fc_trade_tracker_popup))
        self.action_bar.add_widget(BorderButton(text="Top Trades",       on_press=self.top_trade_tracker))
        self.action_bar.add_widget(BorderButton(text="Trends",           on_press=self.fc_trade_tracker_popup))

        self.add_widget(self.top_bar)
        self.add_widget(self.action_bar)
        self.add_widget(self.body)

        DataManager().check_db()

        # for n in range(5):
        #     self.add_tracker(str(n), source=str(n))

    def fc_trade_tracker_popup(self, _):
        MakeTrackerPopup(callback=self.fc_trade_tracker_for).open()

    def fc_trade_tracker_for(self, commodity):
        p = self.add_panel()
        p.embed_commodity_tracker(commodity=commodity)

    def top_trade_tracker(self, _):
        p = self.add_panel()
        p.embed_top_trades_view()

    def add_panel(self) -> Panel:
        p = Panel(panel_index=len(self.body.children))
        for other_panel in self.body.children:
            other_panel.panel_index += 1
        self.body.add_widget(p, 0)
        return p


class TradeHelper(App):
    Window.size = 2000, 1080
    Window.clearcolor = [0.07, 0.07, 0.07, 1]

    def build(self):
        return TradeHelperRoot()

    def on_stop(self):
        print('Closing everything')


if __name__ == '__main__':
    TradeHelper().run()
