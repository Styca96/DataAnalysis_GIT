#!/usr/bin/env python
"""Data Analysis"""
import datetime as dt
import tkinter as tk
from functools import singledispatchmethod
from os import path
from tkinter import filedialog
from typing import Iterator, Literal, Union

import matplotlib.backends.backend_tkagg as tkagg
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import mplcursors
import numpy as np
import pandas as pd
import tksvg
import ttkbootstrap as ttk
import yaml
from matplotlib import rcParams
from matplotlib.widgets import SpanSelector
from scipy.signal import savgol_filter
from tksheet import Sheet
from ttkbootstrap import font
# from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

import func_numba as fnb
from utils import (APP_PATH, Checklist, CollapsingFrame, Menubar, MyTree,
                   PlaceholderEntry, ScrollFrame, Slider, Statusbar,
                   all_children, read_functions, retag)

# plt.style.use('seaborn')
rcParams["date.epoch"] = "2022-01-01T00:00:00"
rcParams["date.autoformatter.hour"] = "%d %H:%M:%S"
rcParams["date.autoformatter.minute"] = "%H:%M:%S"
rcParams["axes.autolimit_mode"] = "round_numbers"


class DataAnalysis(ttk.Window):
    """# GUI generale dell'applicazione"""

    def __init__(self):
        super().__init__(
            title="DataAnalysis",
            iconphoto=None,
            themename='abbtheme',
            size=(1250, 855),
            minsize=(1250, 855),
        )
        self.iconphoto(True, tksvg.SvgImage(file=f"{APP_PATH}/rsc/trello.svg",
                                            height=24, width=24))
        self.state("zoomed")
        self.bind_all("<Button-1>", lambda event: event.widget.focus_set())
        self._style_mod()

        # create a model
        model = Model(None)

        # Create a principal view
        self.menubar = Menubar(self)
        view = View(self)
        view.pack(side=tk.TOP)
        statusbar = Statusbar(self)
        statusbar.pack(fill="x", side=tk.BOTTOM, anchor="sw")
        self.bind("<Key>", statusbar.update_status)
        self.bind("<Button>", statusbar.update_status, add="+")

        # create controller
        controller = Controller(model, view, statusbar)

        # set the controller for the view
        self.menubar.set_controller(controller)
        view.set_controller(controller)

    def _style_mod(self):
        """Create custom Style"""

        f = font.nametofont("TkDefaultFont")
        f.configure(family="ABBvoice", size=10)

        # self.tk.call('tk', 'scaling', 2.0)
        # checkbutton style
        # self.parent.style.configure('my.Round.Toggle',
        #                             font=50)
        # notebook style
        self.style.configure('v.TNotebook',
                             tabposition='wn',
                             padding=2,
                             tabmargins=[2, 5, 2, 0])
        self.style.map("v.TNotebook.Tab",
                       background=[("selected", "#f2f2f2"),
                                   ("!selected", "#a9afb6")
                                   ],
                       padding=[("selected",
                                 (10,  self.winfo_screenmmheight())),
                                ("!selected",
                                (10,  self.winfo_screenmmheight()//2))],
                       compound=[(None, tk.TOP)]
                       )

        self.style.configure('My.success.Treeview', rowheight=35)
        self.style.configure('My.success.Treeview.Heading',
                             font=font.Font(font=("ABBvoice", 12, "bold")),
                             anchor=tk.NW,
                             borderwidth=2,
                             relief='raised',
                             lightcolor=self.style.colors.success,
                             darkcolor=self.style.colors.success,
                             bordercolor=self.style.colors.bg,
                             padding=(5, 10, 5, 10)
                             )


class View(ttk.Frame):
    """## VIEW"""

    def __init__(self, parent: DataAnalysis):
        super().__init__(parent)

        self.images = [ # all used image in this file
            tksvg.SvgImage(
                file=f"{APP_PATH}/rsc/reset.svg",
                name='reset'),
            tksvg.SvgImage(
                file=f"{APP_PATH}/rsc/eye.svg",
                name='show_graph'),
            tksvg.SvgImage(
                file=f"{APP_PATH}/rsc/activity.svg",
                name='show_smooth'),
            tksvg.SvgImage(
                file=f"{APP_PATH}/rsc/cpu.svg",
                name='analysis'),
            tksvg.SvgImage(
                file=f"{APP_PATH}/rsc/trending-up.svg",
                name="thermal_tab"),
            tksvg.SvgImage(
                file=f"{APP_PATH}/rsc/bar-chart-2.svg",
                name="lifetest_tab"),
            tksvg.SvgImage(
                file=f"{APP_PATH}/rsc/search.svg",
                name="search"),
            tksvg.SvgImage(
                file=f"{APP_PATH}/rsc/cpu.svg",
                name="cpu")
            ]

        self.option_wd: LT_ExportOpt | None = None
        self.parent = parent
        self.controller: Controller | None = None
        self.__main_widget()
        self.__createthermal(self.thermal)      # create thermal tab
        self.__createlifetest(self.lifetest)    # create lifetest tab

    def __main_widget(self):
        self.nb = ttk.Notebook(style="v.TNotebook", bootstyle="success")
        self.nb.pack(fill="both", expand=1, side="top")
        # self.nb.bind("<<NotebookTabChanged",
        #   menubar = frame.menubar(self)
        #   self.parent.configure(menu=menubar))

        # self.parent.bind("<Configure>", self.conf)

        self.thermal = ttk.Notebook(self.nb, bootstyle="success")
        self.nb.add(self.thermal, text="Thermal", sticky="nsew",
                    image="thermal_tab")

        self.lifetest = ttk.Notebook(self.nb, bootstyle="success")
        self.nb.add(self.lifetest, text="LifeTest", sticky="nsew",
                    image="lifetest_tab")

    def __createthermal(self, thermal: ttk.Notebook):
        # ################################## #
        # ## ----- VISUAL TAB FRAME ----- ## #
        # ################################## #
        visual_tab = ttk.Frame(thermal)
        thermal.add(visual_tab, text="Thermal DataView", sticky="nsew")

        # ----- VISUAL OPT FRM FRAME ----- #
        visual_opt_frm_scroll = ScrollFrame(visual_tab, mousebind=False)
        visual_opt_frm = visual_opt_frm_scroll.viewPort
        visual_opt_frm_scroll.pack(side=tk.LEFT, fill="y")

        # ----- CHECKLIST FRAME ----- #
        self.frm_option = Checklist(visual_opt_frm, filter=True)
        self.frm_option.grid(row=0, column=0, rowspan=2)

        # ----- BUTTON FRAME ----- #
        button_frm = ttk.Frame(visual_opt_frm, borderwidth=2, relief="raised")
        button_frm.grid(row=2, column=0, sticky="ew",
                        padx=10, pady=(20, 10))

        show_btn = ttk.Button(button_frm, text="SHOW",
                              bootstyle="success-bold",
                              image="show_graph", compound="right",
                              width=18, command=self._show_btn_click)
        show_btn.grid(row=0, column=0, padx=8, pady=20, ipady=5, sticky="w")

        showsmooth_btn = ttk.Button(button_frm, text="SHOW SMOOTH",
                                    bootstyle="success-bold",
                                    image="show_smooth", compound="right",
                                    width=18, command=self._smooth_btn_click)
        showsmooth_btn.grid(row=0, column=1,
                            padx=8, pady=20, ipady=5, sticky="e")

        self.th_analysis_btn = ttk.Button(button_frm, text="ANALYSIS",
                                          bootstyle="success-bold",
                                          image="analysis", compound="right",
                                          command=self._analisi_th_click,
                                          state="disabled", width=20)
        self.th_analysis_btn.grid(row=1, column=0, columnspan=2,
                                  pady=(0, 20), ipady=5)
        self.th_export_btn = ttk.Button(button_frm, text="EXPORT MERGE",
                                          bootstyle="success-bold",
                                        #   image="analysis", compound="right",
                                          command=self._export_th_click,
                                          state="disabled", width=20)
        self.th_export_btn.grid(row=2, column=0, columnspan=2,
                                pady=(0, 20), ipady=5)

        # ----- OPTION FRAME ----- #
        option_frm = CollapsingFrame(visual_opt_frm)
        option_frm.grid(row=3, rowspan=2, column=0, sticky="nswe", padx=10)
        visual_tab.rowconfigure(3, weight=1)

        opt1 = ttk.Frame(option_frm, padding=5)
        self.twin_y = Checklist(opt1)
        self.twin_y.pack(fill="both")

        def update_twin_y():
            options = self.frm_option.get()
            twin_y_sel = self.twin_y.get()
            self.twin_y.selected.set("")
            valid_selection = [i for i in twin_y_sel if i in options]
            self.twin_y.clear_list()
            self.twin_y.insert(options, valid_selection)
        self.frm_option._listbox.listbox.bind("<<ListboxSelect>>",
                                              lambda *_: update_twin_y(),
                                              add="+")
        option_frm.add(child=opt1, title='Twin Y axes')
        opt1.grid_remove()
        opt1.btn.configure(image=option_frm.images[1])

        opt2 = ttk.Frame(option_frm, padding=5)
        self.legend_th = tk.IntVar(value=0)
        self.fixed_span_th = tk.IntVar(value=0)
        self.show_mean_th = tk.IntVar(value=0)
        ttk.Checkbutton(
            opt2,
            text="Legend",
            variable=self.legend_th,
            onvalue=1,
            offvalue=0,
            bootstyle="round-toggle",
            command=lambda: self.th_plot_frm.show_legend(self.legend_th.get())
        ).pack(side=tk.TOP, anchor="w", pady=5)
        ttk.Checkbutton(
            opt2,
            text="Fixed Span",
            variable=self.fixed_span_th,
            onvalue=1,
            offvalue=0,
            bootstyle="round-toggle",
            command=lambda: self.th_plot_frm.change_fixed_span(
                self.fixed_span_th.get()
                )
        ).pack(side=tk.TOP, anchor="w", pady=5)
        ttk.Checkbutton(
            opt2,
            text="Show Mean",
            variable=self.show_mean_th,
            onvalue=1,
            offvalue=0,
            bootstyle="round-toggle"
        ).pack(side=tk.TOP, anchor="w", pady=5)
        option_frm.add(child=opt2, title='Graph Option', bootstyle="info")
        opt2.grid_remove()
        opt2.btn.configure(image=option_frm.images[1])

        opt3 = ttk.Frame(option_frm, padding=5)
        ttk.Label(opt3, text="Title: ", anchor="w"
                  ).grid(row=0, column=0, padx=5, pady=(5, 0))
        ttk.Label(opt3, text="X-axis Label: ", anchor="w"
                  ).grid(row=1, column=0, padx=5, pady=(5, 0))
        ttk.Label(opt3, text="Y1-axis Label: ", anchor="w"
                  ).grid(row=2, column=0, padx=5, pady=(5, 0))
        ttk.Label(opt3, text="Y2-axis Label: ", anchor="w"
                  ).grid(row=3, column=0, padx=5, pady=(5, 0))
        self.th_title_ent = ttk.Entry(opt3)  # PlaceholderEntry(opt3, )
        self.th_title_ent.grid(row=0, column=1)
        self.th_x_ent = ttk.Entry(opt3)  # PlaceholderEntry(opt3, )
        self.th_x_ent.grid(row=1, column=1)
        self.th_y_ent = ttk.Entry(opt3)  # PlaceholderEntry(opt3, )
        self.th_y_ent.grid(row=2, column=1)
        self.th_twiny_ent = ttk.Entry(opt3)  # PlaceholderEntry(opt3, )
        self.th_twiny_ent.grid(row=3, column=1)
        th_update_graph_btn = ttk.Button(opt3, text="Update graph",
                                         bootstyle="outline-info",
                                         command=self._th_graph_update)
        th_update_graph_btn.grid(row=4, column=0, padx=5, pady=(5, 0))
        ttk.Label(opt3, text="Horizontal line: ", anchor="w"
                  ).grid(row=5, column=0, padx=5, pady=(5, 0))
        self.th_x_line = tk.DoubleVar()
        ttk.Entry(opt3, textvariable=self.th_x_line, width=8
                  ).grid(row=5, column=1)
        self.th_n_axis = tk.IntVar(value=1)
        ttk.Radiobutton(opt3, text='Y1', value=1, variable=self.th_n_axis
                        ).grid(row=5, column=2)
        ttk.Radiobutton(opt3, text='Y2', value=2, variable=self.th_n_axis
                        ).grid(row=5, column=3)
        th_add_x_line_btn = ttk.Button(opt3, text="ADD",
                                       bootstyle="outline-info",
                                       command=self._th_graph_xline)
        th_add_x_line_btn.grid(row=5, column=4, padx=5, pady=(5, 0))
        # TODO add_line to graph
        # self.th_y_line = tk.DoubleVar()

        option_frm.add(child=opt3, title='Edit Graph', bootstyle="success")
        opt3.grid_remove()
        opt3.btn.configure(image=option_frm.images[1])
        # ----- SEPARATOR ----- # # TODO change with PanedWindow
        sep = ttk.Separator(visual_tab, orient="vertical")
        sep.pack(side=tk.LEFT, fill="y")

        # ----- GRAPH FRAME ----- #
        graph_frm = ttk.Frame(visual_tab)
        graph_frm.pack(side=tk.LEFT, fill="both", expand=1)

        # ----- IMAGE FRAME ----- #
        self.th_plot_frm = TH_TimeSerie(graph_frm)
        self.th_plot_frm.grid(row=0, column=2, columnspan=4, sticky="nsew")

        # ----- RESULT FRAME ----- #
        self.index_lbl = ttk.Label(graph_frm, text="Samples:")
        self.index_lbl.grid(row=1, column=2, padx=5)
        self.debug_res = Sheet(
            graph_frm,
            width=600,
            height=80,
            data=[["MEAN"]],
            total_rows=1,
            show_x_scrollbar=True,
            show_y_scrollbar=False,
        )
        self.debug_res.row_index(["MEAN"])
        self.debug_res.enable_bindings()
        self.debug_res.grid(row=1, column=3, columnspan=3, sticky="nswe")

        graph_frm.rowconfigure(0, weight=1)
        graph_frm.columnconfigure(5, weight=1)

        # ################################ #
        # ----- ALL RESULT TAB FRAME ----- #
        # ################################ #
        result_tab = ttk.Frame(thermal)
        thermal.add(result_tab, text="Thermal Result", sticky="nsew", state="disabled")
        result_tab.rowconfigure(1, weight=1)

        ttk.Label(result_tab, text="Selected Column Result"
                  ).grid(row=0, column=0)
        self.detail_res = Sheet(
            result_tab,
            width=600,
            headers=["MEAN", "MAX", "MIN"],
            data=[],
            total_columns=3,
            show_x_scrollbar=True,
            show_y_scrollbar=True,
        )
        # self.detail_res.row_index(["MEAN", "MAX", "MIN"])
        self.detail_res.enable_bindings()
        self.detail_res.grid(row=1, column=0, sticky="nswe")

        ttk.Label(result_tab, text="All Column Result"
                  ).grid(row=0, column=1)
        self.all_res = Sheet(
            result_tab,
            width=600,
            headers=["MEAN", "MAX", "MIN"],
            data=[],
            total_columns=3,
            show_x_scrollbar=True,
            show_y_scrollbar=True,
        )
        # self.all_res.row_index(["MEAN", "MAX", "MIN"])
        self.all_res.enable_bindings()
        self.all_res.grid(row=1, column=1, sticky="nswe")

    def __createlifetest(self, lifetest: ttk.Notebook):
        # ## ----- OPTION TAB ----- ## #
        option_tab = ttk.Frame(lifetest)
        lifetest.add(option_tab, text="Cycle Options", sticky="nsew")

        self.col_frm = Checklist(option_tab, filter=True)
        self.col_frm.grid(row=0, column=0, rowspan=2,
                          pady=5, padx=5, sticky="nsew")
        ttk.Label(option_tab, text="Soglie:", anchor="nw"
                  ).grid(row=0, column=1, sticky="new", pady=5, padx=5)
        self.soglie_txt = ttk.Text(option_tab, width=10, height=13)
        self.soglie_txt.grid(row=1, column=1,
                             sticky="nsew", pady=(0, 5), padx=5)

        self.cicli_btn = ttk.Button(
            option_tab, text="CALCOLO CICLI ",
            command=self._cicli_btn_click,
            width=18, bootstyle="success-bold",
            image="search", compound="right"
        )
        self.cicli_btn.grid(row=0, column=2, rowspan=2, ipady=15, padx=60)

        self.cicli_result_tv = MyTree(option_tab)
        self.cicli_result_tv.grid(row=2, column=0, columnspan=2,
                                  pady=20, sticky="w")
        self.analysis_btn = ttk.Button(
            option_tab, text="CYCLE ANALYSIS",
            command=self._analysis_lt_click,
            width=18, bootstyle="success-bold",
            image="cpu", compound="right",
            state="disabled"
        )
        self.analysis_btn.grid(row=2, column=2, rowspan=2, ipady=15, padx=60)

        # ## ----- DISTRIBUTION TAB ----- ## #
        self.distr_tab = DataDistribution(lifetest)
        lifetest.add(self.distr_tab, text="Distribution", sticky="nsew")

        # ## ----- TIMESERIE TAB ----- ## #
        self.timeseries_tab = LT_TimeSerie(lifetest)
        lifetest.add(self.timeseries_tab, text="Timeserie", sticky="nsew")

    # ##----internal function
    def set_controller(self, controller):
        """Set the controller=controller"""
        self.controller: Controller = controller

    def _cicli_btn_click(self):
        if self.controller:
            self.controller.cicli()

    def _analysis_lt_click(self):
        # TODO ttk.Floodgauge()
        if self.controller:
            self.controller.analysis()

    def _show_btn_click(self):
        if self.controller:
            self.controller.plot_th_timeseries()

    def _smooth_btn_click(self):
        if self.controller:
            self.controller.plot_th_timeseries(smooth=True)

    def _analisi_th_click(self):
        if self.controller:
            self.controller.analysis_th()

    def _export_th_click(self):
        if self.controller:
            self.controller.export_thermal_data(True)

    def _th_graph_update(self):
        if self.controller:
            self.controller.update_th_fig(True)

    def _th_graph_xline(self):
        if self.controller:
            self.controller.th_add_line(
                "x", self.th_x_line.get(), self.th_n_axis.get()
                )

    # ##----messagebox function
    def show_error(self, error: str):
        """Mostra box di errore\n
        Args:
            -error (str): stringa di errore da mostrare
        """
        box_title = "Errore"
        box_message = error
        Messagebox.show_error(title=box_title, message=box_message)

    def show_warning(self, warning: str):
        """Mostra box di warning\n
        Args:
            -warning (str): stringa di warning da mostrare
        """
        box_title = "Attenzion"
        box_message = warning
        Messagebox.show_warning(title=box_title, message=box_message)


class Graph_Option:
    _def_x_axis = "Time"
    _def_y_axis = ["y1", "y2"]
    _def_title = ""

    def __init__(self, fig, *axisargs) -> None:
        from matplotlib.axes._axes import Axes
        from matplotlib.figure import Figure
        self._fig: Figure = fig
        self._axis: tuple[Axes] = axisargs

    @property
    def title(self):
        return self._fig._suptitle._text

    @title.setter
    def title(self, new_title: str):
        if isinstance(new_title, str):
            if new_title == "":
                new_title = self._def_title
            self._fig.suptitle(new_title)
        else:
            raise TypeError("title must be a string")

    @property
    def x_axis(self):
        return self._axis[0].get_xlabel()

    @x_axis.setter
    def x_axis(self, new_x_axis: str):

        if isinstance(new_x_axis, str):
            if new_x_axis == "":
                new_x_axis = self._def_x_axis
            self._axis[0].set_xlabel(new_x_axis)
        else:
            raise TypeError("x_axis must be a string")

    @property
    def y_axis(self) -> list[str]:
        ax_y_label = [ax.get_ylabel() for ax in self._axis]
        return ax_y_label

    @y_axis.setter
    def y_axis(self, new_y_axis: str | list[str]):
        if isinstance(new_y_axis, str):
            if new_y_axis == "":
                new_y_axis = self._def_y_axis[0]
            self._axis[0].set_ylabel(new_y_axis)
        elif isinstance(new_y_axis, list):
            if new_y_axis == ["", ""]:
                new_y_axis = self._def_y_axis
            try:
                for ax, new_label in zip(self._axis, new_y_axis):
                    ax.set_ylabel(new_label)
            except IndexError:
                raise IndexError("Axis not in list. Select another index")
        else:
            raise TypeError("y_axis must be a string or list of string")


class DataDistribution(ttk.Frame):
    """### Distribution Frame"""

    def __init__(self,
                 master: tk.Misc = ...,
                 big_fig: bool = False,
                 **frame_kwargs) -> None:
        """Costruisce Frame per la visualizzazione delle sdistribuzioni\n
        Args:
            -parent (tk.Misc): master del Frame
            -big_fig (bool, optional): 'True'=review,tutto schermo;
            'False'=da analizzare.
                Defaults=False.
            -frame_kwargs: kwargs of ttk.Frame
        """
        pad = frame_kwargs.pop("padding", 5)
        super().__init__(master, padding=pad, **frame_kwargs)
        self.parent = master
        self.controller = None
        # self.big_fig = big_fig
        self.__createwidget(big_fig)
        self.graph_option = Graph_Option(self.fig, self.ax)
        self.graph_option._def_x_axis = "Temp [°C]"

    def __createwidget(self, big_fig: bool):
        """Crea i widget\n
        Args:
            -big_fig (bool): 'True' crea grafico tutto schermo, 'False' no
        """
        opt_frm = ttk.Frame(self, padding=5)
        opt_frm.pack(side="left", fill="y", expand=0)
        imag_frm = ttk.Frame(self, padding=5)
        imag_frm.pack(side="left", fill="both", expand=1)

        # ----- OPT FRAME ----- #
        ttk.Label(opt_frm, text="Column Name:", anchor="w"
                  ).pack(side=tk.TOP, fill="x")
        self.col_slc = tk.StringVar()
        self.col_slc_cmb = ttk.Combobox(opt_frm, textvariable=self.col_slc,
                                        width=30)
        self.col_slc_cmb["state"] = "readonly"
        self.col_slc_cmb.pack(side=tk.TOP)
        self.col_slc_cmb.bind("<<ComboboxSelected>>", self.distr_show)
        # self.col_slc_cmb.unbind("<Button-1>")

        scale_frm = ttk.Frame(opt_frm, padding=5)
        scale_frm.pack(side=tk.TOP, fill="x", pady=20)
        self.bins = tk.IntVar()
        self.x_max = tk.IntVar()
        self.x_min = tk.IntVar()
        lbl = ["N. Bins:", "X Max:", "X Min:"]
        var = [self.bins, self.x_max, self.x_min]
        val = [(10, 250, 150), (150, 450000, 150), (0, 400000, 0)]
        self.sli_l: list[Slider] = []
        for i in range(len(lbl)):
            ttk.Label(scale_frm, text=lbl[i], anchor="w"
                      ).pack(side=tk.TOP, fill="x")
            s = Slider(scale_frm, command=self.update_value,
                       scale_kwargs={"from_": val[i][0],
                                     "to": val[i][1],
                                     "value": val[i][2],
                                     "variable": var[i]},)
            s.pack(side=tk.TOP, fill="x", expand=1)
            self.sli_l.append(s)

        self.reset_btn = ttk.Button(
            scale_frm, text="Default Value",
            bootstyle="success",
            image="reset", compound=tk.RIGHT,
            command=lambda var=self.sli_l, val=val: self.reset(var, val)
            )
        self.reset_btn.pack(side=tk.TOP, fill="x", expand=1, padx=5, pady=5)

        # ----- GRAPH FRAME ----- #
        self.fig, self.ax = plt.subplots()

        self.canvas = tkagg.FigureCanvasTkAgg(self.fig, imag_frm)
        tkagg.NavigationToolbar2Tk(self.canvas, imag_frm).update()

        self.canvas.draw_idle()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill="both", expand=1)

        # adjust
        self.fig.subplots_adjust(left=0.125, bottom=0.10, top=0.95, right=0.95)

    def distr_show(self, event):
        if self.controller:
            self.controller.distr_plot(self)  # self.big_fig)

    def update_value(self, scale):
        """Update Graph with new Slider value"""
        x_max = self.x_max.get()
        x_min = self.x_min.get()
        if x_max <= x_min:
            self.sli_l[1].set(x_min + 150)
        if self.controller:
            self.controller.distr_plot(self, adjust=True)
            self.ax.set_xlim(x_min, x_max)

    def reset(self, var, val):
        """Reset scale to default value"""
        # negative index for handling x_max always greater than x_min
        [var[-i].set(val[-i][2]) for i in range(len(var))]
        self.sli_l[0].reset()  # for call callback only one time

    def clear(self):
        """Clear all Frame (Reset to starting state)"""
        self.col_slc_cmb.set("")
        self.reset_btn.invoke()
        self.fig.delaxes(self.ax)
        self.ax = self.fig.add_subplot(111)
        self.canvas.draw_idle()

    def set_controller(self, controller):
        """Set the controller=controller"""
        self.controller: Controller = controller


class LT_TimeSerie(ttk.Frame):
    """### LifeTest TIMESERIES Frame"""

    def __init__(self,
                 master: tk.Misc = ...,
                 big_fig: bool = False,
                 **frame_kwargs) -> None:
        """Costruisce Frame per la visualizzazione delle serie temporali\n
        Args:
            -master (tk.Misc): master del Frame
            -big_fig (bool, optional): 'True'=review,tutto schermo;
            'False'=da analizzare.
                Defaults=False.
            -frame_kwargs: kwargs of ttk.Frame
        """
        pad = frame_kwargs.pop("padding", 5)
        super().__init__(master, padding=pad, **frame_kwargs)
        self.parent = master
        self.controller = None
        # self.big_fig = big_fig
        self.__createwidget(big_fig)
        self.graph_option = Graph_Option(self.fig, self.ax)

    def __createwidget(self, big_fig: bool):
        """Crea i widget\n
        Args:
            -big_fig (bool): 'True' crea grafico tutto schermo, 'False' no
        """
        opt_frm = ttk.Frame(self, padding=5)
        opt_frm.pack(side="left", fill="y", expand=0)
        imag_frm = ttk.Frame(self, padding=5)
        imag_frm.pack(side="left", fill="both", expand=1)

        # ----- OPT FRAME ----- #
        ttk.Label(opt_frm, text="Column Name:", anchor="w"
                  ).pack(side=tk.TOP, fill="x")
        self.col_slc = tk.StringVar()
        self.col_slc_cmb = ttk.Combobox(opt_frm, textvariable=self.col_slc,
                                        width=30)
        self.col_slc_cmb["state"] = "readonly"
        self.col_slc_cmb.pack(side=tk.TOP)
        self.col_slc_cmb.bind("<<ComboboxSelected>>", self.timeseries_show)

        self.smoothing = tk.BooleanVar(value=True)
        self.smooth_btn = ttk.Checkbutton(opt_frm, text="Smoothing",
                                          padding=2, variable=self.smoothing,
                                          # bootstyle="secondary",
                                          command=self.timeseries_show,
                                          style='my.Round.Toggle'
                                          )
        self.smooth_btn.pack(side=tk.TOP, fill="x", pady=(20, 5), padx=5)

        self.all_fig = tk.BooleanVar(value=True)
        self.all_fig_onoff = ttk.Checkbutton(opt_frm, text="All figure",
                                             padding=2, variable=self.all_fig,
                                             bootstyle="round-toggle")
        self.all_fig_onoff.pack(side=tk.TOP, fill="x", padx=5)
        self.slider = ttk.Meter(opt_frm,
                                amounttotal=100,
                                amountused=0,
                                wedgesize=10,
                                metersize=150,
                                bootstyle="info",
                                metertype="semi",
                                meterthickness=20,
                                interactive=True,
                                stripethickness=10,
                                textright="%",
                                subtext="ghaph view",
                                stepsize=5,
                                )
        self.all_fig_onoff.configure(command=self.all_fig_opt)

        retag("special", *all_children(self.slider))
        self.bind_class("special", '<Left>', lambda *_: self.slider.step(-5)
                        if self.slider.amountusedvar.get() not in (0, 100)
                        else None)
        self.bind_class("special", '<Right>', lambda *_: self.slider.step(+5),
                        add="+")
        self.slider.amountusedvar.trace_add("write", self.update_value)

        # ----- GRAPH FRAME ----- #
        self.fig, self.ax = plt.subplots(figsize=(5, 4), dpi=100)
        self.xlim_min = None  # 0
        self.xlim_max = None  # 1

        self.canvas = tkagg.FigureCanvasTkAgg(self.fig, imag_frm)
        tkagg.NavigationToolbar2Tk(self.canvas, imag_frm).update()
        # self.canvas.get_tk_widget().bind("<<Configure>>", self.canvas.resize)
        self.canvas.draw_idle()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill="both", expand=1)
        # adjust
        self.fig.subplots_adjust(left=0.125, bottom=0.10, top=0.95, right=0.95)

    def timeseries_show(self, *args):
        if self.controller:
            self.controller.plot_timeseries(self)

    def all_fig_opt(self):
        """Show or Hide Meter"""
        if self.all_fig.get():
            self.slider.pack_forget()
            self.ax.autoscale(tight=False)
            self.canvas.draw_idle()
        else:
            self.slider.pack(side=tk.TOP, fill="x", anchor="w", padx=5)

    def update_value(self, var, idx, mode):
        """Update value based on Meter var value"""

        if self.xlim_min is None or self.xlim_max is None:
            return

        pos = int(self.getvar(var))
        xmin = self.xlim_min
        xmax = self.xlim_max
        deltax = (xmax-xmin)/100
        self.ax.set(xlim=[xmin+deltax*(pos-5), xmin+deltax*(pos+5)])
        self.fig.canvas.draw_idle()
        self.canvas.draw_idle()

    def clear(self):
        """Clear all Frame (Reset to starting state)"""
        self.col_slc_cmb.set("")
        self.smoothing.set(True)
        self.all_fig.set(True)
        self.fig.delaxes(self.ax)
        self.ax = self.fig.add_subplot(111)
        self.canvas.draw_idle()

    def set_controller(self, controller):
        """Set the controller=controller"""
        self.controller: Controller = controller


class LT_ExportOpt(ttk.Toplevel):
    """### LifeTest EXPORT Frame"""

    def __init__(
        self,
        parent: View,
        all_: bool
    ):
        super().__init__(
            master=parent,
            size=(600, 800),
            # transient=parent,
            topmost=True,
            # toolwindow=True
            )
        # self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.match = {}
        self.parent = parent
        self.all_ = all_
        if all_:
            self.title("Export LifeTest Data Option - ALL")
        else:
            self.title("Export LifeTest Data Option - Distribution")

        self._createwidget()

    def _createwidget(self):
        # ##----------------file option----------------
        ttk.Label(self, text="File Type"
                  ).grid(row=0, column=0, padx=5, pady=5)
        self.file_option = tk.StringVar()
        self.file_cmb = ttk.Combobox(
            self,
            textvariable=self.file_option,
        )
        self.file_cmb.grid(row=0, column=1, columnspan=3, padx=5, pady=5)
        self.file_cmb["state"] = "readonly"
        self.file_cmb["values"] = list(self.match.keys())
        ttk.Button(
            self, text="CONFIRM", width=20, command=self.confirm_btn_click
        ).grid(row=0, column=4, padx=5, pady=5)

        # ##----------------cicli option----------------
        cicli_frm = ttk.Labelframe(self, padding="5", text="Cicli Option")
        cicli_frm.grid(
            row=2, column=0, columnspan=5, pady=(10, 0), padx=5, sticky="ew"
        )

        ttk.Label(cicli_frm, text="Colonna calcolo cicli (str)"
                  ).grid(row=0, column=0)
        ttk.Label(cicli_frm, text="Valore soglia cicli (int)"
                  ).grid(row=1, column=0, sticky="ew", pady=2)
        row_ = self.parent.cicli_result_tv.selection()
        val_ = self.parent.cicli_result_tv.item(row_)["values"]
        selected_col: str = val_[0] if val_ != "" else None
        if selected_col is not None:
            cycle_data = self.parent.controller.model.cycle_data
            selected_soglia = cycle_data[selected_col]["threshold"]
        else:
            selected_soglia = None
        self.col_cicli = tk.StringVar(value=selected_col)
        self.col_text = ttk.Entry(
            cicli_frm, width=30, textvariable=self.col_cicli
        )
        self.col_text.grid(row=0, column=1, columnspan=3)
        self.col_soglia = tk.StringVar(value=selected_soglia)
        self.soglia_text = ttk.Entry(
            cicli_frm, width=30, textvariable=self.col_soglia
        )
        self.soglia_text.grid(row=1, column=1, columnspan=3, pady=2)

        # ##----------------merge option----------------
        merge_frm = ttk.Labelframe(self, padding="5", text="File Option")
        merge_frm.grid(
            row=3, column=0, columnspan=5, pady=(10, 0), padx=5, sticky="ew"
        )

        self.merge_option = tk.BooleanVar(value=None)
        self.merge_rb = ttk.Radiobutton(
            merge_frm,
            text="Merge File",
            variable=self.merge_option,
            value=True,
            command=self.module_on,
        )

        self.merge_rb.grid(row=2, column=0, pady=5)
        self.new_rb = ttk.Radiobutton(
            merge_frm,
            text="New File",
            variable=self.merge_option,
            value=False,
            command=self.module_off,
        )
        self.new_rb.grid(row=2, column=3, pady=5)

        ttk.Label(merge_frm, text="Reset Module"
                  ).grid(row=3, column=0, sticky="ew")
        self.module = tk.StringVar(value="None")
        self.module_cmb = ttk.Combobox(merge_frm, textvariable=self.module)
        self.module_cmb["state"] = "disabled"
        self.module_cmb.grid(row=3, column=1, pady=5)

        # ##----------------Distribution option----------------
        distr_frm = ttk.Labelframe(self, padding="5",
                                   text="Distribution Option")
        distr_frm.grid(
            row=4, column=0, columnspan=5, pady=(10, 0), padx=5, sticky="ew"
        )
        distr_frm.columnconfigure(1, weight=1)
        ttk.Label(distr_frm, text="Range:"
                  ).grid(row=0, column=0, sticky="ew")
        ttk.Label(distr_frm, text="Bar width:"
                  ).grid(row=1, column=0, sticky="ew")
        self.range = tk.IntVar()
        scale_range = Slider(distr_frm,
                             scale_kwargs={
                                 "from_": 150.0,
                                 "to": 450000.0,
                                 "value": 150.0,
                                 "variable": self.range
                                 })
        scale_range.grid(row=0, column=1, sticky="ew", padx=(10, 0))

        self.width_ = tk.IntVar()
        scale_width = Slider(distr_frm,
                             scale_kwargs={
                                 "from_": 1,
                                 "to": 10000,
                                 "value": 1,
                                 "variable": self.width_
                                 })
        scale_width.grid(row=1, column=1, sticky="ew", padx=(10, 0))

        # ##----------------Data option----------------
        self.col_frm = Checklist(self)
        self.col_frm.grid(row=5, column=0, columnspan=5, pady=(10, 0))
        self.file_cmb.bind("<<ComboboxSelected>>", self.default_col)

    def module_on(self):
        """Attiva il Combobox per selezionare il modulo"""
        a = [str(i + 1) for i in range(12)]
        a.append("None")
        self.module_cmb["values"] = a
        self.module_cmb["state"] = "readonly"

    def module_off(self):
        """Disattiva il Combobox per selezionare il modulo"""
        self.module_cmb["state"] = "disabled"

    def confirm_btn_click(self):
        if self.parent.controller:
            if Messagebox.okcancel(
                parent=self,
                title="Confirm",
                message="Are you sure?"
                ) == "OK":
                self.parent.controller.export_all_process(self.all_)
            else:
                self.focus_set()

    def default_col(self, *event):
        self.col_frm.clear_list()
        file_type = self.file_cmb.get()
        self.col_frm.insert(
            available=self.match["ALL"], selected=self.match[file_type]
        )


class TH_TimeSerie(ttk.Frame):
    """### Thermal TIMESERIES Frame"""

    def __init__(self,
                 master: tk.Misc = ...,
                 **frame_kwargs) -> None:
        """Costruisce Frame per la visualizzazione delle serie temporali\n
        Args:
            -master (tk.Misc): master del Frame
            -frame_kwargs: kwargs of ttk.Frame
        """
        pad = frame_kwargs.pop("padding", 5)
        super().__init__(master, padding=pad, **frame_kwargs)
        self.parent = master
        self.__createwidget()
        self.line = []
        self.lined = {}
        self.line_mean = {}
        self.span = None
        self.x_data = None
        self.x_index = None
        self.fixed_span = False
        self.graph_option = Graph_Option(self.fig, self.ax1, self.ax2)

    def __createwidget(self):
        """Crea il Canvas con il plot\n"""
        self.fig, self.ax1 = plt.subplots(dpi=100)

        self.ax2 = self.ax1.twinx()
        self.canvas = tkagg.FigureCanvasTkAgg(self.fig, self)
        tkagg.NavigationToolbar2Tk(self.canvas, self).update()
        self.canvas.get_tk_widget().pack(fill="both", side=tk.TOP, expand=1)
        self.canvas.draw_idle()
        self.canvas.mpl_connect("pick_event", self.__on_pick)
        plt.subplots_adjust(left=0.06, bottom=0.07, top=0.95, right=0.94)

    def __on_pick(self, event: tk.Event):
        """ "Data la linea cliccata se visibile la nasconde e viceversa

        Args:
            event (tk.Event): evento di click"""
        legline = event.artist
        origline = self.lined[legline]
        visible = not origline.get_visible()
        origline.set_visible(visible)
        legline.set_alpha(1.0 if visible else 0.2)
        self.canvas.draw_idle()

    def _legend(self, n_ylines: int):
        """Rende possibile cliccare le linee della leganda per nascondere
        le linee.

        Args:
            n_ylines (int): Numero di linee che il contiene il primo grafico.
                Necessario per l'uso di grafico gemello"""
        legend = self.ax2.get_legend()
        legend.set(draggable=True)
        all_lines = legend.get_lines()
        if self.line_mean == {}:
            lines = all_lines[:]
        else:
            lines = (
                all_lines[:n_ylines]
                + all_lines[2 * n_ylines: len(self.line) + n_ylines]
            )
        [all_lines.remove(i) for i in lines]
        for legline, origline in zip(lines, self.line):
            legline.set_picker(5)
            self.lined[legline] = origline
        for legline, origline in zip(all_lines, self.line_mean.values()):
            legline.set_picker(5)
            self.lined[legline] = origline

    def _createSpan(self):
        """Crea e collega lo SpanSelector al plot"""
        self.span = SpanSelector(
            self.ax2,
            self.__onselect,
            "horizontal",
            useblit=True,
            props=dict(alpha=0.5, facecolor="tab:blue"),
            interactive=True,
            # minspan=0.001,
            # grab_range=30,
            drag_from_anywhere=True,
        )
        self.canvas.mpl_connect("key_press_event", self.span)

    def __onselect(self, xmin, xmax):
        """Funzione dello SpanSelector

        Args:
        xmin (_type_): variabile interna. Valore più basso dello SpanSelector
        xmax (_type_): variabile interna. Valore più alto dello SpanSelector
        """
        xmin_ = mdates.num2date(xmin)
        indmin = self.__find_nearest(self.x_data, xmin_)

        if self.fixed_span:
            indmax = indmin+30
            xmax_ = self.x_data[indmax].to_pydatetime()
            xmax = mdates.date2num(xmax_)
            self.span.artists[0].set_bounds(xmin, 0, xmax-xmin, 1)
            # self.span.rect.set_bounds(xmin, 0, xmax-xmin, 1)
            self.span.artists[2].set_xdata((xmax, xmax))
        else:
            xmax_ = mdates.num2date(xmax)
            indmax = self.__find_nearest(self.x_data, xmax_)

        self.x_index = [indmin, indmax]

    def __find_nearest(self, array: pd.Series, value: np.datetime64) -> int:
        """Trova l'indice a cui corrisponde il valore più prossimo a quello
        passato\n
        Args:
            array (pd.Series[np.datetime64]): serie contenenti le date
            value (np.datetime64): data da confrontare

        Returns:
            [int]: valore dell'indice prossimo"""
        array_np = np.asarray(array)
        value = np.datetime64(value)
        idx = (np.abs(array_np - value)).argmin()
        return array[array_np == array_np[idx]].index[0]

    def change_fixed_span(self, state: bool = True):
        self.fixed_span = state

    def show_legend(self, state: bool = False):
        legend = self.ax2.get_legend()
        if state:
            legend.set_visible(True)
        else:
            legend.set_visible(False)
        self.canvas.draw_idle()

    def clear(self):
        """Clear all Frame (Reset to starting state)"""
        self.fig.clf()
        # self.fig.delaxes(self.ax1)
        # self.fig.delaxes(self.ax2)
        self.ax1 = self.fig.add_subplot(111)
        self.ax2 = self.ax1.twinx()
        plt.subplots_adjust(left=0.06, bottom=0.07, top=0.95, right=0.94)
        self.canvas.draw_idle()

        self.line = []
        self.lined = {}
        self.line_mean = {}
        self.span = None
        self.x_data = None
        self.x_index = None
        self.graph_option = Graph_Option(self.fig, self.ax1, self.ax2)

    def update(self):
        self.canvas.draw_idle()
        # fig.canvas.draw()
        # fig.canvas.flush_events()


class Model:
    """Classe Model\n
    interagisce (r/w) con il database/data,
    verifica che i dati di ingresso siano corretti"""

    def __init__(self, filename: str | None):
        self.filenames = filename
        self.df: pd.DataFrame | None = None  # read data
        self.df_rev: pd.DataFrame | None = None  # read revision data
        self.df_lt: pd.DataFrame | None = None  # clean cycle data
        self.cycle_data: dict = {}
        self.lifetest_analyzed: dict = {"distr": {},
                                        "NaN": {},
                                        "timeseries": {}}
        self.span_data = {}

    def file_to_read(self, revision: bool = False) -> tuple[str] | None:
        """Get files names from directory\n
        - Args: revision (bool, optional): Defaults to False.
            - 'False' ask for a RAW file
            - 'True' ask for an elaborated file\n
        Returns:
            tuple(str): iterator of file path"""
        if revision:
            fileoption = dict(
                title="Please select elaborated file:",
                filetypes=[
                    ("Output file", [".xlsx", ".parquet"]),
                    ("Data Distribution (Excel)", "*.xlsx"),
                    ("Time Series (parquet)", "*.parquet"),
                    ("All files", "*.*"),
                ],
            )
        else:
            fileoption = dict(
                title="Please select a RAW file:",
                defaultextension="*.xl*",
                filetypes=[
                    ("All files", "*.*"),
                    ("Text File", ["*.txt", "*.log"]),
                    ("CVS (tab separator)", ["*.cvs", ".xls"]),
                    ("CVS (comma separator)", "*.cvs"),
                    ("All Excel files", "*.xl*"),
                ],
            )

        files = filedialog.askopenfilenames(**fileoption)
        self.filenames = files if isinstance(files, tuple) else (files,)
        return self.filenames

    def file_typectrl(self, filepath: str, revision: bool = False):
        """Check if the selected file has the correct extension\n
        Args:
            - filepath (str): str filepath
            - revision (bool, optional): Defaults to None.
                - 'False' RAW file
                - 'True' elaborated file"""
        if revision:
            filextension = ("xlsx", "parquet")
        else:
            filextension = (
                "xls",
                "xlsx",
                "xlsm",
                "xlsb",
                "odf",
                "ods",
                "odt",
                "txt",
                "csv",
                "log"
            )

        if filepath.lower().endswith(filextension):
            pass
        else:
            self.filenames = None
            raise ValueError(
                "Invalid file extension\n"
                + "Select from:\n"
                + ", ".join(filextension)
            )

    def read_file(self, filepath: str, revision: bool = False):
        """Return pandas.Dataframe from a file in filepath\n
        - Args: revision (bool, optional): Defaults to False.
            - 'False' apre un file grezzo.
            - 'True' open a revision file based on its extension"""
        if revision:
            try:
                if filepath.endswith(".xlsx"):
                    temp_df = pd.read_excel(
                                            io=filepath,
                                            sheet_name=0,
                                            index_col=0,
                                            skipfooter=1,
                                            )
                elif filepath.endswith(".parquet"):
                    temp_df = pd.read_parquet(
                            filepath, engine="fastparquet"
                        )
            except Exception as e:
                raise e
        else:
            errors = []
            temp_df = None
            for func_ in read_functions:
                try:
                    temp_df = func_(filepath)
                    temp_df.Condition  # Check correct reading
                    break
                except Exception as e:
                    errors.append(e)
            if temp_df is None:
                raise Exception(errors)

        return temp_df

    def rearrange_file(self, data: pd.DataFrame, revision: bool = False):
        """### Preparation of data import\n
        - Update column name (no ' ', '_', '(', ')')
        - Extract correct Data column and sort it
        - Drop not useful column and all NaN column
        - Try to infer to float all object columns
        - interpolate columns with NaN, max 3, with backward value
        - Report NaN and Obj_Col\n
        Args:
            data (pd.DataFrame): data
            revision (bool, optional): Inform if data is raw. Defaults to False.
        """
        temp_data = data.copy()
        # update column names
        temp_data.columns = (
            temp_data.columns.str.strip()
            .str.replace(" ", "_", regex=True)
            .str.replace("(", "", regex=True)
            .str.replace(")", "", regex=True)
            .str.replace(",", "", regex=True)
        )

        # Extract correct Date column data
        if {"Date", "Time"}.issubset(set(temp_data.columns)):
            # old monitor file
            # temp_data.Date = pd.to_datetime(
            #     temp_data['Date'].astype(str) + " " + temp_data['Time'].astype(str)  # noqa: E501
            #     )
            temp_data.Date = pd.to_datetime(temp_data['Date'].astype(str), dayfirst=True)
        else:  # new monitor file
            temp_data.DateTime = pd.to_datetime(temp_data['DateTime'])
            temp_data.rename(columns={"DateTime": "Date"}, inplace=True)

        temp_data.sort_values(
            "Date", axis=0, ignore_index=True, inplace=True
            )

        # drop non functional column and all NaN columns
        [temp_data.drop(i, axis=1, inplace=True, errors='ignore')
         for i in ("Time", "RelTime", "Condition")]
        temp_data.dropna(axis=1, how="all", inplace=True)

        # replace value equal to 0 value with bfill, limit 1 consecutive
        temp_data.replace(0, None, method='bfill', limit=1, inplace=True)
        # replace str value in object columns (mixed type) to float (or NaN)
        obj_col = temp_data.select_dtypes("object").columns.to_list()
        for col in obj_col:
            temp_data[col] = temp_data[col].apply(
                pd.to_numeric, errors='coerce'
                ).astype(float)

        # interpolate columns NaN, max 3, with backward value
        temp_data.interpolate(axis=0, method="pad", limit=3, inplace=True)
        nan_col = temp_data.columns[temp_data.isna().any()].tolist()

        self.df = temp_data

        # warning
        if obj_col != [] or nan_col != []:
            Messagebox.show_warning(
                title="Import file warning",
                message="OBJECT COLUMNS: the following columns "
                f"contain mixed value\n{', '.join(obj_col)}\n\n"
                "NAN COLUMNS: the following columns"
                f"contain multiple NAN value\n{', '.join(nan_col)}\n"
                )

    def module_check_jit(self, df: pd.DataFrame) -> tuple[list, list]:
        """Controlla se ci sono errori nei moduli\n
        Args:
            f_xl (pd.DataFrame): dataframe da analizzare\n
        Returns:
            tuple[list, list]: moduli con errori, indici di errore di
            quei moduli"""
        matches = ["Iout_PM"]
        modul_current = [
            col for col in df.columns[2:] if any(x in col for x in matches)
        ]
        iteration = df.shape[0]
        num_pompe = int(len(modul_current) / 3)
        error_col = {}
        for col in modul_current:
            error_col[col] = []
        n = 1
        for num in range(num_pompe):
            mod1 = modul_current[(num * 3 + 0)]
            mod2 = modul_current[(num * 3 + 1)]
            mod3 = modul_current[(num * 3 + 2)]
            data1 = df[mod1].to_numpy()
            data2 = df[mod2].to_numpy()
            data3 = df[mod3].to_numpy()
            (
                error_col[mod1],
                error_col[mod2],
                error_col[mod3],
            ) = fnb.module_check_index_jit(data1, data2, data3, iteration, n)
        module_error = [
            keys for keys in error_col.keys() if len(error_col[keys]) > 0
        ]
        for mod in module_error:
            data = np.array(error_col[mod])
            error_col[mod] = fnb.correct_index_jit(data)
        if module_error == []:
            return module_error, []
        else:
            return module_error, [error_col[mod] for mod in module_error]

    ##########################################
    # ########### LIFETEST FUNCT ########### #
    ##########################################
    @singledispatchmethod
    def find_cycle(self, arg) -> dict[str, list[int | dt.timedelta]]:
        """Find all ON and OFF based on specified threshold. Then count the
        cycle and time during these

        Args:
            column (str | None, optional): _description_. Defaults to None.
            threshold (int | None, optional): _description_. Defaults to None.

        Returns:
            dict[str, list[int | dt.timedelta]]: _description_
        """
        raise NotImplementedError("Cannot Find Cycle")

    @find_cycle.register
    def _(self, arg: tuple):
        cicli_rslt = {}
        col, threshold = arg
        cicli_rslt[col] = self.__find_cycle(col, threshold)
        return cicli_rslt

    @find_cycle.register
    def _(self, arg: dict):
        cicli_rslt = {}
        for col, threshold in arg.items():
            cicli_rslt[col] = self.__find_cycle(col, threshold)
        return cicli_rslt

    def __find_cycle(self, col: str, threshold: int):
        spegnimenti, accensioni = fnb.speg_acc_index(
                self.df[col].to_numpy(), threshold
            )
        result = self.__cicli_time_jit(
                accensioni, spegnimenti, self.df.Date.to_numpy()
            )

        self.cycle_data[col] = {"threshold": threshold,
                                "on_index": accensioni,
                                "off_index": spegnimenti,
                                "cycle": result[0],
                                "time_on": result[1]}

        return result

    def __cicli_time_jit(
        self, P_on: np.ndarray, P_off: np.ndarray, time: np.ndarray
    ) -> Union[int, dt.timedelta]:
        """Calcolo del numero di cicli e del tempo di on.
        Considera anche i cicli non completi\n
        Args:
            P_on (np.ndarray): indici di inizio ciclo
            P_off (np.ndarray): indici di fine di ciclo
            time (np.ndarray): array dei tempi
        Returns:
            Union[int,dt.timedelta]: cicli e tempo totale in secondi"""
        cicli = 0
        time_on = 0
        time_on_cicli = 0
        sec = np.timedelta64(1, "s")

        if len(P_off) == 0 | len(P_on) == 0:
            return [0, 0]

        elif P_off[0] < P_on[0] and P_on[-1] > P_off[-1]:
            cicli = len(P_on) - 1
            for i in range(cicli):
                time_on_cicli += fnb.delta_time(
                    time[P_off[i + 1]], time[P_on[i]]
                )
            time_on = (
                time_on_cicli
                + fnb.delta_time(time[P_off[0]], time[0])
                + fnb.delta_time(time[-1], time[P_on[-1]])
            )
            cicli += 2

        elif P_off[0] < P_on[0] and P_on[-1] < P_off[-1]:
            cicli = len(P_on)
            for i in range(cicli):
                time_on_cicli += fnb.delta_time(
                    time[P_off[i + 1]], time[P_on[i]]
                )
            time_on = time_on_cicli + fnb.delta_time(time[P_off[0]], time[0])
            cicli += 1

        elif P_off[0] > P_on[0] and P_on[-1] > P_off[-1]:
            cicli = len(P_on) - 1
            for i in range(cicli):
                time_on_cicli += fnb.delta_time(time[P_off[i]], time[P_on[i]])
            time_on = time_on_cicli + fnb.delta_time(time[-1], time[P_on[-1]])
            cicli += 1

        elif P_off[0] > P_on[0] and P_on[-1] < P_off[-1]:
            cicli = len(P_on)
            for i in range(cicli):
                time_on_cicli += fnb.delta_time(time[P_off[i]], time[P_on[i]])
            time_on = time_on_cicli
        time_on_hms = dt.timedelta(seconds=time_on / sec)

        return [cicli, time_on_hms]

    def clean_cycle(self, column_name: str):
        """Remove not cycle time from data base on column passed\n
        Args:
            column_name (str): column for cycle identification
        """
        self.df_lt = self.df.copy()
        date = self.df_lt.Date.to_numpy().astype(dtype="timedelta64[ns]")
        column_data = self.cycle_data[column_name]
        threshold = column_data["threshold"]
        spegnimenti = np.array(column_data["off_index"], dtype=np.int64)
        accensioni = np.array(column_data["on_index"], dtype=np.int64)

        self.df_lt.Date = fnb.retime_jit2(date, spegnimenti, accensioni)

        self.df_lt.drop(
            index=self.df_lt[np.isnan(self.df_lt[column_name])].index,
            inplace=True,
        )
        self.df_lt.drop(
            index=self.df_lt[
                self.df_lt[column_name] < threshold
            ].index,
            inplace=True,
        )

    def data_distribution(
        self,
        column_name: str,
        current_mod: str = None,
        x_min: float = 0,
        x_max: float = 150,
        n_bins: float = 150,
    ):
        """Calculates the distribution of values ​​over time of the selected
        column. By default the column width is 1 and the range is 150"""
        data = self.df_lt

        current_column = data[column_name].replace(0, np.nan).to_numpy()
        if current_mod:
            current_mod = data[current_mod].replace(0, np.nan).to_numpy()
        time = data.Date.to_numpy()
        iteration = data.shape[0] - 1

        x_range = int(x_max) - int(x_min)
        n_bins = int(n_bins)
        bar_width = x_range / n_bins
        sec = np.timedelta64(1, "s")
        y, y_nan = fnb.distribution_jit2(
            current_column,
            current_mod,
            time,
            iteration,
            x_min,
            n_bins,
            bar_width,
            sec,
        )

        self.lifetest_analyzed["distr"][column_name] = y
        self.lifetest_analyzed["NaN"][column_name] = y_nan / sec

        return y

    def data_smoothing(self, column_name: str, revision=False):
        """Calculate rolling window data of column passed\n
        Args:
            column_name (str): column data name
            revision (bool, optional): tell if its not raw file. Defaults to False.
        """
        if revision:
            current_column = self.df_rev[column_name]
        else:
            current_column = self.df_lt[column_name]
        y = current_column.dropna().replace(0, np.nan)
        y = y.rolling(
            1000,
            min_periods=250,
            win_type="kaiser",
            center=True,
            closed="neither",
        ).mean(beta=8)

        self.lifetest_analyzed["timeseries"][column_name] = y

    def create_export_file(
        self, cicli_rslt: list[int], merge: bool = False, module: str = None,
        smooth: bool = False, x_max: int = 150, n_bin: int = 150
    ):
        """Crea file excel di report con le distribuzioni di temperatura\n
        Args:
            cicli_rslt (list[int]): cycle result for selected column and
            threshold
            merge (bool, optional): if merge file. Defaults to False.
            module (str, optional): Module to reset. Defaults to None.
            smooth (bool, optional): if export timeseries too. Defaults to
            False.
            x_max (int, optional): X max value. Defaults to 150.
            n_bin (int, optional): Number of histogram bins. Defaults to 150.
        """
        try:
            cicli_df = pd.DataFrame(
                [cicli_rslt], columns=["Cicli", "Time_on(s)"]
            )
            step = int(x_max/n_bin)
            export_data = pd.DataFrame(data=self.lifetest_analyzed["distr"],
                                       index=list(range(0, x_max, step))
                                       )
            export_nan = pd.DataFrame(data=self.lifetest_analyzed["NaN"],
                                      index=["NotANumber"])
            export_distr = pd.concat([export_data, export_nan])
            if smooth:
                export_timeseries = pd.DataFrame(
                    data=self.lifetest_analyzed["timeseries"]
                    )
                export_timeseries.insert(0, "Date", self.df_lt.Date)

            if merge is False:
                export_mean = self.__data_distr_mean_jit(export_distr)
                export_df = pd.concat([export_distr, export_mean])

                new_file = filedialog.asksaveasfilename(
                    initialfile="output.xlsx",
                    defaultextension=".xlsx",
                    filetypes=[
                        ("Tutti i file", "*.*"),
                        ("Cartella excel (.xlsx)", "*.xlsx"),
                    ],
                )
                if new_file == "":
                    return

                if new_file.endswith(".xlsx") is True:
                    with pd.ExcelWriter(new_file) as writer:
                        export_df.to_excel(writer, sheet_name="Distribution")
                        cicli_df.to_excel(writer, sheet_name="Cicli")
                elif new_file.endswith(".xls") is True:
                    new_file = new_file.replace(".xls", ".xlsx")
                    with pd.ExcelWriter(new_file) as writer:
                        export_df.to_excel(
                            writer,
                            sheet_name="Distribution",
                            engine="xlsxwriter",
                        )
                        cicli_df.to_excel(writer, sheet_name="Cicli")
                    Messagebox.show_info(
                        title="Info",
                        message="Il formato xls non è più supportato\n"
                        "E' stato salvato in formato xlxs",
                    )
                if smooth:
                    new_file = new_file.replace(".xlsx", ".parquet")
                    export_timeseries.to_parquet(new_file,
                                                 engine="fastparquet")

            # ----- MERGE ----- #
            elif merge is True:
                merge_filename = filedialog.askopenfilename(
                    title="Select a cumulation file to merge",
                    defaultextension="*.xlsx",
                    filetypes=[
                        ("Tutti i File Excel", "*.xl*"),
                        ("Tutti i file", "*.*"),
                    ],
                )
                merged_filename = filedialog.asksaveasfilename(
                    title="Select a new file name",
                    defaultextension="*.xlsx",
                    filetypes=[
                        ("Tutti i File Excel", "*.xlsx"),
                        ("Tutti i file", "*.*"),
                    ],
                )
                try:
                    sheet = 0
                    to_merge_f_xl = pd.read_excel(
                        io=merge_filename,
                        sheet_name=sheet,
                        index_col=0,
                        skipfooter=2,
                    )
                    to_merge_cicli = pd.read_excel(
                        io=merge_filename, sheet_name=sheet + 1, index_col=0
                    )
                    columns_1 = to_merge_f_xl.columns.to_list()
                    columns_2 = export_distr.columns.to_list()
                    if module.isnumeric():
                        module_matches = [
                            "Vout_PM",
                            "Iout_PM",
                            "Vout_SP_PM",
                            "Iout_SP_PM",
                            "Tinlet_PM",
                            "T_PFC_PM",
                            "T_DCDC1_PM",
                            "T_DCDC2_PM",
                            "Fan_Voltage_PM",
                            "Vin1_PM",
                            "Vin2_PM",
                            "Vin3_PM",
                            "Status_PM",
                        ]
                        module_match = [f"{x}{int(module)}"
                                        for x in module_matches]
                        col_to_drop = [
                            col
                            for col in to_merge_f_xl.columns
                            if any(x in col for x in module_match)
                        ]
                        to_merge_f_xl.drop(col_to_drop, axis=1, inplace=True)
                    columns = list(set(columns_2) - set(columns_1)) + columns_1
                    df_merge = to_merge_f_xl.add(export_distr, fill_value=0)
                    export_mean = self.__data_distr_mean_jit(df_merge)
                    df_merge = pd.concat([df_merge, export_mean])
                    df_merge = df_merge[columns]
                    cicli_merge = to_merge_cicli.add(cicli_df, fill_value=0)

                    with pd.ExcelWriter(merged_filename) as writer:
                        df_merge.to_excel(
                            writer, sheet_name="Distribution", columns=columns
                        )
                        cicli_merge.to_excel(writer, sheet_name="Cicli")
                except Exception:
                    raise Warning("Nessun file xlsx unito")

                if smooth:
                    try:
                        to_merge_timeseries = pd.read_parquet(
                            merge_filename.replace(".xlsx", ".parquet"),
                            engine="fastparquet",
                        )
                        if module.isnumeric():
                            module_match = [f"PM{int(module)}"]
                            col_to_drop = [
                                col
                                for col in to_merge_f_xl.columns
                                if any(x in col for x in module_match)
                            ]
                            to_merge_timeseries.drop(
                                col_to_drop, axis=1, inplace=True
                            )
                        delta_t = to_merge_timeseries.Date.values[
                            -1
                        ] + np.timedelta64(15, "s")
                        export_timeseries.Date = export_timeseries.Date + delta_t
                        merge_timeseries = pd.concat(
                            [to_merge_timeseries, export_timeseries],
                            ignore_index=True,
                        )
                        merge_timeseries.to_parquet(
                            merged_filename.replace(".xlsx", ".parquet"),
                            engine="fastparquet",
                        )
                    except Exception:
                        raise Warning("Nessun file parquet unito")

        except Exception as e:
            raise (e)

    def __data_distr_mean_jit(self, data: pd.DataFrame) -> pd.DataFrame:
        """Return new Dataframe with Mean and total time in hours of data
        passed\n
        Args:
            data (pd.DataFrame): data to used"""
        means = {}
        time = {}
        iteration = data.shape[0] - 1
        for column in data.columns:
            means[column], time[column] = fnb.ponderate_mean(
                data[column].to_numpy(), iteration
            )
        data = [means, time]
        distr_mean = pd.DataFrame(data=data, index=["mean", "time"])
        return distr_mean

    ##########################################
    # ########### THERMAL FUNCT ########### #
    ##########################################
    def smoothing(self, y: pd.Series | np.ndarray) -> np.ndarray:
        """Smoothing dei dati tramite 'savgol_filter'\n
        Args:
            y (pd.Series|np.ndarray): Dati su cui eseguire lo smooothing

        Returns:
            np.ndarray: smoothing data"""
        y = savgol_filter(
            y, 53, 3  # window size used for filtering
        )  # order of fitted polynomial
        return y

    def data_elaboration(
        self, data: str, index: list[int] = None
    ) -> None:
        """Elabora i dati\n
        Args:
            data (str): Nome della serie da elaborare
            decim (int, optional): Numero dei primi elementi da non
            considerare. Defaults to 0.
            index (list[int], optional): lista con indice di partenza e indice
            di fine per calcoli su zona specifica. Defaults to None.\n
        Returns:
            tuple[float,tuple[float],float,tuple[float]]: restituisce
            'mean, max-min, mean(spec), max-min(spec)'"""
        # mean = self.df[data][decim:].mean()
        # max = self.df[data].max()
        # min = self.df[data].min()

        subdf = self.df.loc[:, self.df.columns != 'Date'].copy()
        subdf.replace(0, np.NaN, inplace=True)
        subdf.interpolate(axis=0, method='linear', limit=3, inplace=True)
        if index is not None:
            mean_p = subdf[data][index[0]: index[1]].mean()
            max_p = subdf[data][index[0]: index[1]].max()
            min_p = subdf[data][index[0]: index[1]].min()
        else:
            mean_p = np.nan
            max_p = np.nan
            min_p = np.nan

        self.span_data[data] = [mean_p, max_p, min_p]


class Ctrl_Thermal:
    model: Model
    view: View
    statusbar: Statusbar

    def plot_th_timeseries(self, smooth: bool = False):
        """Handle all plot process for thermal timeseries\n
        Args:
            smooth (bool, optional): if plot shoothed value. Defaults to False.
        """
        frame = self.view.th_plot_frm
        frame.clear()

        col_slc2 = set(self.view.twin_y.get())
        col_slc1 = set(self.view.frm_option.get()) - col_slc2

        n_graph = len(col_slc1) + len(col_slc2)
        color_c = iter(plt.cm.rainbow(np.linspace(0, 1, n_graph)))
        timedelta = self.model.df.Date.values[0] - np.datetime64("2021-01-01")
        frame.x_data = x = self.model.df.Date - timedelta

        for data in col_slc1:
            self._plot(frame, x, data, color_c, smooth, 1)
        for data in col_slc2:
            self._plot(frame, x, data, color_c, smooth, 2)

        _ = mplcursors.cursor([frame.ax1, frame.ax2], highlight=True)
        frame.ax1.grid()

        # get graph option from view
        self.update_th_fig(False, columns=[col_slc1, col_slc2])

        # other options
        frame.ax1.xaxis.set_major_locator(
            mdates.AutoDateLocator(maxticks=11, minticks=4)
        )
        frame.ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        plt.margins(0.01, 0.01)
        plt.rcParams["axes.autolimit_mode"] = "round_numbers"
        frame.ax1.autoscale(enable=True, axis="y", tight=False)
        frame.ax2.autoscale(enable=True, axis="y", tight=False)
        handles, labels = [
            (a + b)
            for a, b in zip(
                frame.ax1.get_legend_handles_labels(),
                frame.ax2.get_legend_handles_labels(),
            )
        ]
        frame.ax2.legend(handles, labels, fancybox=True)
        if len(col_slc2) == 0:
            frame.ax2.yaxis.set_visible(False)
        frame._legend(len(col_slc1))
        frame.show_legend(self.view.legend_th.get())

        frame._createSpan()
        frame.canvas.draw_idle()
        # altri aggiornamenti
        self.view.th_analysis_btn.configure(state="normal")
        self.view.th_export_btn.configure(state="disabled")

    def _plot(
        self,
        frame: TH_TimeSerie,
        x: pd.Series,
        data: str,
        color_c: Iterator,
        smooth: bool,
        yaxes: Literal[1, 2],
    ):
        """Realizza plotting vero e proprio

        Args:
            frame (tk.Frame): frame su cui eseguire il plot
            x (pd.Series): valori dell'asse x
            data (str): Nome Serie da usare per valori asse y
            color_c (Iterator): Iteratore dei colori per le linee
            smooth (bool): se True plotta dati con smoothing
            yaxes (Literal[1,2]): asse y su cui stampare i dati
        """
        if smooth is False:
            y = self.model.df[data]
        elif smooth is True:
            y = self.model.smoothing(self.model.df[data])
        if yaxes == 1:
            frame.line.append(
                frame.ax1.plot(
                    x, y, linewidth=1, label=data, color=next(color_c)
                )[0]
            )
        elif yaxes == 2:
            frame.line.append(
                frame.ax2.plot(
                    x, y, linewidth=1, label=data, color=next(color_c)
                )[0]
            )

    def analysis_th(self):
        """Handle all thermal analysis process"""
        col_list = self.model.df.columns.to_list()[1::]
        col_slc2 = set(self.view.twin_y.get())
        col_slc1 = set(self.view.frm_option.get()) - col_slc2
        self.__analisi_data(col_list, col_slc1 | col_slc2)
        if self.view.show_mean_th.get():
            self.__analisi_plot(col_slc1, col_slc2)
        self.view.thermal.tab(1, state="normal")
        self.view.th_export_btn.configure(state="normal")

    def __analisi_data(self, col_list: list, col_selected: list):
        """Handle data elaboration and show result\n
        Args:
            col_list (list): all column
            col_selected (list): column selected
        """
        index = self.view.th_plot_frm.x_index
        for data in col_list:
            self.model.data_elaboration(data, index)
        result = self.model.span_data
        data = [["%.4f" % elem for elem in val] for val in result.values()]
        row_index = [key for key in result.keys()]
        data_p = [
            ["%.4f" % elem for elem in val]
            for key, val in result.items()
            if key in col_selected
        ]
        row_index_p = [key for key in result.keys() if key in col_selected]
        
        self.view.index_lbl.configure(text=f"Samples: {index[1]-index[0]}")
        self.view.debug_res.total_columns(number=len(row_index_p))
        self.view.debug_res.headers(newheaders=row_index_p)
        self.view.debug_res.set_sheet_data(
            data=[[i[0] for i in data_p]],
            reset_col_positions=True,
            reset_row_positions=True,
            redraw=True,
            verify=False,
            reset_highlights=False,
            )

        # self.view.detail_res.total_rows(number=len(row_index_p))
        # self.view.detail_res.headers(newheaders=row_index_p)
        self.view.detail_res.set_sheet_data(
            # data=list(zip(*data_p)),
            data=data_p,
            reset_col_positions=True,
            reset_row_positions=True,
            redraw=True,
            verify=False,
            reset_highlights=False,
            )
        self.view.detail_res.row_index(
            newindex=row_index_p,
            index=None,
            reset_row_positions=False,
            show_index_if_not_sheet=True,
        )

        # self.view.all_res.total_rows(number=len(row_index))
        # self.view.all_res.headers(newheaders=row_index)
        self.view.all_res.set_sheet_data(
            # data=list(zip(*data)),
            data=data,
            reset_col_positions=True,
            reset_row_positions=True,
            redraw=True,
            verify=False,
            reset_highlights=False,
            )
        self.view.all_res.row_index(
            newindex=row_index,
            index=None,
            reset_row_positions=False,
            show_index_if_not_sheet=True,
        )

    def __analisi_plot(self, col_slc1: list, col_slc2: list):
        """Plot selected column\n
        Args:
            col_slc1 (list): column for first y axes
            col_slc2 (list): column for twin y axes
        """
        frame = self.view.th_plot_frm
        col_selected = col_slc1 | col_slc2
        # ----- remove mean_spec line -----
        for ax in frame.fig.axes:
            _, label = ax.get_legend_handles_labels()
            if bool(frame.line_mean):
                [ax.lines.remove(line) for _, line in frame.line_mean.items()
                 if line in ax.lines]

        # ----- plot elaborate data -----
        color_c = iter(plt.cm.rainbow(np.linspace(0, 1, len(col_selected))))
        if frame.x_index is not None:
            for data in col_selected:
                mean_p = self.model.span_data[data][0]
                if np.isnan(mean_p):
                    continue
                elif data in col_slc1:
                    frame.line_mean[data] = frame.ax1.axhline(
                        mean_p,
                        label=f"{data} mean",
                        linewidth=0.7,
                        color=next(color_c),
                        linestyle="--",
                    )
                elif data in col_slc2:
                    frame.line_mean[data] = frame.ax2.axhline(
                        mean_p,
                        label=f"{data} mean",
                        linewidth=0.7,
                        color=next(color_c),
                        linestyle="--",
                    )

        # ----- update label -----
        handles, labels = [
            (a + b)
            for a, b in zip(
                frame.ax1.get_legend_handles_labels(),
                frame.ax2.get_legend_handles_labels(),
            )
        ]
        frame.ax2.legend(handles, labels)
        frame._legend(len(col_slc1))
        frame.show_legend(self.view.legend_th.get())
        frame.canvas.draw_idle()

    def export_thermal_data(self, merge=False):
        """Handle export process\n
        Args:
            merge (bool, optional): if merge export data to a selected file.
            Defaults to False.
        """
        if merge:
            filename = filedialog.askopenfilename(
                title='Select a cumulation file to merge',
                defaultextension="*.xlsx",
                filetypes=[("Tutti i File Excel", "*.xl*"),
                           ("Tutti i file", "*.*")]
                )
        else:
            filename = filedialog.asksaveasfilename(
                initialfile='output.xlsx',
                defaultextension='.xlsx',
                filetypes=[('Tutti i file', '*.*'),
                           ('Cartella excel (.xlsx)', '*.xlsx')]
                )

        if filename:
            sub_data, data_mean, data_ptp = self.__exp_data()

            if merge:
                sheet = 0
                to_merge_data = pd.read_excel(io=filename,
                                              sheet_name=sheet,
                                              index_col=0)
                to_merge_mean = pd.read_excel(io=filename,
                                              sheet_name=sheet+1,
                                              index_col=0)
                to_merge_ptp = pd.read_excel(io=filename,
                                             sheet_name=sheet+2,
                                             index_col=0)
                data_merge = pd.concat([to_merge_data, sub_data])
                mean_merge = pd.concat([to_merge_mean, data_mean])
                ptp_merge = pd.concat([to_merge_ptp, data_ptp])

                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    data_merge.to_excel(writer, sheet_name='Data')
                    mean_merge.to_excel(writer, sheet_name='Mean')
                    ptp_merge.to_excel(writer, sheet_name='PtP')

            else:
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    sub_data.to_excel(writer, sheet_name='Data')
                    data_mean.to_excel(writer, sheet_name='Mean')
                    data_ptp.to_excel(writer, sheet_name='PtP')

        self.statusbar.update_status(True, "Export complete")

    def __exp_data(self):
        """Return the correct data to export\n"""
        index = self.view.th_plot_frm.x_index
        try:
            sub_data = self.model.df[index[0]:index[1]].copy()
        except Exception:
            sub_data = self.model.df.copy()
        finally:
            sub_data.set_index("Date", inplace=True)
        data_mean = sub_data.mean().to_frame().transpose()
        data_mean.set_index(pd.Series(sub_data.index.array[0]), inplace=True)
        data_ptp = (sub_data.max() - sub_data.min()).to_frame().transpose()
        data_ptp.set_index(pd.Series(sub_data.index.array[0]), inplace=True)
        return sub_data, data_mean, data_ptp

    def update_th_fig(self, redraw=False, columns=[{""}, {""}]):
        frame = self.view.th_plot_frm

        title = self.view.th_title_ent.get()
        x_label = self.view.th_x_ent.get()
        y_label1 = self.view.th_y_ent.get()
        y_label2 = self.view.th_twiny_ent.get()
        frame.graph_option.title = title if title != "" else ", ".join(columns[0] | columns[1])
        frame.graph_option.x_axis = x_label
        frame.graph_option.y_axis = [y_label1, y_label2]
        if redraw:
            frame.update()

    def th_add_line(self, direction: Literal["x", "y"], value: float, axis: int = 1):
        frame = self.view.th_plot_frm
        match [direction, axis]:
            case ["x", 1]:
                frame.ax1.axhline(y=value, color="black", linestyle="--")
            case ["x", 2]:
                frame.ax2.axhline(y=value, color="black", linestyle="--")
            case ["y", _]:
                frame.ax1.axvline(x=value, color="black", linestyle="--")
        frame.canvas.draw_idle()


class Ctrl_LifeTest:  # TODO compare
    model: Model
    view: View
    statusbar: Statusbar
    compare_wd = None

    def cicli(self):
        """Calculate the number of cycles and the associated time for all
        selected columns based on the threshold values ​​passed by the user"""
        try:
            cln_slct = self.view.col_frm.get()

            if len(cln_slct) == 0:
                raise BufferError("Selezionare almeno una colonna")
            if self.view.soglie_txt.compare("end-1c", "==", "1.0"):
                raise ValueError("Inserire almeno un valore di soglia")

            cln_soglia = []
            for i in range(len(cln_slct)):
                a = i + 1
                soglia = self.view.soglie_txt.get(f"{a}.0", f"{a}.0 lineend")
                if soglia.isnumeric():
                    cln_soglia.append(int(soglia))
                else:
                    raise TypeError("Inserire valori numerici")

            cicli_opt = {col: soglia
                         for col, soglia in zip(cln_slct, cln_soglia)}

            cicli_rslt = self.model.find_cycle(cicli_opt)
            # {col: {"soglia": soglia}
            #              for col, soglia in zip(cln_slct, cln_soglia)}
            # self.model.cicli_resume = {col: soglia
            #              for col, soglia in zip(cln_slct, cln_soglia)}
            # self.model.cicli_resume = {
            #     col: {"soglia": soglia,
            #           "cicli": cicli,
            #           "time": time_}
            #     for col, soglia in zip(cln_slct, cln_soglia)}
            # ----- UPDATE VIEW ----- #
            t = self.view.cicli_result_tv
            t.clear()
            for keys in cicli_rslt.keys():
                t.insert(
                    parent="",
                    index="end",
                    values=(
                        f"{keys}",
                        f"{cicli_rslt[keys][0]}",
                        f"{str(cicli_rslt[keys][1])}",
                    ),
                )
            self.view.analysis_btn["state"] = "normal"
            self.view.lifetest.tab(1, state="normal")
            self.view.lifetest.tab(2, state="normal")
            self.statusbar.update_status(
                True, "Calcoli Cicli di Lavoro completato"
            )

        except BufferError as warning:
            self.view.show_warning(warning)
        except ValueError as warning:
            self.view.show_warning(warning)
        except TypeError as error:
            self.view.show_error(error)

    def analysis(self):
        """Cleans data based on selected column with its threshold. Then it
        calculates the distributions and the timeseries"""

        row_ = self.view.cicli_result_tv.selection()
        val_ = self.view.cicli_result_tv.item(row_)["values"]
        column_slct: str = val_[0]
        self.model.clean_cycle(column_slct)

        columns_ = list(self.model.df_lt.columns[1:])
        self._all_distribution(columns_)
        self.view.parent.update()
        self._all_timeseries(columns_)
        self.view.lifetest.tab(1, state="normal")
        self.view.lifetest.tab(2, state="normal")

    def _all_distribution(self, distr_column: list[str]):
        """Calculates default distribution"""
        # populate combobox
        self.statusbar.update_status(True, "Calcolo distribuzioni in corso...")
        self.view.parent.update()
        self.view.distr_tab.col_slc_cmb["values"] = distr_column

        # calcolate the default distribution
        for column in distr_column:
            self.model.data_distribution(column)

        # aggiornamento
        self.view.distr_tab.set_controller(self)
        self.statusbar.update_status(True, "Calcolo distribuzioni completato")

    def _all_timeseries(self, timeseries_column: list[str]):
        """Calculates default TIMESERIES"""
        # populate combobox
        self.statusbar.update_status(True, "Calcolo timeseries in corso...")
        self.view.parent.update()
        self.view.timeseries_tab.col_slc_cmb["values"] = timeseries_column

        # calcolate the timeseries regression
        try:
            for column in timeseries_column:
                self.model.data_smoothing(column)
        except Exception as error:
            self.view.show_error(error)

        # aggiornamento
        self.view.timeseries_tab.set_controller(self)
        self.statusbar.update_status(True, "Analisi completata")

    def distr_plot(self, distr_tab: DataDistribution, adjust: bool = False):
        """Plot distribution data\n
        Args:
            distr_tab (DataDistribution): graph frame
            adjust (bool, optional): plotting not default. Defaults to False.
        """
        column_slct = distr_tab.col_slc_cmb.get()
        if adjust is True:
            x_max = distr_tab.x_max.get()
            x_min = distr_tab.x_min.get()
            n_bin = distr_tab.bins.get()
            y = self.model.data_distribution(
                column_slct, x_min=x_min, x_max=x_max, n_bins=n_bin
            )
            x = np.array(range(len(y)))
            width = (int(x_max) - int(x_min)) / int(n_bin)
            x = x * (width) + x_min
        else:
            x = list(range(1, 151))
            width = 1

        distr_tab.fig.delaxes(distr_tab.ax)
        distr_tab.ax = distr_tab.fig.add_subplot(111)
        distr_tab.fig.subplots_adjust(
            left=0.125, bottom=0.1, top=0.95, right=0.95
            )
        # if big_fig:
        #     y = self.model.data_distr[column_slct][:-2]
        #     frame.fig.subplots_adjust(bottom=0.14, top=0.95, right=0.95)
        #     mean = self.model.data_distr[column_slct]["mean"]

        y = self.model.lifetest_analyzed["distr"][column_slct]
        mean = self.model.df_lt[column_slct].mean()

        distr_tab.ax.axvline(
            mean, color="green", linewidth=1, label=f"media:{mean:.4f}"
        )
        distr_tab.ax.bar(
            x,
            y,
            width=width,
            edgecolor="white",
            linewidth=0.7,
            label=f"{column_slct}",
        )
        distr_tab.ax.set_ylabel("Seconds")
        distr_tab.ax.grid()
        distr_tab.ax.legend()
        distr_tab.canvas.draw()

    def plot_timeseries(self, timeseries_tab: LT_TimeSerie):
        """Plotting timeseries\n
        Args:
            timeseries_tab (LT_TimeSerie): graph frame
        """
        column_slct = timeseries_tab.col_slc_cmb.get()
        y_smooth = self.model.lifetest_analyzed["timeseries"][column_slct]
        # if big_fig:
        #     x = np.array(
        #         fnb.hms(
        #             self.model.f_xl.Date.to_numpy() / np.timedelta64(1, "s")
        #         )
        #     )
        #     y = self.model.f_xl[column_slct].dropna().replace(0, np.nan)
        #     length = len(y.index)

        # x = np.array(
        #     fnb.hms(
        #         self.model.df_lt.Date.to_numpy() / np.timedelta64(1, "s")
        #     )
        # )
        x = self.model.df_lt.Date + np.datetime64("2022-01-01")
        y = self.model.df_lt[column_slct].dropna().replace(0, np.nan)
        length = y.index[-1]

        timeseries_tab.fig.delaxes(timeseries_tab.ax)
        timeseries_tab.ax = timeseries_tab.fig.add_subplot(111)
        timeseries_tab.fig.subplots_adjust(
            left=0.125, bottom=0.1, top=0.95, right=0.95
            )
        timeseries_tab.xlim_max = x.iloc[-1]
        timeseries_tab.xlim_min = x.iloc[0]
        timeseries_tab.ax.plot(x[0:length], y,
                               linewidth=0.7, label=column_slct)
        if timeseries_tab.smoothing.get():
            timeseries_tab.ax.plot(x[0:length], y_smooth,
                                   linewidth=0.6, color="r",
                                   label=f"{column_slct}_smooth")
        timeseries_tab.ax.set_ylabel("Temp")
        timeseries_tab.ax.set_title(column_slct)
        timeseries_tab.ax.grid()
        timeseries_tab.ax.legend()

        self._loc = mdates.AutoDateLocator(minticks=3, maxticks=11)
        self._form = mdates.AutoDateFormatter(self._loc, defaultfmt="%H:%M:%S")
        timeseries_tab.ax.xaxis.set_major_locator(self._loc)

        timeseries_tab.ax.xaxis.set_major_formatter(self._form)
        # timeseries_tab.ax.xaxis.set_major_formatter(
        #     mdates.ConciseDateFormatter(
        #         self._loc,
        #         zero_formats=['', '%Y', '%b', '%d', '%H:%M', '%H:%M:%S'],
        #         offset_formats=['', '', '', '%d', '%d', '%d %H:%M'],
        #         formats=['%Y', '%b', '%d', '%H:%M', '%H:%M:%S', '%S.%f']
        #         )
        #     )

        plt.margins(0.01, 0.01)
        timeseries_tab.ax.autoscale(enable=True, axis="y", tight=False)

        timeseries_tab.canvas.draw()

    def compare_distr(self):  # TODO compare time. Maybe more column select?
        pass

    def export_all_option(self, all_=True):
        """Open Export windows\n
        Args:
            all_ (bool, optional): if all data or only distribution.
            Defaults to True.
        """
        with open(f"{APP_PATH}\\preset.yaml", "r") as f:
            preset = yaml.safe_load(f)
        # db = pd.read_excel(f"{APP_PATH}\\preset.xlsx",
        #                    sheet_name=0)
        # matches = {
        #     k1: [v for _, v in v1.items() if v == v and v is not np.nan]
        #     for k1, v1 in db.to_dict().items()
        # }
        matches = preset["lifetest"]
        matches["ALL"] = list(self.model.df.columns[1:])
        matches["NONE"] = []
        self.view.option_wd = LT_ExportOpt(self.view, all_)
        self.view.option_wd.match = matches
        self.view.option_wd.file_cmb["value"] = list(matches.keys())

    def export_all_option_control(self) -> tuple[str, int, int, int]:
        """Controlla se le opzioni di export inserite sono corrette"""
        # colonna cicli
        col_cicli = self.view.option_wd.col_text.get()
        if col_cicli == "":
            raise Warning("Inserire nome di una colonna e un valore di soglia")
        elif col_cicli not in list(self.model.df.columns):
            raise Exception("Nome colonna non presente")

        # soglia cicli
        soglia_cicli = self.view.option_wd.soglia_text.get()
        if soglia_cicli == "":
            raise Exception(
                "Inserire nome di una colonna e un valore di soglia"
            )
        elif soglia_cicli.isnumeric() is False:
            raise TypeError("Inserire un valore numerico")
        elif soglia_cicli.isnumeric() is True:
            soglia_cicli = int(soglia_cicli)

        # width bin
        bar_width = self.view.option_wd.width_.get()
        if bar_width == "":
            raise Exception(
                "Inserire un valore di 'bar width'"
            )
        bar_width = int(bar_width)

        # range histogram
        x_max = self.view.option_wd.range.get()
        if x_max == "":
            raise Exception(
                "Inserire un valore di range"
            )
        n_bin = round(x_max/bar_width)
        x_max = bar_width*n_bin

        return col_cicli, soglia_cicli, x_max, n_bin

    def export_all_process(self, all_: bool):
        """Comanda il processo di creazione del file di report"""
        try:
            col_cicli, soglia_cicli, x_max, n_bin = self.export_all_option_control()  # noqa: E501
            self.statusbar.update_status(
                True, "Calcoli per export in corso..."
            )
            self.view.parent.update()
            self.model.lifetest_analyzed = {"distr": {},
                                            "NaN": {},
                                            "timeseries": {}}
            cicli_rslt = self.model.find_cycle((col_cicli, soglia_cicli))
            cicli_rslt[col_cicli][1] = cicli_rslt[col_cicli][1].total_seconds()

            distr_col: list[str] = list(self.view.option_wd.col_frm.get())

            self.model.clean_cycle(col_cicli)
            module_matches = [
                "Vout_PM",
                "Iout_PM",
                "Vout_SP_PM",
                "Iout_SP_PM",
                "Tinlet_PM",
                "T_PFC_PM",
                "T_DCDC1_PM",
                "T_DCDC2_PM",
                "Fan_Voltage_PM",
                "Vin1_PM",
                "Vin2_PM",
                "Vin3_PM",
                "Status_PM",
            ]
            for column in distr_col:
                if any(x in column for x in module_matches):
                    mod = column[-3:]
                    self.model.data_distribution(column, f"Iout_{mod}",
                                                 x_max=x_max, n_bins=n_bin)
                else:
                    self.model.data_distribution(column,
                                                 x_max=x_max, n_bins=n_bin)
                if all_:
                    self.model.data_smoothing(column)

            self.model.create_export_file(
                cicli_rslt=cicli_rslt[col_cicli],
                merge=self.view.option_wd.merge_option.get(),
                module=self.view.option_wd.module.get(),
                smooth=all_,
                x_max=x_max,
                n_bin=n_bin
            )
            self.statusbar.update_status(True, "File esportato correttamente")

        except Warning as warning:
            self.view.show_warning(warning)
            self.view.option_wd.focus_set()
            self.statusbar.update_status(
                True, "File esportato correttamente - WARNING"
            )
        except TypeError as error:
            self.view.show_error(error)
            self.view.option_wd.focus_set()
            self.statusbar.update_status(True, "ERRORE")
        except Exception as error:
            self.view.show_error(error)
            self.view.option_wd.focus_set()
            self.statusbar.update_status(True, "ERRORE")
        else:
            self.view.option_wd.destroy()


class Controller(Ctrl_Thermal, Ctrl_LifeTest):
    """
    # Class Controller:
    logica generale del programma,
    riceve gli input da View(tramite users),
    esegue logica, si relaziona col model,
    passa i risultati al View
    """
    def __init__(self, model: Model, view: View, statusbar: Statusbar):
        self.model = model
        self.view = view
        self.statusbar = statusbar

    def select_files(self):
        """Seleziona file e resetta View and Model"""
        try:
            files = self.model.file_to_read()
            for file in files:
                self.model.file_typectrl(file)
            if files:
                # ----- READ FILE ----- #
                file_df = pd.DataFrame()
                for file in files:
                    temp_df = self.model.read_file(file)
                    file_df = pd.concat((file_df, temp_df))
                self.model.rearrange_file(file_df)

                # if is a LifeTest file should run correctly
                try:
                    self.module_check()
                except Exception:
                    pass

                columns = list(self.model.df.columns[1:])

                with open(f"{APP_PATH}\\preset.yaml", "r") as f:
                    preset = yaml.safe_load(f)
                def_col = preset["thermal"]["DEFAULT"]
                def_col = [i.strip()
                           .replace(" ", "_")
                           .replace("(", "")
                           .replace(")", "")
                           .replace(",", "")
                           for i in def_col]

                # ----- RESET LIFETEST ----- #
                self.__clear_view_lt()
                self.view.col_frm.insert(available=columns, selected=def_col)

                # ----- RESET THERMAL ----- #
                self.__clear_view_th()
                self.view.frm_option.insert(available=columns, selected=def_col)
                self.view.debug_res.total_columns(number=len(columns))
                self.view.debug_res.headers(newheaders=columns)
                self.view.debug_res.refresh(redraw_header=True,
                                         redraw_row_index=True)

                # ----- RESET MODEL ----- #
                self.model.df_rev = None
                self.model.df_lt = None
                self.model.cycle_data: dict = {}
                self.model.lifetest_analyzed: dict = {"distr": {},
                                                      "NaN": {},
                                                      "timeseries": {}}

                self.model.span_data = {}

                self.view.parent.title(
                    f"DataAnalysis - {path.basename(file)}"
                )
                self.statusbar.update_status(
                    True, "File importato correttamente"
                )

        except ValueError as error:
            self.view.show_error(error)
        except Exception as error:
            self.view.show_error(error)

    def __clear_view_lt(self):
        """Clear Lifetest Tab"""
        self.view.col_frm.clear_list()
        self.view.analysis_btn["state"] = "disabled"
        self.view.cicli_result_tv.clear()
        self.view.lifetest.tab(1, state="disabled")
        self.view.lifetest.tab(2, state="disabled")
        self.view.lifetest.select(0)
        self.view.distr_tab.clear()
        self.view.timeseries_tab.clear()
        # TODO compare tab reset
        # self.view.col_compare_frm._setzero()
        # self.view.col_compare_frm._populate(col_list=columns)
        # self.view.compare_distr_btn["state"] = "disabled"
        # self.view.compare_time_btn["state"] = "disabled"
        # self.view.nb.tab(3, state="disabled")

    def __clear_view_th(self):
        """Clear thermal tab"""
        self.view.frm_option.clear_list()
        self.view.twin_y.clear_list()
        self.view.th_analysis_btn.configure(state="disabled")
        self.view.th_export_btn.configure(state="disabled")
        self.view.th_plot_frm.clear()

        self.view.debug_res.set_sheet_data(data=[[]])
        self.view.index_lbl.configure(text=f"Samples: ")

        # TODO clear result
        self.view.thermal.tab(1, state="disabled")
        self.view.detail_res.set_sheet_data(data=[[]])
        self.view.all_res.set_sheet_data(data=[[]])
        # self.view.result_selected.reset_data()
        # self.view.result_all.reset_data()

    def module_check(self):
        """Check during import if some module has error"""
        module_broke, index_broke = self.model.module_check_jit(
            self.model.df
        )
        if len(module_broke) > 0:
            box_title = "POSSIBILI MODULI CON ERRORI!!!\n\n"
            box_message = ""
            for i in range(len(module_broke)):
                box_message += (
                    f"{module_broke[i]}: controllare indici {index_broke[i]}\n"
                )
            message = box_title + box_message
            self.view.show_warning(message)


def on_closing() -> Messagebox:
    """Messagge box di conferma chiusura"""
    if Messagebox.yesno("Do you want to quit?", "Quit", bootstyle="success") == "Yes":
        master.destroy()
        master.quit()


if __name__ == "__main__":
    # add new themes if not present
    from utils import import_user_themes
    import_user_themes()
    # launch application
    master = DataAnalysis()
    master.place_window_center()
    master.protocol("WM_DELETE_WINDOW", on_closing)
    master.mainloop()
