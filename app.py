#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  1 17:27:37 2020

@author: simonvdv
"""
import pandas as pd
import numpy as np

from bokeh.models import ColumnDataSource, Column
from bokeh.models.tools import HoverTool
from bokeh.plotting import figure
from bokeh.io import show, output_file, output_notebook, curdoc
from bokeh.models.widgets import CheckboxGroup
from bokeh.layouts import row, WidgetBox, grid
from bokeh.application.handlers import FunctionHandler
from bokeh.application import Application
from bokeh.server.server import Server
from bokeh.embed import server_document
from bokeh.models import LinearAxis, Range1d

import datetime as dt
import random

#Gather only used datas/other for eventual future uses:
cases = pd.read_csv("https://epistat.sciensano.be/Data/COVID19BE_CASES_AGESEX.csv", encoding="ISO-8859-1", index_col="DATE", parse_dates=True)
#muni = pd.read_csv("https://epistat.sciensano.be/Data/COVID19BE_CASES_MUNI.csv", encoding="ISO-8859-1", index_col="DATE", parse_dates=True)
#muni_cum = pd.read_csv("https://epistat.sciensano.be/Data/COVID19BE_CASES_MUNI_CUM.csv", encoding="ISO-8859-1")
hosp = pd.read_csv("https://epistat.sciensano.be/Data/COVID19BE_HOSP.csv", encoding="ISO-8859-1", index_col="DATE", parse_dates=True)
deaths = pd.read_csv("https://epistat.sciensano.be/Data/COVID19BE_MORT.csv", encoding="ISO-8859-1", index_col="DATE", parse_dates=True)
#tests = pd.read_csv("https://epistat.sciensano.be/Data/COVID19BE_tests.csv", encoding="ISO-8859-1", index_col="DATE", parse_dates=True)

french = pd.read_csv("https://raw.githubusercontent.com/opencovid19-fr/data/master/data-sources/sante-publique-france/covid_hospit.csv",\
                     sep=";", index_col="jour", parse_dates=True)

tmp = pd.DataFrame(cases.groupby('DATE').sum()['CASES'])
df2 = deaths.groupby("DATE").sum().merge(hosp.groupby("DATE").sum(), on="DATE")
df2 = tmp.merge(df2, on="DATE", how='left').fillna(0).astype(int)
df2 = df2[['CASES', 'DEATHS', 'TOTAL_IN', 'TOTAL_IN_ICU', 'NEW_IN', 'NEW_OUT']]

bar_cat = ['CASES', 'DEATHS', 'TOTAL_IN', 'TOTAL_IN_ICU']
line_cat = ['NEW_IN', 'NEW_OUT']

df_line = df2[line_cat]

#easier to work with an un-tidy dataset in Bokeh
def make_dataset(list_cat):
    #only chosen cat

    plot_df_bar = df2[list_cat].reset_index().melt(['DATE']).set_index('DATE').sort_index() #adios tidy data :/

    #new format as typical melted DF/"multi-index without being multiindexed" :
    #DATE  variable value
    #day-1 CASES     28
    #day-1 DEATHS    1
    #day-2 CASES (...)
        
    colors = {'CASES':'grey', 'DEATHS':'darkgrey', 'TOTAL_IN':'orange', 'TOTAL_IN_ICU':'yellow'}
    
    plot_df_bar["color"] = plot_df_bar["variable"].map(colors)
    
    #for better visibility : order 
    
    plot_df_bar['variable'] = pd.Categorical(plot_df_bar['variable'],\
                        ['TOTAL_IN', 'CASES', 'TOTAL_IN_ICU','DEATHS'])
    plot_df_bar = plot_df_bar.sort_values(['variable'])
    

    
    return ColumnDataSource(plot_df_bar)


def make_plot(src_bar):
  
    # create a new plot with a datetime axis type
    p = figure(plot_width=700, plot_height=700, x_axis_type="datetime", title = "Belgique")
        
    p.vbar(x='DATE', top='value', source = src_bar, fill_alpha = 1,\
           hover_fill_alpha = 1.0, line_color = 'black', width=dt.timedelta(1), \
               color='color', legend='variable', name="vbars")

    
    colors = {'NEW_IN':'red', 'NEW_OUT':'green'}
    names = df_line.columns
    for i in names:
        p.line(x=df_line.index, y=df_line[i], legend_label=i, line_width=4, color=colors[i], name=i)
        


    #define tooltips    
    p.add_tools(HoverTool(tooltips = [('Date', '@DATE{%F}'), ('', '@variable: @value')],\
                          formatters={'@DATE': 'datetime'}, point_policy="follow_mouse", mode="vline", names=["vbars"]))
        
    p.add_tools(HoverTool(tooltips = [('', '$name: @value')],\
                          point_policy="follow_mouse", mode="vline", names=list(names)))

    # attributes
    p.legend.location = "top_left"
    p.grid.grid_line_alpha = 0
    p.xaxis.axis_label = 'Date'
    p.yaxis.axis_label = 'Value'
    p.ygrid.band_fill_color = "olive"
    p.ygrid.band_fill_alpha = 0.1
    
    return p

def update(attr, old, new):
    #chosen cat
    cat_to_plot = [cat_selection.labels[i] for i in cat_selection.active]
    new_bar = make_dataset(cat_to_plot)
    src_bar.data.update(new_bar.data)


cat_selection = CheckboxGroup(labels=bar_cat, active=[1, 2, 3])
cat_selection.on_change('active', update)

init_cat = [cat_selection.labels[i] for i in cat_selection.active]

src_bar = make_dataset(init_cat) 
p = make_plot(src_bar)

df2_cross_french = df2.merge(french[['hosp', 'rea', 'dc']].groupby('jour').sum().reset_index().set_index('jour'), left_index=True, right_index=True, how='left').fillna(0).astype(int)

def make_plot_compare(cat):
    colors = {'hosp':'blue', 'rea':'blue', 'dc':'blue', 'TOTAL_IN':'red', 'TOTAL_IN_ICU':'red', 'DEATHS':'red'}
    f = figure(plot_width=400, plot_height=400, x_axis_type="datetime", title = "France (blue) vs Belgium (red) : {}".format(cat))
    plot_df_bar = df2_cross_french[cat].reset_index().melt(['DATE']).set_index('DATE').sort_index()
    plot_df_bar["color"] = plot_df_bar["variable"].map(colors)
    
    
    plot_CDS_be = ColumnDataSource(plot_df_bar[plot_df_bar["color"]=='red'])
    plot_CDS_fr = ColumnDataSource(plot_df_bar[plot_df_bar["color"]=='blue'])
            
    if 'hosp' in cat:
        f.extra_y_ranges = {"france": Range1d(start=0, end=60000),
                           "belgium": Range1d(start=0, end=6000)}
    else:
        f.extra_y_ranges = {"france": Range1d(start=0, end=15000), 
                           "belgium": Range1d(start=0, end=1500)}
        
    f.add_layout(LinearAxis(y_range_name="belgium", axis_label="belgium", axis_line_color='red', axis_label_text_color='red'), 'left')
    f.add_layout(LinearAxis(y_range_name="france", axis_label="France", axis_line_color='blue', axis_label_text_color='blue'), 'right')        
    
    f.vbar(x='DATE', top='value', source = plot_CDS_be, fill_alpha = 0.7,\
       width=dt.timedelta(1), \
       line_color='black', color='color', legend_label='Be')
        
    f.vbar(x='DATE', top='value', source = plot_CDS_fr, fill_alpha = 0.7,\
       width=dt.timedelta(1), \
       line_color='black', color='color', y_range_name='france', legend_label='Fr')
        
    f.grid.grid_line_alpha = 0
    f.xaxis.axis_label = 'Date'
    f.ygrid.band_fill_color = "olive"
    f.ygrid.band_fill_alpha = 0.1
    
    return f



total = make_plot_compare(['hosp', 'TOTAL_IN'])

icu = make_plot_compare(['rea', 'TOTAL_IN_ICU'])

#deaths = make_plot_compare(['dc', 'DEATHS'])



layout = grid([[cat_selection], [p], [total, icu]])


curdoc().add_root(layout)
