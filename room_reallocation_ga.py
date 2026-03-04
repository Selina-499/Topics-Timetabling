"""
Room Reallocation Optimization - Rebuilt for Your Data Structure
Genetic Algorithm for optimizing room assignments considering:
- Room capacity constraints
- Campus travel times
- Student timetable preferences
- Evening class penalties
- Room utilization
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any
import pandas as pd
import numpy as np
from deap import base, creator, tools, algorithms


# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================

DAY_TO_INT = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
}

# Penalty weights (adjust these to tune the optimization)
PENALTIES = {
    'hard_violation': 200_000,      # Capacity violation (hard constraint)
    'campus_move': 40,              # Reward for moving Holyrood to Central
    'not_central': 10,              # Penalty for Holyrood not going to Central
    'wed_fri_evening': 30,          # Penalty for Wednesday/Friday evening classes
    'long_duration': 2,             # Penalty per minute over max duration
    'max_duration': l,            # Maximum preferred duration (minutes)
    'commute_days': 8,              # Penalty per extra commute day for students
    'travel_minute': 1.0,           # Penalty per travel minute between events
    'impossible_travel': 50,        # Penalty for impossible travel between events
    'evening_start_hour': 16,       # Evening starts at 4 PM
}


# ============================================================================
# DATA PARSING AND VALIDATION
# ============================================================================

def parse_timeslot(timeslot: str) -> Tuple[int, int]:
    """
    Parse timeslot string into (day_index, start_minutes).
    Expected format: "Monday 09:00" or "Tuesday 14:30"
    
    Returns:
    --------
    day : int (0=Monday, 1=Tuesday, etc.)
    start_minutes : int (minutes from midnight)
    """
    try:
        parts = timeslot.strip().split()
        day_str = parts[0]
        time_str = parts[1]
        
        day = DAY_TO_INT.get(day_str)
        if day is None:
            raise ValueError(f"Invalid day: {day_str}")
        
        hour, minute = map(int, time_str.split(":"))
        start_minutes = hour * 60 + minute
        
        return day, start_minutes
    except Exception as e:
        print(f"⚠ Warning: Could not parse timeslot '{timeslot}': {e}")
        return 0, 540  # Default to Monday 9:00 AM


def is_evening(start: int, end: int, evening_start: int = None) -> bool:
    """Check if an event occurs in the evening."""
    if evening_start is None:
        evening_start = PENALTIES['evening_start_hour'] * 60
    return start >= evening_start or end > 17 * 60


def validate_data(events_df, rooms_df, student_df, travel_df):
    """
    Validate that all required columns exist and data types are correct.
    """
    print("\n" + "="*80)
    print("DATA VALIDATION")
    print("="*80)
    
    # Check Events data
    required_events_cols = ['Event ID', 'Event Size', 'Campus', 'Timeslot', 
                           'Duration (minutes)', 'Week List']
    missing = [col for col in required_events_cols if col not in events_df.columns]
    if missing:
        raise ValueError(f"Events data missing columns: {missing}")
    print(f"✓ Events data: {len(events_df)} events")
    
    # Check Rooms data
    required_rooms_cols = ['Id', 'Capacity', 'Campus']
    missing = [col for col in required_rooms_cols if col not in rooms_df.columns]
    if missing:
        raise ValueError(f"Rooms data missing columns: {missing}")
    print(f"✓ Rooms data: {len(rooms_df)} rooms")
    
    # Check Student data
    required_student_cols = ['AnonID', 'Event ID']
    missing = [col for col in required_student_cols if col not in student_df.columns]
    if missing:
        raise ValueError(f"Student data missing columns: {missing}")
    print(f"✓ Student data: {len(student_df)} enrollments")
    
    # Check Travel data
    required_travel_cols = ['Campus From', 'Campus To', 'Travel time (mins)']
    missing = [col for col in required_travel_cols if col not in travel_df.columns]
    if missing:
        raise ValueError(f"Travel data missing columns: {missing}")
    print(f"✓ Travel data: {len(travel_df)} campus pairs")
    
    # Check for null values in critical columns
    events_nulls = events_df[required_events_cols].isnull().sum()
    if events_nulls.any():
        print(f"\n⚠ Warning: Null values in Events data:")
        print(events_nulls[events_nulls > 0])
    
    rooms_nulls = rooms_df[required_rooms_cols].isnull().sum()
    if rooms_nulls.any():
        print(f"\n⚠ Warning: Null values in Rooms data:")
        print(rooms_nulls[rooms_nulls > 0])
    
    print("✓ Validation complete")


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass(frozen=True)
class Room:
    """Represents a room with its properties."""
    room_id: Any
    room_number: str
    campus: str
    capacity: int
    building: str
    room_type: str


@dataclass(frozen=True)
class Event:
    """Represents a teaching event with its requirements."""
    event_id: Any
    event_name: str
    size: int
    orig_campus: str
    orig_room: str
    orig_building: str
    day: int
    start: int
    end: int
    duration: int
    weeks: List[int]


# ============================================================================
# PROBLEM BUILDING
# ============================================================================

def build_problem(events_df, rooms_df, student_df, travel_df):
    """
    Build the optimization problem from your data.
    
    Parameters:
    -----------
    events_df : DataFrame with columns ['Event ID', 'Event Size', 'Campus', 
                'Timeslot', 'Duration (minutes)', 'Week List', 'Room', 'Building']
    rooms_df : DataFrame with columns ['Id', 'Room_Number', 'Capacity', 'Campus', 
               'Building_Name', 'Room_Type']
    student_df : DataFrame with columns ['AnonID', 'Event ID']
    travel_df : DataFrame with columns ['Campus From', 'Campus To', 'Travel time (mins)']
    
    Returns:
    --------
    events : List[Event]
    rooms : List[Room]
    student_events : Dict[student_id, List[event_index]]
    travel_time_fn : Function to get travel time between campuses
    """
    
    print("\n" + "="*80)
    print("BUILDING OPTIMIZATION PROBLEM")
    print("="*80)
    
    # Build rooms list
    rooms = []
    for _, row in rooms_df.iterrows():
        rooms.append(
            Room(
                room_id=row["Id"],
                room_number=str(row.get("Room_Number", "Unknown")),
                campus=str(row["Campus"]).strip(),
                capacity=int(row["Capacity"]),
                building=str(row.get("Building_Name", "Unknown")),
                room_type=str(row.get("Room_Type", "Unknown")),
            )
        )
    
    print(f"✓ Loaded {len(rooms)} rooms")
    
    # Build travel time matrix
    travel_matrix = {}
    for _, row in travel_df.iterrows():
        campus_from = str(row["Campus From"]).strip().lower()
        campus_to = str(row["Campus To"]).strip().lower()
        travel_time = int(row["Travel time (mins)"])
        travel_matrix[(campus_from, campus_to)] = travel_time
    
    def travel_time_fn(c1, c2):
        """Get travel time between two campuses."""
        key = (str(c1).strip().lower(), str(c2).strip().lower())
        return travel_matrix.get(key, 999)  # 999 = unreachable/unknown
    
    print(f"✓ Loaded travel times for {len(travel_matrix)} campus pairs")
    
    # Build events list
    events = []
    event_index = {}
    skipped = 0
    
    for idx, row in events_df.iterrows():
        try:
            # Parse timeslot
            day, start = parse_timeslot(str(row["Timeslot"]))
            
            # Get duration
            duration = int(row["Duration (minutes)"])
            end = start + duration
            
            # Get week list
            week_list = row.get("Week List", [])
            if isinstance(week_list, str):
                # If it's a string, try to parse it
                week_list = eval(week_list) if week_list.startswith('[') else []
            elif not isinstance(week_list, list):
                week_list = []
            
            # Get event size
            event_size = row.get("Event Size", 0)
            if pd.isna(event_size):
                event_size = 0
            else:
                event_size = int(float(event_size))
            
            ev = Event(
                event_id=row["Event ID"],
                event_name=str(row.get("Event Name", "Unknown")),
                size=event_size,
                orig_campus=str(row.get("Campus", "Unknown")).strip(),
                orig_room=str(row.get("Room", "Unknown")),
                orig_building=str(row.get("Building", "Unknown")),
                day=day,
                start=start,
                end=end,
                duration=duration,
                weeks=week_list,
            )
            
            event_index[row["Event ID"]] = len(events)
            events.append(ev)
            
        except Exception as e:
            skipped += 1
            if skipped <= 5:  # Only print first 5 errors
                print(f"⚠ Skipped event {row.get('Event ID', 'Unknown')}: {e}")
    
    print(f"✓ Loaded {len(events)} events")
    if skipped > 0:
        print(f"⚠ Skipped {skipped} events due to parsing errors")
    
    # Build student-event mapping
    student_events = defaultdict(list)
    matched = 0
    unmatched = 0
    
    for _, row in student_df.iterrows():
        event_id = row["Event ID"]
        if event_id in event_index:
            student_events[row["AnonID"]].append(event_index[event_id])
            matched += 1
        else:
            unmatched += 1
    
    print(f"✓ Loaded {len(student_events)} students")
    print(f"  - Matched enrollments: {matched:,}")
    if unmatched > 0:
        print(f"  - ⚠ Unmatched enrollments: {unmatched:,}")
    
    print("\nProblem Statistics:")
    print(f"  - Events to schedule: {len(events)}")
    print(f"  - Rooms available: {len(rooms)}")
    print(f"  - Students: {len(student_events)}")
    print(f"  - Average events per student: {len(student_df) / len(student_events):.1f}")
    
    # Campus distribution
    campus_dist = defaultdict(int)
    for ev in events:
        campus_dist[ev.orig_campus] += 1
    print(f"\nEvents by Campus:")
    for campus, count in sorted(campus_dist.items()):
        print(f"  - {campus}: {count}")
    
    return events, rooms, dict(student_events), travel_time_fn


# ============================================================================
# OBJECTIVE FUNCTION
# ============================================================================

def make_evaluator(events, rooms, student_events, travel_time_fn, penalties=None):
    """
    Create the objective function for the genetic algorithm.
    
    The function evaluates solutions based on:
    1. Hard constraints (room capacity)
    2. Campus movement preferences
    3. Evening class penalties
    4. Long duration penalties
    5. Student travel time
    6. Timetable conflicts
    
    Returns:
    --------
    evaluate : Function that takes an individual and returns fitness tuple
    """
    
    if penalties is None:
        penalties = PENALTIES
    
    P_HARD = penalties['hard_violation']
    W_MOVE = penalties['campus_move']
    P_NOT_CENTRAL = penalties['not_central']
    P_WED_FRI_EVENING = penalties['wed_fri_evening']
    P_LONG = penalties['long_duration']
    MAX_DURATION = penalties['max_duration']
    P_COMMUTE_DAY = penalties['commute_days']
    P_TRAVEL_MIN = penalties['travel_minute']
    P_IMPOSSIBLE = penalties['impossible_travel']
    
    def evaluate(individual):
        """
        Evaluate a solution (room assignment).
        
        Parameters:
        -----------
        individual : List[int]
            List where individual[i] = room index for event i
        
        Returns:
        --------
        fitness : tuple
            Single-element tuple with fitness score (higher is better)
        """
        
        hard_violations = 0
        soft_score = 0.0
        assigned_campus = []
        
        # 1. Check room capacity and campus preferences
        for event_idx, room_idx in enumerate(individual):
            ev = events[event_idx]
            rm = rooms[room_idx]
            
            assigned_campus.append(rm.campus)
            
            # Hard constraint: Room must fit all students
            if rm.capacity < ev.size:
                hard_violations += 1
            
            # Soft preference: Move Holyrood events to Central campus
            if ev.orig_campus.lower() == "holyrood":
                if rm.campus.lower() == "central":
                    soft_score += W_MOVE  # Reward
                else:
                    soft_score -= P_NOT_CENTRAL  # Penalty
            
            # Soft penalty: Avoid Wednesday/Friday evening classes
            if ev.day in (2, 4) and is_evening(ev.start, ev.end):
                soft_score -= P_WED_FRI_EVENING
            
            # Soft penalty: Avoid very long classes
            if ev.duration > MAX_DURATION:
                soft_score -= P_LONG * (ev.duration - MAX_DURATION)
        
        # 2. Check room conflicts (same room, same week, same day, overlapping time)
        room_schedule = defaultdict(list)
        for event_idx, room_idx in enumerate(individual):
            ev = events[event_idx]
            for week in ev.weeks:
                # Key: (room, week, day)
                room_schedule[(room_idx, week, ev.day)].append((ev.start, ev.end))
        
        # Check for overlaps
        for intervals in room_schedule.values():
            intervals.sort()  # Sort by start time
            for i in range(len(intervals) - 1):
                s1, e1 = intervals[i]
                s2, e2 = intervals[i + 1]
                if s2 < e1:  # Overlap detected
                    hard_violations += 1
        
        # 3. Check student timetable quality
        for student_id, event_indices in student_events.items():
            
            # Penalty for students commuting on multiple days
            days_used = {events[e].day for e in event_indices}
            if len(days_used) > 1:
                soft_score -= P_COMMUTE_DAY * (len(days_used) - 1)
            
            # Check travel time between consecutive events
            student_schedule = defaultdict(list)
            for event_idx in event_indices:
                ev = events[event_idx]
                for week in ev.weeks:
                    # Store: (week, day) -> [(start, end, event_idx)]
                    student_schedule[(week, ev.day)].append((ev.start, ev.end, event_idx))
            
            # For each day, check if student can travel between events
            for schedule_items in student_schedule.values():
                schedule_items.sort(key=lambda x: x[0])  # Sort by start time
                
                for i in range(len(schedule_items) - 1):
                    s1, e1, idx1 = schedule_items[i]
                    s2, e2, idx2 = schedule_items[i + 1]
                    
                    campus1 = assigned_campus[idx1]
                    campus2 = assigned_campus[idx2]
                    
                    travel_minutes = travel_time_fn(campus1, campus2)
                    gap_minutes = s2 - e1
                    
                    # Penalty for any travel time
                    soft_score -= P_TRAVEL_MIN * travel_minutes
                    
                    # Hard penalty if travel is impossible
                    if gap_minutes < travel_minutes:
                        soft_score -= P_IMPOSSIBLE
        
        # Combine hard and soft scores
        # Hard violations are heavily penalized to ensure feasibility
        total_score = soft_score - (P_HARD * hard_violations)
        
        return (total_score,)
    
    return evaluate


# ============================================================================
# INITIALIZATION STRATEGY
# ============================================================================

def make_greedy_initializer(events, rooms):
    """
    Create a greedy initialization function that tries to assign rooms smartly.
    
    Strategy:
    1. For each event, try to find a suitable room on the same campus
    2. If not available, try nearby campuses
    3. Prioritize capacity match
    
    Returns:
    --------
    init_function : Function that returns an initial solution
    """
    
    # Group rooms by campus
    rooms_by_campus = defaultdict(list)
    for idx, room in enumerate(rooms):
        rooms_by_campus[room.campus.lower()].append(idx)
    
    # Campus preference order (adjust based on your preferences)
    campus_fallback_order = ["central", "lauriston", "new college", "holyrood"]
    
    def init():
        """Generate one initial solution."""
        # Start with random assignment
        individual = [random.randrange(len(rooms)) for _ in events]
        
        # Try to improve with greedy heuristic
        for event_idx, event in enumerate(events):
            orig_campus = event.orig_campus.lower()
            
            # Try to find a suitable room
            # Priority 1: Same campus, adequate capacity
            for room_idx in rooms_by_campus.get(orig_campus, []):
                if rooms[room_idx].capacity >= event.size:
                    individual[event_idx] = room_idx
                    break
            else:
                # Priority 2: Fallback campuses
                for campus in campus_fallback_order:
                    if campus == orig_campus:
                        continue
                    for room_idx in rooms_by_campus.get(campus, []):
                        if rooms[room_idx].capacity >= event.size:
                            individual[event_idx] = room_idx
                            break
                    else:
                        continue
                    break
        
        return individual
    
    return init


# ============================================================================
# GENETIC ALGORITHM
# ============================================================================

def run_ga(events_df, rooms_df, student_df, travel_df,
           pop_size=150, ngen=100, seed=0, penalties=None):
    """
    Run the genetic algorithm optimization.
    
    Parameters:
    -----------
    events_df : DataFrame
        Events data
    rooms_df : DataFrame
        Rooms data
    student_df : DataFrame
        Student enrollment data
    travel_df : DataFrame
        Campus travel times
    pop_size : int
        Population size
    ngen : int
        Number of generations
    seed : int
        Random seed for reproducibility
    penalties : dict, optional
        Custom penalty weights
    
    Returns:
    --------
    best_solution : List[int]
        Best room assignment found
    best_fitness : float
        Fitness score of best solution
    events : List[Event]
        Event objects
    rooms : List[Room]
        Room objects
    """
    
    print("\n" + "="*80)
    print("GENETIC ALGORITHM OPTIMIZATION")
    print("="*80)
    
    # Validate data
    validate_data(events_df, rooms_df, student_df, travel_df)
    
    # Build problem
    events, rooms, student_events, travel_time_fn = build_problem(
        events_df, rooms_df, student_df, travel_df
    )
    
    if len(events) == 0:
        raise ValueError("No events to schedule!")
    
    if len(rooms) == 0:
        raise ValueError("No rooms available!")
    
    # Create evaluator
    evaluate = make_evaluator(events, rooms, student_events, travel_time_fn, penalties)
    
    # Set random seed
    random.seed(seed)
    
    # Setup DEAP
    if hasattr(creator, "FitnessMax"):
        del creator.FitnessMax
    if hasattr(creator, "Individual"):
        del creator.Individual
    
    creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMax)
    
    toolbox = base.Toolbox()
    
    # Register genetic operators
    greedy_init = make_greedy_initializer(events, rooms)
    toolbox.register("individual", tools.initIterate, creator.Individual, greedy_init)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("evaluate", evaluate)
    toolbox.register("select", tools.selTournament, tournsize=3)
    toolbox.register("mate", tools.cxTwoPoint)
    toolbox.register("mutate", tools.mutUniformInt, low=0, up=len(rooms)-1, indpb=0.05)
    
    # Create initial population
    print(f"\nInitializing population of {pop_size} solutions...")
    pop = toolbox.population(n=pop_size)
    
    # Hall of fame to track best solution
    hof = tools.HallOfFame(1)
    
    # Run evolution
    print(f"Evolving for {ngen} generations...")
    print("=" * 80)
    
    pop, log = algorithms.eaSimple(
        pop, toolbox,
        cxpb=0.7,  # Crossover probability
        mutpb=0.3,  # Mutation probability
        ngen=ngen,
        halloffame=hof,
        verbose=True
    )
    
    # Get best solution
    best = hof[0]
    best_fitness = best.fitness.values[0]
    
    print("\n" + "="*80)
    print("OPTIMIZATION COMPLETE")
    print("="*80)
    print(f"Best fitness: {best_fitness:,.2f}")
    
    return list(best), best_fitness, events, rooms


# ============================================================================
# RESULTS EXPORT
# ============================================================================

def export_assignment(best_solution, events_df, rooms, events,
                     out_csv="ga_room_allocation.csv"):
    """
    Export the room assignment results to CSV.
    
    Parameters:
    -----------
    best_solution : List[int]
        Best room assignment (room index for each event)
    events_df : DataFrame
        Original events dataframe
    rooms : List[Room]
        Room objects
    events : List[Event]
        Event objects
    out_csv : str
        Output filename
    
    Returns:
    --------
    results_df : DataFrame
        Results with assigned rooms
    """
    
    print("\n" + "="*80)
    print("EXPORTING RESULTS")
    print("="*80)
    
    # Build assignment lists
    assigned_room_id = []
    assigned_room_number = []
    assigned_campus = []
    assigned_building = []
    assigned_capacity = []
    assigned_room_type = []
    
    for room_idx in best_solution:
        room = rooms[room_idx]
        assigned_room_id.append(room.room_id)
        assigned_room_number.append(room.room_number)
        assigned_campus.append(room.campus)
        assigned_building.append(room.building)
        assigned_capacity.append(room.capacity)
        assigned_room_type.append(room.room_type)
    
    # Create output dataframe
    out = events_df.copy()
    out["Assigned_RoomID"] = assigned_room_id
    out["Assigned_Room_Number"] = assigned_room_number
    out["Assigned_Campus"] = assigned_campus
    out["Assigned_Building"] = assigned_building
    out["Assigned_Capacity"] = assigned_capacity
    out["Assigned_Room_Type"] = assigned_room_type
    
    # Flag campus changes
    out["Campus_Changed"] = (
        out["Campus"].astype(str).str.lower().str.strip()
        != out["Assigned_Campus"].astype(str).str.lower().str.strip()
    )
    
    # Calculate capacity utilization
    out["Capacity_Utilization"] = (
        out["Event Size"] / out["Assigned_Capacity"] * 100
    ).round(2)
    
    # Flag issues
    out["Overcapacity"] = out["Event Size"] > out["Assigned_Capacity"]
    
    # Export to CSV
    out.to_csv(out_csv, index=False)
    
    # Print summary
    print(f"✓ Exported results to: {out_csv}")
    print(f"\nSummary:")
    print(f"  - Total events: {len(out)}")
    print(f"  - Campus changes: {out['Campus_Changed'].sum()} ({out['Campus_Changed'].mean()*100:.1f}%)")
    print(f"  - Overcapacity events: {out['Overcapacity'].sum()}")
    print(f"  - Average utilization: {out['Capacity_Utilization'].mean():.1f}%")
    
    print(f"\nCampus Movement:")
    campus_changes = out[out['Campus_Changed']].groupby(['Campus', 'Assigned_Campus']).size()
    for (from_campus, to_campus), count in campus_changes.items():
        print(f"  - {from_campus} → {to_campus}: {count} events")
    
    return out


def analyze_results(results_df, events, rooms, student_events=None):
    """
    Detailed analysis of the optimization results.
    
    Parameters:
    -----------
    results_df : DataFrame
        Results from export_assignment()
    events : List[Event]
        Event objects
    rooms : List[Room]
        Room objects
    student_events : dict, optional
        Student-event mapping
    """
    
    print("\n" + "="*80)
    print("DETAILED RESULTS ANALYSIS")
    print("="*80)
    
    print("\n1. Room Capacity Analysis:")
    print(f"   - Min utilization: {results_df['Capacity_Utilization'].min():.1f}%")
    print(f"   - Max utilization: {results_df['Capacity_Utilization'].max():.1f}%")
    print(f"   - Average utilization: {results_df['Capacity_Utilization'].mean():.1f}%")
    print(f"   - Median utilization: {results_df['Capacity_Utilization'].median():.1f}%")
    
    # Utilization categories
    under_50 = (results_df['Capacity_Utilization'] < 50).sum()
    btw_50_80 = ((results_df['Capacity_Utilization'] >= 50) & 
                 (results_df['Capacity_Utilization'] <= 80)).sum()
    over_80 = ((results_df['Capacity_Utilization'] > 80) & 
               (results_df['Capacity_Utilization'] <= 100)).sum()
    over_100 = (results_df['Capacity_Utilization'] > 100).sum()
    
    print(f"\n   Utilization breakdown:")
    print(f"   - Under 50%: {under_50} events")
    print(f"   - 50-80% (optimal): {btw_50_80} events")
    print(f"   - 80-100%: {over_80} events")
    print(f"   - Over 100% (PROBLEM): {over_100} events")
    
    print("\n2. Campus Distribution:")
    campus_dist = results_df['Assigned_Campus'].value_counts()
    for campus, count in campus_dist.items():
        print(f"   - {campus}: {count} events ({count/len(results_df)*100:.1f}%)")
    
    print("\n3. Room Type Distribution:")
    room_type_dist = results_df['Assigned_Room_Type'].value_counts()
    for rtype, count in list(room_type_dist.items())[:10]:
        print(f"   - {rtype}: {count} events")
    
    if over_100 > 0:
        print("\n⚠ WARNING: Overcapacity Events:")
        overcap = results_df[results_df['Overcapacity']]
        for _, row in overcap.head(10).iterrows():
            print(f"   - {row['Event ID']}: {row['Event Size']} students in "
                  f"{row['Assigned_Capacity']} capacity room "
                  f"({row['Capacity_Utilization']:.0f}% utilization)")


# ============================================================================
# MAIN EXECUTION EXAMPLE
# ============================================================================

if __name__ == "__main__":
    print("""
    USAGE EXAMPLE:
    
    # Import your data
    # Events_data = FilteredEvents[...]
    # Rooms_data = Filtered_Rooms[...]
    # Student_data = Filtered_Students[...]
    # Roomconstraintdata = Roomconstraintdata[...]
    
    from room_reallocation_ga_v2 import *
    
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
    """)