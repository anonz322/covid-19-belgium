#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  1 17:27:37 2020

@author: simonvdv
"""
import pandas as pd
#import numpy as np

from bokeh.models import ColumnDataSource, Column
from bokeh.models.tools import HoverTool
from bokeh.plotting import figure
from bokeh.io import show, output_file, output_notebook, curdoc
from bokeh.models.widgets import CheckboxGroup
from bokeh.layouts import row, WidgetBox
from bokeh.application.handlers import FunctionHandler
from bokeh.application import Application
from bokeh.server.server import Server
from bokeh.embed import server_document
from tornado.ioloop import IOLoop

import datetime as dt
import random

#Gather only used datas/other for eventual future uses:
cases = pd.read_csv("https://epistat.sciensano.be/Data/COVID19BE_CASES_AGESEX.csv", encoding="ISO-8859-1", index_col="DATE", parse_dates=True)
#muni = pd.read_csv("https://epistat.sciensano.be/Data/COVID19BE_CASES_MUNI.csv", encoding="ISO-8859-1", index_col="DATE", parse_dates=True)
#muni_cum = pd.read_csv("https://epistat.sciensano.be/Data/COVID19BE_CASES_MUNI_CUM.csv", encoding="ISO-8859-1")
hosp = pd.read_csv("https://epistat.sciensano.be/Data/COVID19BE_HOSP.csv", encoding="ISO-8859-1", index_col="DATE", parse_dates=True)
deaths = pd.read_csv("https://epistat.sciensano.be/Data/COVID19BE_MORT.csv", encoding="ISO-8859-1", index_col="DATE", parse_dates=True)
#tests = pd.read_csv("https://epistat.sciensano.be/Data/COVID19BE_tests.csv", encoding="ISO-8859-1", index_col="DATE", parse_dates=True)


tmp = pd.DataFrame(cases.groupby('DATE').sum()['CASES'])
df2 = deaths.groupby("DATE").sum().merge(hosp.groupby("DATE").sum(), on="DATE")
df2 = tmp.merge(df2, on="DATE", how='left').fillna(0).astype(int)
categories = list(df2.columns)

#easier to work with an un-tidy dataset in Bokeh
def make_dataset(list_cat):
    #only chosen cat
    df = df2[list_cat]
    plot_df = df.reset_index().melt(['DATE']).set_index('DATE').sort_index() #adios tidy data :/
    #new format as typical melted DF/"multi-index without being multiindexed" :
    #DATE  variable value
    #day-1 CASES     28
    #day-1 DEATHS    1
    #day-2 CASES (...)
    
    #random colors !FIX ME: nice colors
    col_gen = lambda : "#"+''.join([random.choice('0123456789ABCDEF') for j in range(6)])
    colors = {i:col_gen() for i in categories}
    plot_df["color"] = plot_df["variable"].map(colors)
    
    return ColumnDataSource(plot_df)


def make_plot(src):
    # create a new plot with a datetime axis type
    p = figure(plot_width=700, plot_height=700, x_axis_type="datetime")
    p.vbar(x='DATE', top='value', source = src, fill_alpha = 0.7,\
           hover_fill_alpha = 1.0, line_color = 'black', width=dt.timedelta(1), color='color', legend='variable')

    #define tooltips    
    p.add_tools(HoverTool(tooltips = [('Date', '@DATE{%F}'), ('', '@variable: @value')], formatters={'@DATE': 'datetime'}, point_policy="follow_mouse"))

    # attributes
    p.title.text = "Count"
    p.legend.location = "top_left"
    p.grid.grid_line_alpha = 0
    p.xaxis.axis_label = 'Date'
    p.yaxis.axis_label = 'Daily new cases'
    p.ygrid.band_fill_color = "olive"
    p.ygrid.band_fill_alpha = 0.1

    return p

def update(attr, old, new):
    #chosen cat
    cat_to_plot = [cat_selection.labels[i] for i in cat_selection.active]
    new_df = make_dataset(cat_to_plot)
    src.data.update(new_df.data)

cat_selection = CheckboxGroup(labels=categories, active=[0, 1])
cat_selection.on_change('active', update)

controls = Column(cat_selection)
init_cat = [cat_selection.labels[i] for i in cat_selection.active]


src = make_dataset(init_cat) 
p = make_plot(src)
layout = row(controls, p)
curdoc().add_root(layout)
