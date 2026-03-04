import xpress as xp
import pandas as pd
import numpy as np
from datetime import datetime

class TimetablingModel:
    """University timetabling model using Xpress solver."""
    
    def __init__(self, students_df, events_df, weeks_df, rooms_df):
        self.students_df = students_df
        self.events_df = events_df
        self.weeks_df = weeks_df
        self.rooms_df = rooms_df
        
        self.model = xp.problem(name="Timetabling")
        
        # Data structures
        self.events = []
        self.days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        self.time_slots = self._generate_time_slots()
        self.weeks = []
        self.rooms = []
        
        # Parameters
        self.event_size = {}
        self.event_duration = {}
        self.event_weeks = {}
        self.event_name = {}
        self.room_capacity = {}
        self.room_campus = {}
        self.room_building = {}
        self.curricula = {}
        
        # Decision variables
        self.x = {}
        self.v = {}
        
        print("✓ Model initialized")
    
    def _generate_time_slots(self):
        """Generate 30-min slots from 09:00 to 18:00."""
        slots = []
        for hour in range(9, 18):
            for minute in [0, 30]:
                slots.append(f"{hour:02d}:{minute:02d}")
        return slots
    
    def build_data(self, max_events=50, max_rooms=20):
        """Build sets and parameters with robust fallbacks."""
        print("\nBuilding data structures...")
        
        # 1. Build Weeks from Semester1_data
        # Columns: Week Number, Date Commencing, Week Label, Week Type, Date Ending, Academic Year
        teaching_weeks_df = self.weeks_df[self.weeks_df['Week Type'] == 'Other']
        if teaching_weeks_df.empty:
            print("  ! Warning: No 'Teaching Week' found. Using all available unique weeks.")
            teaching_weeks = self.weeks_df['Week Number'].unique()
        else:
            teaching_weeks = teaching_weeks_df['Week Number'].unique()
            
        self.weeks = sorted([int(w) for w in teaching_weeks if pd.notna(w)])[:4]  # Limit to 4 weeks for testing
        print(f"  Weeks: {len(self.weeks)} ({self.weeks})")

        # 2. Build Events from Events_data
        # Columns: Event ID, Event Name, Event Size, Campus, Number of Weeks, 
        #          Weeks, Week List, Room, Building, Timeslot, Duration (minutes)
        self.events = self.events_df['Event ID'].unique()[:max_events].tolist()
        
        for e in self.events:
            event_row = self.events_df[self.events_df['Event ID'] == e].iloc[0]
            
            # Event Size
            self.event_size[e] = event_row.get('Event Size', 0)
            if pd.isna(self.event_size[e]):
                self.event_size[e] = 0
            else:
                self.event_size[e] = int(self.event_size[e])
            
            # Event Name
            self.event_name[e] = event_row.get('Event Name', 'Unknown')
            
            # Duration (convert minutes to 30-min slots)
            dur = event_row.get('Duration (minutes)', 60)
            if pd.isna(dur):
                dur = 60
            self.event_duration[e] = max(1, int(np.ceil(float(dur) / 30)))
            
            # Week List - parse from the 'Week List' column
            weeks = event_row.get('Week List', [])
            if isinstance(weeks, list) and len(weeks) > 0:
                # Already a list
                self.event_weeks[e] = [w for w in weeks if w in self.weeks]
            elif isinstance(weeks, str):
                # Parse string like "[1, 2, 3, 4, 5]" or "1,2,3,4,5"
                try:
                    # Try to parse as list literal
                    import ast
                    weeks_parsed = ast.literal_eval(weeks)
                    if isinstance(weeks_parsed, list):
                        self.event_weeks[e] = [w for w in weeks_parsed if w in self.weeks]
                    else:
                        self.event_weeks[e] = self.weeks[:1]  # Default to first week
                except:
                    # Try comma-separated
                    try:
                        weeks_parsed = [int(w.strip()) for w in weeks.split(',')]
                        self.event_weeks[e] = [w for w in weeks_parsed if w in self.weeks]
                    except:
                        self.event_weeks[e] = self.weeks[:1]
            else:
                # Default: assign to all available weeks
                self.event_weeks[e] = self.weeks
            
            # Ensure at least one week
            if len(self.event_weeks[e]) == 0:
                self.event_weeks[e] = self.weeks[:1]
        
        print(f"  Events: {len(self.events)}")
        print(f"    - Average event size: {np.mean(list(self.event_size.values())):.1f}")
        print(f"    - Average duration: {np.mean(list(self.event_duration.values())):.1f} slots")
        
        # 3. Build Rooms from Rooms_data
        # Columns: Id, Room_Number, Room_Type, Capacity, Campus, 
        #          Building_Code, Building_Name, Capacity_Category
        room_count = 0
        for _, row in self.rooms_df.iterrows():
            if room_count >= max_rooms: 
                break
            
            room_id = row['Id']
            campus = row.get('Campus', 'Central')
            
            # Skip Holyrood rooms
            if campus == 'Holyrood':
                continue
            
            self.rooms.append(room_id)
            
            # Capacity
            capacity = row.get('Capacity', 0)
            if pd.isna(capacity):
                capacity = 0
            self.room_capacity[room_id] = int(capacity)
            
            # Campus
            self.room_campus[room_id] = campus
            
            # Building
            self.room_building[room_id] = row.get('Building_Name', 'Unknown')
            
            room_count += 1
        
        print(f"  Rooms: {len(self.rooms)} (excluding Holyrood)")
        
        # Campus distribution
        campus_counts = {}
        for r in self.rooms:
            c = self.room_campus.get(r, 'Unknown')
            campus_counts[c] = campus_counts.get(c, 0) + 1
        print(f"    - Campus distribution: {campus_counts}")

        # 4. Build Curricula from Student_data
        # Columns: AnonID, Department, Programme, Event ID, Course Name
        student_events = self.students_df.groupby('AnonID')['Event ID'].apply(set).to_dict()
        
        c_id = 0
        for student_id, events in list(student_events.items())[:5000]:  # Limit to 500 curricula
            relevant_events = [e for e in events if e in self.events]
            if len(relevant_events) > 1:
                self.curricula[c_id] = relevant_events
                c_id += 1
        
        print(f"  Curricula: {len(self.curricula)}")
        if len(self.curricula) > 0:
            avg_size = np.mean([len(c) for c in self.curricula.values()])
            print(f"    - Average curriculum size: {avg_size:.1f} events")
        
        print("✓ Data structures built\n")

    def build_model(self):
        """Build the MIP model."""
        print("Building MIP model...")
        self._create_variables()
        self._create_objective()
        self._add_constraints()
        print(f"✓ Model built: {self.model.attributes.cols} vars, {self.model.attributes.rows} constraints\n")

    def _create_variables(self):
        """Create binary decision variables x and violation variables v."""
        print("  Creating variables...")
        
        var_count = 0
        for e in self.events:
            for w in self.event_weeks.get(e, self.weeks[:1]):
                if w not in self.weeks:
                    continue
                for d in self.days:
                    for t in self.time_slots:
                        for r in self.rooms:
                            self.x[e, d, t, r, w] = xp.var(vartype=xp.binary)
                            self.v[e, d, t, r, w] = xp.var(lb=0)
                            var_count += 1
        
        self.model.addVariable(list(self.x.values()) + list(self.v.values()))
        print(f"    ✓ Created {len(self.x)} x variables, {len(self.v)} v variables")

    def _create_objective(self):
        """Objective: Minimize room size violations and prefer Central campus."""
        print("  Creating objective...")
        
        obj_terms = []
        
        # Capacity violation penalty (high weight)
        for v_var in self.v.values():
            obj_terms.append(100 * v_var)
        
        # Campus preference penalty
        for (e, d, t, r, w), x_var in self.x.items():
            campus = self.room_campus.get(r, 'Central')
            if campus == 'Lauriston':
                obj_terms.append(10 * x_var)
            elif campus == 'New College':
                obj_terms.append(20 * x_var)
            # Central has 0 penalty (most preferred)
        
        self.model.setObjective(xp.Sum(obj_terms), sense=xp.minimize)
        print(f"    ✓ Objective created with {len(obj_terms)} terms")

    def _add_constraints(self):
        """Add scheduling constraints."""
        print("  Adding constraints...")
        
        constraint_count = 0
        
        # 1. Each event scheduled exactly once per week
        for e in self.events:
            for w in self.event_weeks.get(e, self.weeks[:1]):
                if w not in self.weeks:
                    continue
                
                vars_for_event = []
                for d in self.days:
                    for t in self.time_slots:
                        for r in self.rooms:
                            if (e, d, t, r, w) in self.x:
                                vars_for_event.append(self.x[e, d, t, r, w])
                
                if vars_for_event:
                    self.model.addConstraint(xp.Sum(vars_for_event) == 1)
                    constraint_count += 1
        
        print(f"    ✓ Added {constraint_count} event completeness constraints")
        
        # 2. Room uniqueness (one event per room per time slot)
        room_constraints = 0
        for r in self.rooms:
            for w in self.weeks:
                for d in self.days:
                    for t in self.time_slots:
                        vars_at_time = []
                        for e in self.events:
                            if (e, d, t, r, w) in self.x:
                                vars_at_time.append(self.x[e, d, t, r, w])
                        
                        if vars_at_time:
                            self.model.addConstraint(xp.Sum(vars_at_time) <= 1)
                            room_constraints += 1
        
        print(f"    ✓ Added {room_constraints} room uniqueness constraints")
        
        # 3. Curriculum clash prevention (simplified)
        clash_constraints = 0
        for c_id, events in self.curricula.items():
            for w in self.weeks:
                for d in self.days:
                    for t in self.time_slots:
                        vars_in_curriculum = []
                        for e in events:
                            if e not in self.events:
                                continue
                            for r in self.rooms:
                                if (e, d, t, r, w) in self.x:
                                    vars_in_curriculum.append(self.x[e, d, t, r, w])
                        
                        if vars_in_curriculum:
                            self.model.addConstraint(xp.Sum(vars_in_curriculum) <= 1)
                            clash_constraints += 1
        
        print(f"    ✓ Added {clash_constraints} curriculum clash constraints")
        
        # 4. Capacity violation logic
        capacity_constraints = 0
        for (e, d, t, r, w), x_var in self.x.items():
            size = self.event_size.get(e, 0)
            cap = self.room_capacity.get(r, 1)
            v_var = self.v[e, d, t, r, w]
            
            # Underfill penalty: v >= (0.5 * cap - size) * x
            self.model.addConstraint(v_var >= (0.5 * cap - size) * x_var)
            
            # Overfill penalty: v >= (size - cap) * x
            self.model.addConstraint(v_var >= (size - cap) * x_var)
            
            capacity_constraints += 2
        
        print(f"    ✓ Added {capacity_constraints} capacity constraints")

    def solve(self, time_limit=600):
        """Solve using Xpress."""
        print(f"Solving (time limit: {time_limit}s)...")
        
        # Set solver parameters
        self.model.controls.maxtime = -time_limit  # Negative for time limit in seconds
        self.model.controls.miprelstop = 0.05  # 5% optimality gap
        self.model.controls.outputlog = 1  # Show solver output
        
        start_time = datetime.now()
        self.model.solve()
        solve_time = (datetime.now() - start_time).total_seconds()
        
        # Check solution status
        status = self.model.attributes.solstatus
        
        print(f"\nSolution status: {status}")
        print(f"Solve time: {solve_time:.1f}s")
        
        if status in [xp.SolStatus.FEASIBLE, xp.SolStatus.OPTIMAL]:
            obj_val = self.model.attributes.objval
            print(f"✓ Solution found! Objective value: {obj_val:.2f}")
            
            if status == xp.SolStatus.OPTIMAL:
                print("  (Optimal solution)")
            else:
                print("  (Feasible solution - may not be optimal)")
            
            return True
        else:
            print(f"✗ No solution found. Status: {status}")
            return False

    def extract_solution(self):
        """Extract solution to a clean DataFrame."""
        print("\nExtracting solution...")
        
        results = []
        for (e, d, t, r, w), var in self.x.items():
            if self.model.getSolution(var) > 0.5:  # Binary variable is 1
                results.append({
                    'Event_ID': e,
                    'Event_Name': self.event_name.get(e, 'Unknown'),
                    'Week': w,
                    'Day': d,
                    'Time': t,
                    'Room_ID': r,
                    'Room_Building': self.room_building.get(r, 'Unknown'),
                    'Campus': self.room_campus.get(r, 'Unknown'),
                    'Event_Size': self.event_size.get(e, 0),
                    'Room_Capacity': self.room_capacity.get(r, 0)
                })
        
        df = pd.DataFrame(results)
        
        if len(df) > 0:
            # Sort by week, day, time
            day_order = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4}
            df['Day_Order'] = df['Day'].map(day_order)
            df = df.sort_values(['Week', 'Day_Order', 'Time']).drop('Day_Order', axis=1)
            
            print(f"✓ Extracted {len(df)} scheduled events")
            print(f"\nCampus distribution:")
            print(df['Campus'].value_counts())
        else:
            print("⚠ No events scheduled")
        
        return df


def run_model(students, events, weeks, rooms, max_events=50, max_rooms=20, time_limit=900):
    """Main execution function."""
    print("="*60)
    print("UNIVERSITY TIMETABLING OPTIMIZATION")
    print("="*60)
    
    model = TimetablingModel(students, events, weeks, rooms)
    model.build_data(max_events=max_events, max_rooms=max_rooms)
    model.build_model()
    
    success = model.solve(time_limit=time_limit)
    
    if success:
        schedule_df = model.extract_solution()
        
        # Save to file
        output_path = '/mnt/user-data/outputs/final_schedule.csv'
        schedule_df.to_csv(output_path, index=False)
        print(f"\n✓ Schedule saved to: {output_path}")
        
        return schedule_df
    else:
        return success


if __name__ == "__main__":
    print("Timetabling Model ")
    print("\nExpected column names:")
    print("  Events_data: Event ID, Event Name, Event Size, Campus, Weeks, Week List, Duration (minutes)")
    print("  Rooms_data: Id, Room_Number, Room_Type, Capacity, Campus, Building_Name")
    print("  Semester1_data: Week Number, Week Label, Week Type")
    print("  Student_data: AnonID, Event ID")
    # Load data
    Events_data = pd.read_csv('Event_data.csv')
    Rooms_data = pd.read_csv('Rooms_data.csv')
    Semester1_data = pd.read_csv('Semester1.csv')
    Student_data = pd.read_csv('Student_data.csv')
    schedule = run_model(Student_data, Events_data, Semester1_data, Rooms_data)
    schedule.to_csv('my_schedule.csv', index=False)