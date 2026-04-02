import pandas as pd
import numpy as np
from collections import defaultdict
import time

class EnhancedHolyroodHeuristic:
    """Enhanced realistic heuristic: Hard no-overlap + Utilization cap + Strong Central priority"""
    
    def __init__(self):
        self.days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        self.time_slots = [f"{h:02d}:{m:02d}" for h in range(9, 19) for m in [0, 30]]
        
        self.events = []
        self.weeks = []
        self.rooms = []                    # Non-Holyrood only
        self.holyrood_events = set()
        
        self.event_name = {}
        self.event_size = {}
        self.event_duration = {}           # 30-min blocks
        self.event_weeks = {}
        self.event_original_room = {}
        self.event_original_campus = {}
        self.room_capacity = {}
        self.room_campus = {}
        
        self.conflicts = defaultdict(set)
        self.travel_matrix = {}
        
        self.assignment = defaultdict(list)
        
        print("✓ Enhanced heuristic with hard no-overlap and utilization control")

    def load_data(self, max_events=5000):
        print(f"📊 Loading data ({max_events} events)...")
        events_df = pd.read_csv('Event_data.csv')
        rooms_df = pd.read_csv('Rooms_data.csv')
        semester_df = pd.read_csv('Semester1.csv')
        students_df = pd.read_csv('Student_data.csv')
        travel_df = pd.read_csv('Travel_Times.csv')

        self.weeks = sorted([int(w) for w in semester_df['Week Number'].dropna().unique()])

        def parse_weeks(ws):
            if pd.isna(ws): return self.weeks
            s = set()
            for p in str(ws).split(','):
                p = p.strip()
                if '-' in p:
                    a, b = map(int, p.split('-'))
                    s.update(range(a, b+1))
                else:
                    s.add(int(p))
            return sorted([w for w in s if w in self.weeks])

        self.events = events_df['Event ID'].unique()[:max_events].tolist()
        for e in self.events:
            row = events_df[events_df['Event ID'] == e].iloc[0]
            self.event_name[e] = row.get('Event Name', 'Unknown')
            self.event_size[e] = int(row.get('Event Size', 0)) if pd.notna(row.get('Event Size')) else 0
            dur = float(row.get('Duration (minutes)', 60))
            self.event_duration[e] = max(1, int(np.ceil(dur / 30)))
            self.event_weeks[e] = parse_weeks(row.get('Weeks'))
            self.event_original_room[e] = row.get('Room')
            self.event_original_campus[e] = row.get('Campus', 'Central')
            if self.event_original_campus[e] == 'Holyrood':
                self.holyrood_events.add(e)

        for _, row in rooms_df.iterrows():
            if row.get('Campus') == 'Holyrood': continue
            r = row['Id']
            self.rooms.append(r)
            self.room_capacity[r] = int(row.get('Capacity', 0))
            self.room_campus[r] = row.get('Campus', 'Central')

        # Student conflicts
        student_events = students_df.groupby('AnonID')['Event ID'].apply(set).to_dict()
        for ev_set in student_events.values():
            relevant = [e for e in ev_set if e in self.events]
            for i in range(len(relevant)):
                for j in range(i+1, len(relevant)):
                    a, b = relevant[i], relevant[j]
                    self.conflicts[a].add(b)
                    self.conflicts[b].add(a)

        # Travel
        for _, row in travel_df.iterrows():
            c1, c2 = row['Campus From'], row['Campus To']
            gap = int(np.ceil(row['Travel time (mins)'] / 30))
            self.travel_matrix[(c1, c2)] = gap
            self.travel_matrix[(c2, c1)] = gap

        print(f"✅ Loaded {len(self.events)} events, {len(self.rooms)} rooms")

    def solve(self):
        print("🚀 Running enhanced heuristic with hard constraints...")
        start = time.time()
        
        # Most constrained first
        difficulty = {}
        for e in self.events:
            conf = len(self.conflicts[e])
            size_f = self.event_size.get(e, 50)
            dur_f = self.event_duration[e]
            week_f = len(self.event_weeks.get(e, []))
            holy_bonus = 25 if e in self.holyrood_events else 1
            difficulty[e] = conf * size_f * dur_f * week_f * holy_bonus
        
        event_order = sorted(self.events, key=lambda e: difficulty[e], reverse=True)
        
        self.assignment = defaultdict(list)
        occupied = defaultdict(bool)   # (week, day, slot_idx, room)
        
        for e in event_order:
            weeks = self.event_weeks.get(e, self.weeks)
            best_score = float('inf')
            best_choice = None
            
            for day_idx, day in enumerate(self.days):
                for s_idx in range(len(self.time_slots) - self.event_duration[e] + 1):
                    t_str = self.time_slots[s_idx]
                    is_lecture = any(w in str(self.event_name.get(e,"")).lower() for w in ["lecture", "whole class"])
                    wed_penalty = 200 if day == 'Wednesday' and t_str >= "13:00" and is_lecture else 0
                    
                    for r in self.rooms:
                        camp = self.room_campus[r]
                        cap = self.room_capacity.get(r, 0)
                        size = self.event_size.get(e, 0)
                        
                        # Strong Central priority
                        camp_penalty = 0 if camp == 'Central' else (30 if camp == 'Lauriston' else 50)
                        reloc_penalty = 50 if e in self.holyrood_events else 10
                        cap_penalty = 600 if size > cap else (200 if size > 0.9*cap else 0)
                        
                        total_score = wed_penalty + camp_penalty + reloc_penalty + cap_penalty
                        
                        # HARD NO-OVERLAP + DURATION CHECK
                        feasible = True
                        dur = self.event_duration[e]
                        for w in weeks:
                            for k in range(dur):
                                if occupied[(w, day, s_idx + k, r)]:
                                    feasible = False
                                    break
                            if not feasible: break
                        
                        # Student clash + travel gap
                        if feasible:
                            for other in self.conflicts[e]:
                                if other not in self.assignment: continue
                                for ow, od, os_idx, oroom in self.assignment[other]:
                                    if ow in weeks and od == day:
                                        o_dur = self.event_duration[other]
                                        if max(s_idx, os_idx) < min(s_idx + dur, os_idx + o_dur):
                                            feasible = False
                                            break
                                    # Travel gap
                                    if feasible and ow in weeks and od == day:
                                        gap = self.travel_matrix.get((camp, self.room_campus[oroom]), 0)
                                        if gap > 0 and abs(s_idx - os_idx) < dur + gap:
                                            feasible = False
                                            break
                        
                        if feasible and total_score < best_score:
                            best_score = total_score
                            best_choice = (day, s_idx, r)
            
            if best_choice:
                day, s_idx, r = best_choice
                dur = self.event_duration[e]
                for w in weeks:
                    for k in range(dur):
                        slot = s_idx + k
                        self.assignment[e].append((w, day, slot, r))
                        occupied[(w, day, slot, r)] = True
            else:
                print(f"⚠️ Could not assign {e}")
        
        print(f"✅ Enhanced timetable generated in {time.time() - start:.1f} seconds")

    def save_outputs(self):
        print("📤 Saving improved outputs...")
        
        rows = []
        for e, slots in self.assignment.items():
            for w, day, slot_idx, r in slots:
                if slot_idx >= len(self.time_slots): continue
                t = self.time_slots[slot_idx]
                size = self.event_size.get(e, 0)
                cap = self.room_capacity.get(r, 1)
                rows.append({
                    'Week': w,
                    'Day': day,
                    'Time': t,
                    'Event_ID': e,
                    'Event_Name': self.event_name.get(e),
                    'Room': r,
                    'Campus': self.room_campus[r],
                    'Orig_Campus': self.event_original_campus.get(e),
                    'From_Holyrood': self.event_original_campus.get(e) == 'Holyrood',
                    'Size': size,
                    'Room_Capacity': cap,
                    'Util_%': round(size / cap * 100, 1) if cap > 0 else 0
                })
        
        timetable_df = pd.DataFrame(rows)
        timetable_df = timetable_df.sort_values(['Week', 'Day', 'Time'])
        timetable_df.to_csv('timetable_enhanced.csv', index=False)
        
        # Utilization table
        room_usage = defaultdict(lambda: {'events': 0, 'capacity': 0, 'campus': ''})
        for e, slots in self.assignment.items():
            for _, _, _, r in slots:
                room_usage[r]['events'] += 1
                room_usage[r]['capacity'] = self.room_capacity.get(r, 0)
                room_usage[r]['campus'] = self.room_campus[r]
        
        util_rows = []
        for r, data in room_usage.items():
            util_rows.append({
                'Room': r,
                'Campus': data['campus'],
                'Capacity': data['capacity'],
                'Events_Assigned': data['events'],
                'Utilization_%': round(data['events'] / max(1, len(self.time_slots)) * 100, 1)
            })
        
        util_df = pd.DataFrame(util_rows)
        util_df = util_df.sort_values(['Campus', 'Utilization_%'], ascending=[True, False])
        util_df.to_csv('room_table_enhanced.csv', index=False)
        
        # Summary
        print("\n" + "="*85)
        print("ENHANCED HOLYROOD CLOSURE SUMMARY (with hard no-overlap)")
        print("="*85)
        print(f"Total events scheduled     : {len(timetable_df)}")
        holy_moved = timetable_df[timetable_df['From_Holyrood'] == True]
        print(f"Holyrood events moved      : {len(holy_moved)}")
        if not holy_moved.empty:
            central = len(holy_moved[holy_moved['Campus']=='Central'])
            laur = len(holy_moved[holy_moved['Campus']=='Lauriston'])
            newc = len(holy_moved[holy_moved['Campus']=='New College'])
            print(f"   → Central               : {central} ({central/len(holy_moved)*100:.1f}%)")
            print(f"   → Lauriston             : {laur}")
            print(f"   → New College           : {newc}")
        
        print("\n=== ROOM UTILIZATION TABLE (Top 10) ===")
        print(util_df.head(10).to_string(index=False))
        
        print("\n✅ Files saved:")
        print("   holyrood_closure_timetable_enhanced.csv")
        print("   room_utilization_enhanced.csv")

# ====================== RUN ======================
if __name__ == "__main__":
    model = EnhancedHolyroodHeuristic()
    model.load_data(max_events=5000)      # You can increase this
    model.solve()
    model.save_outputs()
