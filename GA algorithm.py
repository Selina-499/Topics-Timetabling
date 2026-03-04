# -*- coding: utf-8 -*-
"""
Created on Tue Feb 24 16:42:50 2026

@author: Anja Ny Aina Harisoa
"""
import pandas as pd
import room_reallocation_ga
#importlib.reload(room_reallocation_ga)
from room_reallocation_ga import *
#Read processed data

#export_csv(Events_data, 'Event_data.csv')
#export_csv(Rooms_data, 'Rooms_data.csv')
#export_csv(Semester1_data, 'Semester1.csv')
#export_csv(Roomconstraintdata, 'Commute_duration.csv')

Events_data=pd.read_csv('Event_data.csv')
Rooms_data=pd.read_csv('Rooms_data.csv')
Semester1_data=pd.read_csv('Semester1.csv')
Roomconstraintdata=pd.read_csv('Commute_duration.csv')
Student_data=pd.read_csv('Student_data.csv')

# Run optimization
best_solution, best_fitness, events, rooms = run_ga(
    events_df=Events_data,
    rooms_df=Rooms_data,
    student_df=Student_data,
    travel_df=Roomconstraintdata,
    pop_size=150,
    ngen=100,
    seed=42
)

# Export results
results = export_assignment(
    best_solution,
    Events_data,
    rooms,
    events,
    out_csv='optimized_room_allocation.csv'
)

# Analyze results
analyze_results(results, events, rooms)