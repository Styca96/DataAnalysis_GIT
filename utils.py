#!/usr/bin/env python
"""
Permette di analizzare file *.xlsx
Analisi dei dati di Prove vita
"""

import math
import platform
import shutil
import textwrap
import tkinter as tk
from ctypes import Structure, byref, sizeof, windll, wintypes
from functools import partial
from pathlib import Path, PureWindowsPath
from typing import TYPE_CHECKING, Any, Callable

import pandas as pd
import tksvg
import ttkbootstrap as ttk
import ttkbootstrap.dialogs as ttk_dial
import ttkbootstrap.utility as ttkutility
import win32gui
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.localization import MessageCatalog
from ttkbootstrap.style import Bootstyle
from ttkbootstrap.themes import user

if TYPE_CHECKING:
    from Test_Analysis import Controller

# from tkinter import font  # ttk
# from tkinter import messagebox

APP_PATH = f"{PureWindowsPath(__file__).parent}"

tab_csv = partial(pd.read_csv,
                  sep="\t",
                  header=0,
                  index_col=False,
                  skipinitialspace=False,
                  skip_blank_lines=False,
                  keep_default_na=True,
                  encoding="cp1252",
                  encoding_errors="ignore",
                  # parse_dates=[["Date", "Time"]],
                  # dayfirst=True,
                  on_bad_lines="skip",
                  engine="python",
                  )
comma_csv = partial(pd.read_csv,
                    sep=',',
                    index_col=False,
                    skipinitialspace=True,
                    skip_blank_lines=False,
                    encoding="cp1252",
                    encoding_errors="ignore",
                    # parse_dates=[["Date", "Time"]],
                    # dayfirst=True,
                    # on_bad_lines='skip',
                    engine="python"
                    )
excel_xlsx = partial(pd.read_excel,
                     sheet_name=0,
                     # parse_dates=[["Date", "Time"]],
                     engine=None,
                     )
read_functions = {tab_csv, comma_csv, excel_xlsx}


def import_user_themes():
    """Import user themes into the user.py file. Any existing data
    in the user.py file will be overwritten."""
    outpath = Path(user.__file__)
    inpath = APP_PATH + "/rsc/user.py"
    shutil.copyfile(inpath, outpath)


def retag(tag, *args: tk.Widget):
    '''Add the given tag as the first bindtag for every widget passed in'''
    for widget in args:
        widget.bindtags((tag,) + widget.bindtags())


def all_children(wid: tk.Widget):
    """Return a list of all Widget's children"""
    _list = wid.winfo_children()

    for item in _list:
        if item.winfo_children():
            _list.extend(all_children(item))

    return _list


# ----- GUI main Class ---- #
class Statusbar(ttk.Frame):
    """###Status bar di aggiornamento"""

    def __init__(self, parent):
        super().__init__(parent, width=1000)
        self.parent = parent
        fontMenu = ("Helvetica", 12)

        self.status = tk.StringVar()
        self.status.set("DataAnalysis")

        self.label = ttk.Label(
            self,
            textvariable=self.status,
            foreground="black",
            background="lightgrey",
            font=fontMenu,
            anchor="sw",
        )
        self.label.pack(fill="x", side=tk.BOTTOM)

    def update_status(self, *args):
        """Aggiorna lo stato.

        Se vengono passati due *args di cui il primo è 'bool'
        aggiorna la barra con il secondo
        """
        if isinstance(args[0], bool):
            self.status.set(args[1])
        else:
            self.status.set("DataAnalysis - ")


class Menubar:
    """### APP MENU"""

    def __init__(self, parent: ttk.Window):
        fontMenu = ("ubuntu", 10)
        self.parent = parent

        menubar = ttk.Menu(parent, font=fontMenu)
        parent.config(menu=menubar)

        # file dropdown
        file_dropdown = ttk.Menu(menubar, font=fontMenu, tearoff=0)
        file_dropdown.add_command(
            label="Select Files",
            accelerator="Ctrl+Alt+O",
            command=self.file_select_file,
        )
        file_dropdown.add_separator()
        file_dropdown.add_command(
            label="Chiudi", accelerator="Ctrl+Esc", command=self.destroy
        )
        # file dropdown
        about_dropdown = ttk.Menu(menubar, font=fontMenu, tearoff=0)
        about_dropdown.add_command(label="About", command=self.about)
        about_dropdown.add_separator()
        about_dropdown.add_command(
            label="Note Rilascio", command=self.show_release_notes
        )
        # export dropdown
        export_dropdown = ttk.Menu(menubar, font=fontMenu, tearoff=0)
        export_lifetest = ttk.Menu(export_dropdown, font=fontMenu, tearoff=0)
        export_thermal = ttk.Menu(export_dropdown, font=fontMenu, tearoff=0)
        export_lifetest.add_command(
            label="Export Distribution Data",
            accelerator="Ctrl+S",
            command=self.export_distribution_click,
        )
        export_lifetest.add_command(
            label="Export All",
            accelerator="Ctrl+Alt+S",
            command=self.export_all_result_click,
        )
        export_thermal.add_command(
            label="Selected data - New File",
            command=self.exp_data,
            accelerator="Ctrl+N",
        )
        export_thermal.add_command(
            label="Selected data - Merge",
            command=self.merge_exp_data,
            accelerator="Ctrl+Alt+N",
        )
        export_dropdown.add_cascade(label="Export - LifeTest", menu=export_lifetest)
        export_dropdown.add_cascade(label="Export - Thermal", menu=export_thermal)
        # other dropdown
        other_dropdown = ttk.Menu(menubar, font=fontMenu, tearoff=0)
        # review_dropdown = ttk.Menu(other_dropdown, font=fontMenu, tearoff=0)
        # edit_dropdown = ttk.Menu(other_dropdown, font=fontMenu, tearoff=0)
        # review_dropdown.add_command(
        #     label="Timeseries",
        #     command=self.review_timeseries_click,
        # )
        # review_dropdown.add_command(
        #     label="Distribution",
        #     command=self.review_distribution_click,
        # # )
        # edit_dropdown.add_command(
        #     label="Edita titolo e assi",
        #     command=self.modify_ax
        # )
        # edit_dropdown.add_command(
        #     label="Edita legenda",
        #     command=self.modify_legend
        # )
        # other_dropdown.add_cascade(label="LifeTest - Review", menu=review_dropdown)
        # other_dropdown.add_cascade(label="Thermal - Edit", menu=edit_dropdown)
        # option dropdown
        option_dropdown = ttk.Menu(menubar, font=fontMenu, tearoff=0)
        theme_dropdown = ttk.Menu(option_dropdown, font=fontMenu, tearoff=0)
        self.theme = tk.IntVar(value=0)
        theme_dropdown.add_radiobutton(label='light', var=self.theme,
                                       value=0, command=self.change_theme)
        theme_dropdown.add_radiobutton(label='dark', var=self.theme,
                                       value=1, command=self.change_theme)
        option_dropdown.add_cascade(label="Theme", menu=theme_dropdown)
        # menubar
        menubar.add_cascade(label="File", menu=file_dropdown)
        menubar.add_cascade(label="Export", menu=export_dropdown)
        menubar.add_cascade(label="Other", menu=other_dropdown)
        menubar.add_cascade(label="Option", menu=option_dropdown)
        menubar.add_cascade(label="About", menu=about_dropdown)

    def set_controller(self, controller):
        """Set the controller=controller"""
        self.controller: Controller = controller

    def file_select_file(self):
        """Seleziona file"""
        if self.controller:
            self.controller.select_files()

    def destroy(self):
        """Destroy all item"""
        for child in self.parent.winfo_children():
            child.destroy()
        self.parent.destroy()
        self.parent.quit()

    def about(self):
        """About this application"""
        box_title = "About this application"
        box_message = ("App for data analysys on LifeTest or ThermalTest\n"
                       "by: Samuele Gonnelli")
        Messagebox.show_info(title=box_title, message=box_message)

    def show_release_notes(self):
        """Show Release Note"""
        box_title = "Note di Rilascio"
        box_message = "Version 1.0 - ReView"
        Messagebox.show_info(title=box_title, message=box_message)

    def export_distribution_click(self):
        """Export only distribution result"""
        if self.controller:
            self.controller.export_all_option(False)

    def export_all_result_click(self):
        """Export all result"""
        if self.controller:
            self.controller.export_all_option(True)

    def exp_data(self):
        """Export thermal result"""
        if self.controller:
            self.controller.export_thermal_data(False)

    def merge_exp_data(self):
        """Export and merge thermal data"""
        if self.controller:
            self.controller.export_thermal_data(True)

    def review_timeseries_click(self):
        """Review TimeSeries result"""
        if self.controller:
            self.controller.review_timeseries()

    def review_distribution_click(self):
        """Review distributions result"""
        if self.controller:
            self.controller.review_distribution()

    def modify_ax(self):
        """Edit Thermal's ax"""
        if self.controller:
            self.controller.edit_ax()

    def modify_legend(self):
        """Modify Thermal's legend"""
        if self.controller:
            self.controller.edit_legend()

    def change_theme(self):
        """Choose light or dark theme"""
        if self.theme.get():
            self.parent.style.theme_use("cyborg")
            # self.parent.style.theme_use("darkly")
            self.parent._style_mod()
        else:
            self.parent.style.theme_use("abbtheme")


# ----- View Class ---- #
class AutoHideScrollbar(ttk.Scrollbar):
    """Scrollbar that automatically hides when not needed."""

    def __init__(self, master=None, **kwargs):
        """
        Create a scrollbar.

        :param master: master widget
        :type master: widget
        :param kwargs: options to be passed on to the :class:`ttk.Scrollbar`
        initializer
        """
        ttk.Scrollbar.__init__(self, master=master, bootstyle="round",
                               **kwargs)
        self._pack_kw = {}
        self._place_kw = {}
        self._layout = 'place'

    def set(self, lo, hi):
        """
        Set the fractional values of the slider position.

        :param lo: lower end of the scrollbar (between 0 and 1)
        :type lo: float
        :param hi: upper end of the scrollbar (between 0 and 1)
        :type hi: float
        """
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            if self._layout == 'place':
                self.place_forget()
            elif self._layout == 'pack':
                self.pack_forget()
            else:
                self.grid_remove()
        else:
            if self._layout == 'place':
                self.place(**self._place_kw)
            elif self._layout == 'pack':
                self.pack(**self._pack_kw)
            else:
                self.grid()
        ttk.Scrollbar.set(self, lo, hi)

    def _get_info(self, layout):
        """Alternative to pack_info and place_info in case of bug."""
        info = str(self.tk.call(layout, 'info', self._w)).split("-")
        dic = {}
        for i in info:
            if i:
                key, val = i.strip().split()
                dic[key] = val
        return dic

    def place(self, **kw):
        """
        Place a widget in the parent widget.

        :param in_: master relative to which the widget is placed
        :type in_: widget
        :param x: locate anchor of this widget at position x of master
        :type x: int
        :param y: locate anchor of this widget at positiony of master
        :type y: int
        :param relx: locate anchor of this widget between 0 and 1
                      relative to width of master (1 is right edge)
        :type relx: float
        :param rely: locate anchor of this widget between 0 and 1
                      relative to height of master (1 is bottom edge)
        :type rely: float
        :param anchor: position anchor according to given direction
                        ("n", "s", "e", "w" or combinations)
        :type anchor: str
        :param width: width of this widget in pixel
        :type width: int
        :param height: height of this widget in pixel
        :type height: int
        :param relwidth: width of this widget between 0.0 and 1.0
                          relative to width of master (1.0 is the same width
                          as the master)
        :type relwidth: float
        :param relheight: height of this widget between 0.0 and 1.0
                           relative to height of master (1.0 is the same
                           height as the master)
        :type relheight: float
        :param bordermode: "inside" or "outside": whether to take border width
        of master widget into account
        :type bordermode: str
        """
        ttk.Scrollbar.place(self, **kw)
        try:
            self._place_kw = self.place_info()
        except TypeError:
            # bug in some tkinter versions
            self._place_kw = self._get_info("place")
        self._layout = 'place'

    def pack(self, **kw):
        """
        Pack a widget in the parent widget.

        :param after: pack it after you have packed widget
        :type after: widget
        :param anchor: position anchor according to given direction
                        ("n", "s", "e", "w" or combinations)
        :type anchor: str
        :param before: pack it before you will pack widget
        :type before: widget
        :param expand: expand widget if parent size grows
        :type expand: bool
        :param fill: "none" or "x" or "y" or "both": fill widget if widget
        grows
        :type fill: str
        :param in_: widget to use as container
        :type in_: widget
        :param ipadx: add internal padding in x direction
        :type ipadx: int
        :param ipady: add internal padding in y direction
        :type ipady: int
        :param padx: add padding in x direction
        :type padx: int
        :param pady: add padding in y irection
        :type pady: int
        :param side: "top" (default), "bottom", "left" or "right": where to add
        this widget
        :type side: str
        """
        ttk.Scrollbar.pack(self, **kw)
        try:
            self._pack_kw = self.pack_info()
        except TypeError:
            # bug in some tkinter versions
            self._pack_kw = self._get_info("pack")
        self._layout = 'pack'

    def grid(self, **kw):
        """
        Position a widget in the parent widget in a grid.

        :param column: use cell identified with given column (starting with 0)
        :type column: int
        :param columnspan: this widget will span several columns
        :type columnspan: int
        :param in_: widget to use as container
        :type in_: widget
        :param ipadx: add internal padding in x direction
        :type ipadx: int
        :param ipady: add internal padding in y direction
        :type ipady: int
        :param padx: add padding in x direction
        :type padx: int
        :param pady: add padding in y irection
        :type pady: int
        :param row: use cell identified with given row (starting with 0)
        :type row: int
        :param rowspan: this widget will span several rows
        :type rowspan: int
        :param sticky: "n", "s", "e", "w" or combinations: if cell is
                       larger on which sides will this widget stick to
                       the cell boundary
        :type sticky: str
        """
        ttk.Scrollbar.grid(self, **kw)
        self._layout = 'grid'


class ScrolledListbox(ttk.Frame):
    """Simple :class:`tk.Listbox` with an added scrollbar."""

    def __init__(self, master=None, compound=tk.RIGHT, **kwargs):
        """
        Create a Listbox with a vertical scrollbar.

        :param master: master widget
        :type master: widget
        :param compound: side for the Scrollbar to be on
        (:obj:`tk.LEFT` or :obj:`tk.RIGHT`)
        :type compound: str
        :param kwargs: keyword arguments passed on to the :class:`tk.Listbox`
        initializer
        """
        super().__init__(master)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.listbox = tk.Listbox(self, **kwargs)
        self.scrollbar = AutoHideScrollbar(self, orient="vertical",
                                           command=self.listbox.yview)

        self.config_listbox(yscrollcommand=self.scrollbar.set)
        if compound is not tk.LEFT and compound is not tk.RIGHT:
            raise ValueError(f"Invalid compound value passed: {compound}")
        self.__compound = compound
        self._grid_widgets()

    def _grid_widgets(self):
        """Puts the two whole widgets in the correct position depending on
        compound."""
        scrollbar_column = 0 if self.__compound is tk.LEFT else 2
        self.listbox.grid(row=0, column=1, sticky="nswe")
        self.scrollbar.grid(row=0, column=scrollbar_column, sticky="ns")

    def config_listbox(self, *args, **kwargs):
        """Configure resources of the Listbox widget."""
        self.listbox.configure(*args, **kwargs)


class Checklist(ttk.Frame):
    """Checklist with Available and Selected Items"""
    values = []

    def __init__(self, master: tk.Misc | None = ..., filter: bool = False, **kwargs) -> None:
        """Create a Checklist create with double Listbox for Available and
        Selected items.\n
        Args:
            master (tk.Misc | None, optional): _description_. Defaults to ....
            filter (bool, optional): If show filter entry for available items.
            Defaults to False.
            **kwargs: options to be passed on to the :class:`ttk.Frame`
        initializer
        """
        super().__init__(master, **kwargs)
        self.rowconfigure(1, weight=1, minsize=40)

        if filter:
            filter_frm = ttk.Frame(self)
            filter_frm.grid(row=0, column=0, columnspan=2)
            self.__filter_img = tksvg.SvgImage(
                file=f"{APP_PATH}/rsc/filter.svg"
            )
            ttk.Label(filter_frm, text="Filter: ").grid(row=0, column=0)
            self.search_ent = ttk.Entry(filter_frm)
            self.search_ent.grid(row=0, column=1)
            self.search_ent.bind('<KeyRelease>', self.handle_keyrelease)
            ttk.Label(filter_frm, image=self.__filter_img
                      ).grid(row=0, column=2)

        ttk.Label(self, text="Available Items:", anchor="w"
                  ).grid(row=1, column=0, sticky="ew", pady=2, padx=2)
        self.available_items = tk.StringVar()
        self._listbox = ScrolledListbox(self,
                                        selectmode=tk.MULTIPLE,
                                        listvariable=self.available_items,
                                        )
        self._listbox.grid(row=2, column=0, sticky="nsew")
        self._listbox.listbox.bind("<<ListboxSelect>>", self._on_select)
        self._listbox.listbox.config(exportselection=False)
        self.__all_btn_img = tksvg.SvgImage(
            file=f"{APP_PATH}/rsc/arrow-right.svg"
            )
        self.all_btn = ttk.Button(self, bootstyle="info",
                                  image=self.__all_btn_img,
                                  text="Select all", compound="right",
                                  command=self._all_none)
        self.all_btn.grid(row=3, column=0, pady=10, sticky="w")

        ttk.Label(self, text="Selected Items:", anchor="w"
                  ).grid(row=1, column=1, sticky="ew", pady=2, padx=25)
        self.selected = tk.StringVar()
        self._slct_lstbx = ScrolledListbox(self,
                                           listvariable=self.selected,
                                           exportselection=False
                                           )
        self._slct_lstbx.grid(row=2, column=1, padx=25, sticky="nsew")
        self.__remove_btn_img = tksvg.SvgImage(
            file=f"{APP_PATH}/rsc/arrow-left.svg"
            )
        self.remove_btn = ttk.Button(self, bootstyle="info",
                                     image=self.__remove_btn_img,
                                     text="Remove", compound="left",
                                     command=self._remove)
        self.remove_btn.grid(row=3, column=1, sticky="w", pady=10, padx=25)

    def clear_list(self):
        """Clear both listbox"""
        self._listbox.listbox.delete(0, tk.END)
        self._slct_lstbx.listbox.delete(0, tk.END)

    def handle_keyrelease(self, event):
        """Handle entry filter release key"""
        value = self.search_ent.get()
        if value == '':
            data = self.values
        else:
            data = []
            for item in self.values:
                if value.lower() in item.lower():
                    data.append(item)

        original_data = self.values
        actual_selection = self.get()
        new_selection = [i for i in actual_selection if i in data]

        self.clear_list()

        self.insert(data, new_selection)
        self.values = original_data
        self.selected.set(actual_selection)
        self.search_ent.focus_set()

    def _on_select(self, event):
        """Available Listbox selection event"""
        sel_items = []
        for i in event.widget.curselection():
            sel_items.append(event.widget.get(i))
            self.all_btn.config(text="Remove All")
        self.selected.set(sel_items)

    def _all_none(self):
        """Select or Remove All"""
        if (self._listbox.listbox.curselection() != () or
                self.available_items.get() == ""):
            self._listbox.listbox.selection_clear(0, tk.END)
            self.all_btn.config(text="Select All")
        else:
            self._listbox.listbox.selection_set(0, tk.END)
            self.all_btn.config(text="Remove All")
        self._listbox.listbox.event_generate("<<ListboxSelect>>")

    def _remove(self):
        """Remove Selected Listbox selection"""
        idx = self._slct_lstbx.listbox.curselection()
        if idx == ():
            return
        val = self._slct_lstbx.listbox.get(*idx)
        self._slct_lstbx.listbox.delete(*idx)
        self._listbox.listbox.selection_clear(
            self._listbox.listbox.get(0, tk.END).index(val)
            )
        if self.get() == ():
            self.all_btn.config(text="Select All")    

    def insert(self, available: list = [], selected: list = []):
        """Insert available items in the first Listbox and automatically
        selected the item in selected list if present\n
        Args:
            available (list, optional): lista opzioni. Defaults to [].
            selected (list, optional): opzioni selezionate. Defaults to [].
        """
        self.values = available
        self.available_items.set(available)
        # starting selection
        self._listbox.listbox.focus_set()
        for i in selected:
            try:
                idx = available.index(i)
                self._listbox.listbox.selection_set(idx)
                self._listbox.listbox.activate(idx)
                self._listbox.listbox.event_generate("<<ListboxSelect>>")
            except ValueError:
                continue
        # update button
        if self._listbox.listbox.curselection() != ():
            self.all_btn.config(text="Remove All")

    def get(self):
        """Get all selected value"""
        val = self._slct_lstbx.listbox.get(0, tk.END)
        return val


class MyTree(ttk.Frame):
    """Tree for result"""
    tv = None

    def __init__(self, master: tk.Misc | None = ..., **kwargs):
        super().__init__(master, **kwargs)
        self.tv = ttk.Treeview(self,
                               show="headings",
                               height=5,
                               padding=2,
                               selectmode="browse",
                               columns=("Data", "Cycle", "Time ON"))
        self.tv.pack(fill=tk.X, side="left", pady=1)

        self.tv.configure(style='My.success.Treeview')
        self.tv.heading(0, text='Column Data', anchor=tk.W)  # image, command
        self.tv.heading(1, text='Cycle', anchor=tk.CENTER)
        self.tv.heading(2, text='Time ON', anchor=tk.CENTER)

        self.tv.column(
            'Data', width=250, stretch=True, anchor=tk.W, minwidth=100
            )
        for col in ["Cycle", "Time ON"]:
            self.tv.column(col,
                           anchor=tk.CENTER,
                           width=ttkutility.scale_size(self, 125),
                           stretch=False,
                           minwidth=50)
        self.scrollbar = AutoHideScrollbar(self, orient="vertical",
                                           command=self.tv.yview)
        self.scrollbar.pack(fill=tk.Y, side="left", pady=1)
        self.tv.configure(yscrollcommand=self.scrollbar.set)

    def __getattr__(self, item):
        try:
            return super().__getattribute__(item)
        except Exception:
            if self.tv:
                return self.tv.__getattribute__(item)

    def bind(self, *args, **kwargs):
        self.tv.bind(*args, **kwargs)

    def clear(self):
        """Delete all TreeView children"""
        for i in self.tv.get_children():
            self.tv.delete(i)


class Slider(ttk.Frame):
    """Modified Slider class with indicator label"""
    scale = None

    def __init__(self,
                 master: tk.Misc = ...,
                 resolution: float = 1,
                 command: Callable[[ttk.Scale], Any] = lambda *args: None,
                 frame_kwargs: dict[str, Any] = {},
                 scale_kwargs: dict[str, Any] = {}) -> None:
        """Construct a Ttk Scale with indicator Label with parent master.

        STANDARD OPTIONS

            master, resolution, command, frame_kwargs, scale_kwargs

        FRAME-OPTIONS
            - border: _ScreenUnits = ...,
            - borderwidth: _ScreenUnits = ...,
            - class_: str = ...,
            - cursor: _Cursor = ...,
            - height: _ScreenUnits = ...,
            - name: str = ...,
            - padding: _Padding = ...,
            - relief: _Relief = ...,
            - style: str = ...,
            - takefocus: _TakeFocusValue = ...,
            - width: _ScreenUnits = ...

        SCALE-OPTIONS
            - class_: str = ...,
            - cursor: _Cursor = ...,
            - from_: float = ...,
            - length: _ScreenUnits = ...,
            - name: str = ...,
            - orient: Literal['horizontal', 'vertical'] = ...,
            - state: str = ...,
            - style: str = ...,
            - takefocus: _TakeFocusValue = ...,
            - to: float = ...,
            - value: float = ... (default_value),
            - variable: IntVar | DoubleVar = ...
            """
        super().__init__(master, **frame_kwargs)
        self._res = resolution
        self._callback = command

        self.var: tk.IntVar | tk.DoubleVar = scale_kwargs.get("variable",
                                                              tk.DoubleVar())
        from_ = scale_kwargs.pop("from_", 0)
        self.default_val = scale_kwargs.pop("value", from_)
        self.var.set(self.default_val)
        # self.var.trace_add("write",  # update label every time variable change
                        #    lambda *_: self.lbl.configure(text=self.var.get()))

        self.scale = ttk.Scale(
            self,
            orient=scale_kwargs.pop("orient", "horizontal"),
            from_=from_,
            to=scale_kwargs.pop("to", 100),
            value=self.default_val,
            variable=self.var,
            length=100,
            bootstyle=scale_kwargs.pop("bootstyle", "info"),
            )
        self.scale.pack(side=tk.LEFT, expand=1, fill="x", padx=5)

        self.entry = ttk.Entry(self, textvariable=self.var, width=8,
                               validate="key",
                               validatecommand=(
                                   self.register(self.__validate_entry), "%P"
                                   ))
        self.entry.pack(side=tk.LEFT, pady=5)
        self.entry.bind("<FocusOut>",
                        lambda e: self._callback(self.scale), add="+")

        self.scale.bind("<ButtonRelease-1>",
                        lambda e: self.scale.event_generate(
                            '<Button-3>', x=e.x, y=e.y
                            )
                        )
        self.scale.bind('<Button-3>',
                        lambda e: self.after(1, self.event_mouse, e), add="+")
        self.scale.bind('<Left>',
                        lambda e: self._callback(self.scale), add="+")
        self.scale.bind('<Right>',
                        lambda e: self._callback(self.scale), add="+")

    def __validate_entry(self, inp:str):
        """Validate Value insert in indicator entry\n
        Args:
            inp (str): all typed key"""
        try:
            if inp == "":
                return True
            int(inp)
        except Exception:
            return False
        return True

    def event_mouse(self, e):
        """Handling Button-3 event\n
        Args:
            e (tk.Event): tkinter event
        """
        value = round(self.var.get(), 10)
        res_val = round(value - math.remainder(value, self._res), 10)
        if res_val.is_integer():
            res_val = int(res_val)
        self.scale.set(res_val)
        self.update()
        self._callback(self.scale)

    def bind(self, *args, **kwargs):
        self.scale.bind(*args, **kwargs)

    def reset(self):
        """Rest scale to default value and call callback"""
        self.scale.set(self.default_val)
        self.update()
        self._callback(self.scale)

    def __getattr__(self, item):
        try:
            return self.__getattribute__(item)
        except Exception:
            if self.scale:
                return self.scale.__getattribute__(item)


class CollapsingFrame(ttk.Frame):
    """A collapsible frame widget that opens and closes with a click."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.columnconfigure(0, weight=1)
        self.cumulative_rows = 0

        # widget images
        self.images = [
            tksvg.SvgImage(
                file=f"{APP_PATH}/rsc/chevrons-right.svg",
                name='close'),
            tksvg.SvgImage(
                file=f"{APP_PATH}/rsc/chevrons-down.svg",
                name='open'),
        ]

    def add(self, child, title="", bootstyle="primary", **kwargs):
        """Add a child to the collapsible frame

        Parameters:

            child (Frame):
                The child frame to add to the widget.

            title (str):
                The title appearing on the collapsible section header.

            bootstyle (str):
                The style to apply to the collapsible section header.

            **kwargs (Dict):
                Other optional keyword arguments.
        """
        if child.winfo_class() != 'TFrame':
            return

        style_color = Bootstyle.ttkstyle_widget_color(bootstyle)
        frm = ttk.Frame(self, bootstyle=style_color)
        frm.grid(row=self.cumulative_rows, column=0, sticky="ew")

        # header title
        header = ttk.Label(
            master=frm,
            text=title,
            bootstyle=(style_color, 'inverse')
        )
        if kwargs.get('textvariable'):
            header.configure(textvariable=kwargs.get('textvariable'))
        header.pack(side=tk.LEFT, fill=tk.BOTH, padx=10)

        # header toggle button
        def _func(c=child): return self._toggle_open_close(c)
        btn = ttk.Button(
            master=frm,
            image=self.images[0],
            bootstyle=style_color,
            command=_func
        )
        btn.pack(side=tk.RIGHT)

        # assign toggle button to child so that it can be toggled
        child.btn = btn
        child.grid(row=self.cumulative_rows + 1, column=0, sticky="nsew")

        # increment the row assignment
        self.cumulative_rows += 2

    def _toggle_open_close(self, child):
        """Open or close the section and change the toggle button
        image accordingly.

        Parameters:

            child (Frame):
                The child element to add or remove from grid manager.
        """
        if child.winfo_viewable():
            child.grid_remove()
            child.btn.configure(image=self.images[1])
        else:
            child.grid()
            child.btn.configure(image=self.images[0])


# class Result(tk.Frame):
#     def __init__(self, parent):
#         super().__init__(parent)
#         self.grid_columnconfigure(0, weight=1)
#         self.grid_rowconfigure(0, weight=1)

#         header = [
#             "Mean (all)",
#             "Max (all)",
#             "Min (all)",
#             "Mean (detail)",
#             "Max (detail)",
#             "Min (detail)",
#         ]
#         self.sheet = Sheet(
#             self,
#             width=620,
#             height=180,
#             data=[],
#             total_columns=6,
#             total_rows=6,
#             # headers=header,
#         )
#         self.sheet.enable_bindings()
#         self.sheet.grid(row=0, column=0, sticky="nswe")

#     def add_data(self, data: list[list], row_index: list):
#         self.sheet.set_sheet_data(
#             data=data,
#             reset_col_positions=True,
#             reset_row_positions=True,
#             redraw=True,
#             verify=False,
#             reset_highlights=False,
#         )
#         self.sheet.row_index(
#             newindex=row_index,
#             index=None,
#             reset_row_positions=False,
#             show_index_if_not_sheet=True,
#         )
#         self.sheet.readonly_rows(
#             rows=[0, 1, 2, 3, 4, 5], readonly=True, redraw=True
#         )
#         self.sheet.refresh(redraw_header=True, redraw_row_index=True)

#     def reset_data(self):
#         self.sheet.set_sheet_data(
#             data=[],
#             reset_col_positions=True,
#             reset_row_positions=True,
#             redraw=True,
#             verify=False,
#             reset_highlights=False,
#         )
#         self.sheet.row_index(
#             newindex=[],
#             index=None,
#             reset_row_positions=False,
#             show_index_if_not_sheet=True,
#         )
#         self.sheet.refresh(redraw_header=True, redraw_row_index=True)


class ScrollFrame(ttk.Frame):
    """Class for a vertical Scrollable Frame. The frame is accessible at
    'viewPort' attribute"""

    def __init__(self, parent: tk.Misc = ..., mousebind: bool = True, **kwargs):
        """Create a Scrollable Frame\n
        Args:
            parent (tk.Misc, optional): Parent. Defaults to ....
            mousebind (bool, optional): add bind of mousewheel to scrollbar of
            frame. Defaults to True.
            **kwargs: options to be passed on to the :class:`ttk.Frame`
        """
        pad = kwargs.pop("padding", 2)
        super().__init__(parent, padding=pad, **kwargs)  # create a frame (self)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        # place canvas on self
        self._canvas = ttk.Canvas(self, borderwidth=0)
        # place a scrollbar on self
        self._vsb = AutoHideScrollbar(self, orient="vertical",
                                      command=self._canvas.yview)
        # attach scrollbar action to scroll of canvas
        self._canvas.configure(yscrollcommand=self._vsb.set)
        self._canvas.yview_moveto(0)

        # place a frame on the canvas, this frame will hold the child widgets
        self.viewPort = ttk.Frame(self._canvas)
        self.canvas_window = self._canvas.create_window(
            (4, 4),
            window=self.viewPort,
            anchor="nw",  # add view port frame to canvas
            tags="self.viewPort",
        )

        # bind an event whenever the size of the viewPort frame changes.
        self.viewPort.bind("<Configure>", self.onFrameConfigure)
        # bind an event whenever the size of the canvas frame changes.
        self._canvas.bind("<Configure>", self.onCanvasConfigure)
        self.__grid_widgets()
        # # bind wheel events when the cursor enters the control
        # self.viewPort.bind("<Enter>", self.onEnter)
        # # # unbind wheel events when the cursorl leaves the control
        # self.viewPort.bind("<Leave>", self.onLeave)

        # perform an initial stretch on render, otherwise the scroll region has a tiny border until the first resize # noqa: E501
        self.onFrameConfigure(None)

    def __grid_widgets(self):
        """Places all the child widgets in the appropriate positions."""
        scrollbar_column = 2
        self._canvas.grid(row=0, column=1, sticky="nswe")
        self._vsb.grid(row=0, column=scrollbar_column, sticky="ns")

    def onFrameConfigure(self, event):
        """Reset the scroll region to encompass the inner frame"""
        # whenever the size of the frame changes, alter the scroll region respectively. # noqa: E501
        # self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        (size_x, size_y) = (self.viewPort.winfo_reqwidth(), self.viewPort.winfo_reqheight())
        self._canvas.config(scrollregion="0 0 {0} {1}".format(size_x, size_y))
        if self.viewPort.winfo_reqwidth() is not self._canvas.winfo_width():
            # If the interior Frame is wider than the canvas, automatically resize the canvas to fit the frame
            self._canvas.config(width=self.viewPort.winfo_reqwidth())

    def onCanvasConfigure(self, event):
        """Reset the canvas window to encompass inner frame when required"""
        canvas_width = event.width
        # whenever the size of the canvas changes alter the window region respectively # noqa: E501
        self._canvas.itemconfig(self.canvas_window, width=canvas_width)

    def onMouseWheel(self, event):  # cross platform scroll wheel event
        if platform.system() == "Windows":
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif platform.system() == "Darwin":
            self._canvas.yview_scroll(int(-1 * event.delta), "units")
        else:
            if event.num == 4:
                self._canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self._canvas.yview_scroll(1, "units")

    # bind wheel events when the cursor enters the control
    def onEnter(self, event):
        if platform.system() == "Linux":
            self._canvas.bind_all("<Button-4>", self.onMouseWheel)
            self._canvas.bind_all("<Button-5>", self.onMouseWheel)
        else:
            self._canvas.bind_all("<MouseWheel>", self.onMouseWheel)

    # unbind wheel events when the cursorl leaves the control
    def onLeave(self, event):
        if platform.system() == "Linux":
            self._canvas.unbind_all("<Button-4>")
            self._canvas.unbind_all("<Button-5>")
        else:
            self._canvas.unbind_all("<MouseWheel>")


# ----- Monkey Patch MessageDialog with flashing ----- #
class FLASHWINFO(Structure):
    """FlashWindowsInfo"""
    FLASHW_STOP = 0
    FLASHW_CAPTION = 0x00000001
    FLASHW_TRAY = 0x00000002
    FLASHW_ALL = 0x00000003
    FLASHW_TIMER = 0x00000004
    FLASHW_TIMERNOFG = 0x0000000C
    _fields_ = (('cbSize', wintypes.UINT),
                ('hwnd', wintypes.HWND),
                ('dwFlags', wintypes.DWORD),
                ('uCount', wintypes.UINT),
                ('dwTimeout', wintypes.DWORD))

    def __init__(self, cbSize, hwnd, flags=FLASHW_ALL, count=5, timeout_ms=0):
        # self.cbSize = sizeof(self)
        self.cbSize = cbSize
        self.hwnd = hwnd
        self.dwFlags = flags
        self.uCount = count
        self.dwTimeout = timeout_ms


class MessageDialog(ttk_dial.Dialog):
    """Class for flashing custome message Dialog"""

    def __init__(
        self,
        message,
        title=" ",
        buttons=None,
        command=None,
        width=50,
        parent=None,
        alert=False,
        default=None,
        padding=(20, 20),
        icon=None,
        **kwargs,
    ):
        """
        Parameters:

            message (str):
                A message to display in the message box.

            title (str):
                The string displayed as the title of the message box.
                This option is ignored on Mac OS X, where platform
                guidelines forbid the use of a title on this kind of
                dialog.

            buttons (List[str]):
                A list of buttons to appear at the bottom of the popup
                messagebox. The buttons can be a list of strings which
                will define the symbolic name and the button text.
                `['OK', 'Cancel']`. Alternatively, you can assign a
                bootstyle to each button by using the colon to separate the
                button text and the bootstyle. If no colon is found, then
                the style is set to 'primary' by default.
                `['OK:success','Cancel:danger']`.

            command (Tuple[Callable, str]):
                The function to invoke when the user closes the dialog.
                The actual command is a tuple that consists of the
                function to call and the symbolic name of the button that
                closes the dialog.

            width (int):
                The maximum number of characters per line in the message.
                If the text stretches beyond the limit, the line will break
                at the word.

            parent (Widget):
                Makes the window the logical parent of the message box.
                The messagebox is displayed on top of its parent window.

            alert (bool):
                Ring the display's bell when the dialog is shown.

            default (str):
                The symbolic name of the default button. The default
                button is invoked when the the <Return> key is pressed.
                If no default is provided, the right-most button in the
                button list will be set as the default.,

            padding  (Union[int, Tuple[int]]):
                The amount of space between the border and the widget
                contents.

            icon (str):
                An image path, path-like object or image data to be
                displayed to the left of the text.

            **kwargs (Dict):
                Other optional keyword arguments.

        Example:

            ```python
            root = tk.Tk()

            md = MessageDialog("Displays a message with buttons.")
            md.show()
            ```
        """
        super().__init__(parent, title, alert)
        self._message = str(message)
        self._command = command
        self._width = width
        self._alert = alert
        self._default = (default,)
        self._padding = padding
        self._icon = icon
        self._localize = kwargs.get("localize")

        if buttons is None:
            self._buttons = [
                f"{MessageCatalog.translate('Cancel')}:secondary",
                f"{MessageCatalog.translate('OK')}:primary",
            ]
        else:
            self._buttons = buttons

    def create_body(self, master):
        """Overrides the parent method; adds the message section."""
        container = ttk.Frame(master, padding=self._padding)
        if self._icon:
            try:
                # assume this is image data
                self._img = ttk.PhotoImage(data=self._icon)
                icon_lbl = ttk.Label(container, image=self._img)
                icon_lbl.pack(side=tk.LEFT, padx=5)
            except Exception:
                try:
                    # assume this is a file path
                    self._img = ttk.PhotoImage(file=self._icon)
                    icon_lbl = ttk.Label(container, image=self._img)
                    icon_lbl.pack(side=tk.LEFT, padx=5)
                except Exception:
                    # icon is neither data nor a valid file path
                    print("MessageDialog icon is invalid")

        if self._message:
            for msg in self._message.split("\n"):
                message = "\n".join(textwrap.wrap(msg, width=self._width))
                message_label = ttk.Label(container, text=message)
                message_label.pack(pady=(0, 3), fill=tk.X, anchor=tk.N)
        container.pack(fill=tk.X, expand=True)

    def create_buttonbox(self, master):
        """Overrides the parent method; adds the message buttonbox"""
        frame = ttk.Frame(master, padding=(5, 5))

        button_list = []

        for i, button in enumerate(self._buttons[::-1]):
            cnf = button.split(":")
            if len(cnf) == 2:
                text, bootstyle = cnf
            else:
                text = cnf[0]
                bootstyle = "secondary"

            if self._localize is True:
                text = MessageCatalog.translate(text)

            btn = ttk.Button(frame, bootstyle=bootstyle, text=text)
            btn.configure(command=lambda b=btn: self.on_button_press(b))
            btn.pack(padx=2, side=tk.RIGHT)
            btn.lower()  # set focus traversal left-to-right
            button_list.append(btn)

            if self._default is not None and text == self._default:
                self._initial_focus = btn
            elif self._default is None and i == 0:
                self._initial_focus = btn

        # bind default button to return key press and set focus
        self._toplevel.bind("<Return>", lambda _, b=btn: b.invoke())
        self._toplevel.bind("<KP_Enter>", lambda _, b=btn: b.invoke())

        ttk.Separator(self._toplevel).pack(fill=tk.X)
        frame.pack(side=tk.BOTTOM, fill=tk.X, anchor=tk.S)

        if not self._initial_focus:
            self._initial_focus = button_list[0]

    def on_button_press(self, button):
        """Save result, destroy the toplevel, and execute command."""
        self._result = button["text"]
        command = self._command
        if command is not None:
            command()
        self._toplevel.destroy()

    def show(self, position=None):
        """Create and display the popup messagebox."""
        super().show(position)

    def build(self):
        super().build()
        self._toplevel.bind("<Button-1>", self.flash)

    def flash(self, event):
        """Flash if User not click in Message dialog topwindow"""
        if self.winfo_containing(event.x_root, event.y_root) != self:
            self._toplevel.focus_set()
            ntymes = 3
            flash_time = 50
            info = FLASHWINFO(0, hwnd=win32gui.GetForegroundWindow(),
                              count=ntymes, timeout_ms=flash_time)
            info.cbSize = sizeof(info)
            windll.user32.FlashWindowEx(byref(info))


ttk_dial.dialogs.MessageDialog = MessageDialog
