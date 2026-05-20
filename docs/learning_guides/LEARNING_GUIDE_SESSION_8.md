# Learning Guide Session 8: Building an Interactive Calendar & Appointment Scheduling System

**Session Focus:** Database Schema Design • RESTful API Development • Calendar UI Integration • DateTime Handling • Data Serialization • Interactive Forms

**What We Built:** A complete appointment scheduling system with calendar visualization, enabling managers to schedule visits to apartments and view all scheduled activities on specific dates.

---

## Table of Contents
1. [Session Overview](#session-overview)
2. [Understanding the Problem](#understanding-the-problem)
3. [Database Schema Design](#database-schema-design)
4. [Backend API Development](#backend-api-development)
5. [Frontend Calendar Integration](#frontend-calendar-integration)
6. [Interactive Appointment Creation](#interactive-appointment-creation)
7. [Debugging DateTime Serialization](#debugging-datetime-serialization)
8. [Merging Multiple Data Sources](#merging-multiple-data-sources)
9. [Common Pitfalls & Solutions](#common-pitfalls--solutions)
10. [Complete Code Examples](#complete-code-examples)
11. [Testing & Verification](#testing--verification)

---

## Session Overview

### The Challenge
Build a calendar system where managers can:
1. **View** scheduled visits on a calendar (dates with appointments show blue dots)
2. **Click** any date to see all scheduled activities
3. **Create** new appointments for future dates
4. **Validate** apartment numbers before scheduling

### The Constraints
- ✅ Calendar must show BOTH complaints (with appointment_date) AND standalone appointments
- ✅ Only valid flat numbers can be scheduled
- ✅ DateTime must be stored correctly in UTC format
- ✅ Frontend must auto-refresh after creating appointments
- ✅ Must handle past and future dates differently

### What We Accomplished
- **New Database Table:** `appointments` with proper constraints
- **New Database Column:** `appointment_date` added to `complaints` table
- **4 New API Endpoints:** Create, Read, Update, Cancel appointments
- **Enhanced Calendar Widget:** Shows merged data from two sources
- **Interactive Form:** Validates flats, selects time, auto-refreshes
- **Proper Serialization:** DateTime and Enum handling fixed

---

## Understanding the Problem

### The User Story

**As a property manager:**
- I need to see which apartments have scheduled visits
- I want to schedule new visits to apartments
- I need to know what time each visit is scheduled
- I should see both complaint-related visits and general appointments

### The Data Model Challenge

**Before:**
```
Complaints Table:
- id
- description
- status
- created_at  ← Only creation date, no scheduled visit date!
```

**Problem:** Can't tell WHEN to visit. Calendar shows when complaint was created, not when visit is scheduled.

**After:**
```
Complaints Table:
- id
- description
- status
- created_at
- appointment_date  ← NEW! When manager will visit

Appointments Table (NEW):
- id
- flat_number
- appointment_date
- status
- notes
```

**Solution:** Two sources of scheduled visits:
1. Complaints with `appointment_date` set
2. Standalone appointments in `appointments` table

---

## Database Schema Design

### Understanding Database Constraints

**Constraint:** A rule enforced by the database to ensure data integrity.

**Example:** 
```sql
status VARCHAR(20) CHECK (status IN ('scheduled', 'completed', 'cancelled'))
```
This ensures only valid status values can be inserted!

### Step 1: Add appointment_date to Complaints

**File:** `backend/add_appointment_date_migration.sql`

```sql
-- Migration to add appointment_date to existing complaints table
-- Run this in your Supabase SQL Editor

-- Add appointment_date column to complaints table
ALTER TABLE complaints 
ADD COLUMN IF NOT EXISTS appointment_date TIMESTAMP WITH TIME ZONE;

-- Add a comment to document the column
COMMENT ON COLUMN complaints.appointment_date IS 'Scheduled date/time for manager to visit and fix the issue';

-- Optional: Add an index for faster queries by appointment_date
CREATE INDEX IF NOT EXISTS idx_complaints_appointment_date ON complaints(appointment_date);
```

**Why TIMESTAMP WITH TIME ZONE?**
```
Regular TIMESTAMP: "2026-02-10 14:30:00"
  → Problem: Is this India time? US time? Unknown!

TIMESTAMP WITH TIME ZONE: "2026-02-10 14:30:00+05:30"
  → Clear! This is India Standard Time
  → Database converts to UTC internally
  → Displays in user's timezone automatically
```

**How to Run:**
1. Go to Supabase Dashboard
2. Click **SQL Editor**
3. Paste the SQL
4. Click **Run**

### Step 2: Create Appointments Table

**File:** `backend/schema.sql` (excerpt)

```sql
-- Create appointments table
CREATE TABLE IF NOT EXISTS appointments (
    id SERIAL PRIMARY KEY,
    complaint_id INTEGER REFERENCES complaints(id) ON DELETE SET NULL,
    flat_number VARCHAR(20) NOT NULL,
    appointment_date TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'scheduled',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT appointments_status_check CHECK (status IN ('scheduled', 'completed', 'cancelled', 'rescheduled'))
);
```

**Field Breakdown:**

| Field | Type | Purpose | Why? |
|-------|------|---------|------|
| `id` | SERIAL | Auto-incrementing ID | Unique identifier |
| `complaint_id` | INTEGER (nullable) | Link to complaint if related | Not all appointments are about complaints |
| `flat_number` | VARCHAR(20) | Apartment number | "101", "A201", "B-305" |
| `appointment_date` | TIMESTAMP | When to visit | Core scheduling data |
| `status` | VARCHAR(20) | Current state | Track if completed/cancelled |
| `notes` | TEXT | Additional info | "Check water pressure", "Bring ladder" |
| `created_at` | TIMESTAMP | When appointment created | Audit trail |

**Key Design Decisions:**

1. **Why `complaint_id` is nullable?**
   ```
   Use Case 1: Complaint-related appointment
   complaint_id: 42  → Visit for complaint #42
   
   Use Case 2: General maintenance appointment
   complaint_id: NULL → Regular inspection, no complaint
   ```

2. **Why VARCHAR(20) for flat_number?**
   ```
   Allows flexible formats:
   - "101"
   - "A-201"
   - "Building-B-305"
   - "P12-Tower-3"
   ```

3. **Why CHECK constraint on status?**
   ```
   Prevents typos and invalid data:
   ✅ 'scheduled' → Allowed
   ❌ 'sched' → Rejected by database
   ❌ 'Scheduled' → Rejected (case-sensitive)
   ```

### Understanding Foreign Keys

```sql
complaint_id INTEGER REFERENCES complaints(id) ON DELETE SET NULL
```

**Translation:**
- `REFERENCES complaints(id)` → complaint_id must exist in complaints table
- `ON DELETE SET NULL` → If complaint deleted, set this to NULL (don't delete appointment)

**Example:**
```
Complaints Table:        Appointments Table:
id | description         id | complaint_id | flat_number
---|----                 ---|--------------|------------
42 | Leaky faucet        1  | 42           | 101

[Delete complaint #42]

Complaints Table:        Appointments Table:
(empty)                  id | complaint_id | flat_number
                         1  | NULL         | 101  ← Still exists!
```

---

## Backend API Development

### Understanding REST API Design

**REST Principle:** Resources are nouns, HTTP methods are verbs.

```
Resource: appointments

GET    /appointments     → List all
POST   /appointments     → Create new
GET    /appointments/5   → Get specific
PATCH  /appointments/5   → Update specific
DELETE /appointments/5   → Cancel specific
```

### Step 1: Create Pydantic Schemas

**File:** `backend/app/schemas/appointment.py`

```python
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from enum import Enum


class AppointmentStatus(str, Enum):
    """Enum for appointment status"""
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class AppointmentBase(BaseModel):
    flat_number: str = Field(..., description="Flat number for the appointment")
    appointment_date: datetime = Field(..., description="Scheduled date and time for the appointment")
    status: AppointmentStatus = Field(AppointmentStatus.SCHEDULED, description="Current status of the appointment")
    notes: Optional[str] = Field(None, description="Additional notes or instructions")


class AppointmentCreate(AppointmentBase):
    """Schema for creating a new appointment"""
    complaint_id: Optional[int] = Field(None, description="Related complaint ID if linked to a complaint")


class AppointmentUpdate(BaseModel):
    """Schema for updating an appointment"""
    appointment_date: Optional[datetime] = None
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None


class AppointmentResponse(AppointmentBase):
    """Schema for appointment responses"""
    id: int
    complaint_id: Optional[int] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
```

**Understanding Pydantic:**

**What is Pydantic?** A data validation library for Python.

**Why use it?**
```python
# Without Pydantic:
def create_appointment(data: dict):
    # Manual validation
    if 'flat_number' not in data:
        raise ValueError("Missing flat_number")
    if not isinstance(data['appointment_date'], datetime):
        raise ValueError("Invalid date format")
    # ... 20 more lines of validation

# With Pydantic:
def create_appointment(data: AppointmentCreate):
    # Automatic validation!
    # Pydantic ensures all fields are correct
    pass
```

**Field Explanations:**

1. **Field(..., description)**
   ```python
   flat_number: str = Field(..., description="Flat number")
   ```
   - `...` means "required field"
   - `description` appears in auto-generated API docs

2. **Optional[str] = None**
   ```python
   notes: Optional[str] = None
   ```
   - Field can be string or None
   - Default value is None

3. **Enum vs String**
   ```python
   # Without Enum:
   status: str  # Could be "sheduled" (typo!)
   
   # With Enum:
   status: AppointmentStatus  # Only valid values allowed
   ```

### Step 2: Create API Routes

**File:** `backend/app/routes/appointments.py`

```python
"""
Appointments API routes using Supabase client.
Handles CRUD operations for appointments.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from supabase import Client
from app.db.session import get_db
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
    AppointmentStatus
)
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate,
    db: Client = Depends(get_db)
):
    """Create a new appointment."""
    try:
        # Verify flat exists
        flat_response = db.table("flats")\
            .select("id")\
            .eq("flat_number", appointment_data.flat_number)\
            .execute()
        
        if not flat_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flat {appointment_data.flat_number} not found"
            )
        
        # Use mode='json' to serialize datetime and enum to strings
        insert_data = appointment_data.model_dump(mode='json')
        
        # Create appointment
        response = db.table("appointments").insert(insert_data).execute()
        
        if response.data:
            return response.data[0]
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create appointment"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating appointment: {str(e)}"
        )


@router.get("", response_model=list[AppointmentResponse])
async def get_appointments(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    flat_number: Optional[str] = Query(None, description="Filter by flat number"),
    db: Client = Depends(get_db)
):
    """
    Get all appointments with optional filters.
    
    Query params:
    - start_date: Filter appointments from this date (ISO format: 2024-01-01)
    - end_date: Filter appointments until this date
    - flat_number: Filter by specific flat
    """
    try:
        query = db.table("appointments").select("*")
        
        # Apply filters
        if start_date:
            query = query.gte("appointment_date", start_date)
        if end_date:
            query = query.lte("appointment_date", end_date)
        if flat_number:
            query = query.eq("flat_number", flat_number)
        
        response = query.order("appointment_date").execute()
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching appointments: {str(e)}"
        )
```

**Key Patterns:**

1. **Flat Validation Before Creation:**
   ```python
   # Check if flat exists in database
   flat_response = db.table("flats").select("id").eq("flat_number", "101").execute()
   
   if not flat_response.data:
       # Flat doesn't exist → Reject appointment
       raise HTTPException(404, "Flat not found")
   ```

2. **Query Filters:**
   ```python
   query = db.table("appointments").select("*")
   
   # Add filters dynamically
   if start_date:
       query = query.gte("appointment_date", start_date)  # >= start_date
   if end_date:
       query = query.lte("appointment_date", end_date)    # <= end_date
   ```

3. **Dependency Injection (Depends):**
   ```python
   async def create_appointment(
       appointment_data: AppointmentCreate,
       db: Client = Depends(get_db)  ← FastAPI injects database client
   ):
   ```

### Step 3: Register Router in Main App

**File:** `backend/app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import complaints, voice, flats, appointments  # Add appointments

app = FastAPI(title="Tenant Management API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(complaints.router)
app.include_router(voice.router)
app.include_router(flats.router)
app.include_router(appointments.router)  # NEW!
```

### Step 4: Test API with Python

**File:** `backend/test_appointments_table.py`

```python
"""
Quick test script to check if appointments table exists and test insertion
"""
import os
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Testing appointments table...")
print("=" * 60)

# Test 1: Check if table exists
try:
    result = supabase.table("appointments").select("*").limit(1).execute()
    print("Table exists!")
    print(f"Current appointments count: {len(result.data)}")
except Exception as e:
    print(f"Table error: {e}")
    print("\nThe appointments table doesn't exist in Supabase yet.")
    print("You need to run the schema.sql to create it.")
    exit(1)

# Test 2: Try to insert a test appointment
print("\nTrying to create a test appointment...")
try:
    test_data = {
        "flat_number": "101",
        "appointment_date": (datetime.now() + timedelta(days=3)).isoformat(),
        "status": "scheduled",
        "notes": "Test appointment from script"
    }
    
    result = supabase.table("appointments").insert(test_data).execute()
    print(f"Successfully created test appointment: {result.data}")
    
    # Clean up - delete the test appointment
    if result.data:
        supabase.table("appointments").delete().eq("id", result.data[0]["id"]).execute()
        print("(Test appointment cleaned up)")
        
except Exception as e:
    print(f"Failed to create appointment: {e}")
    print("\nThis is likely the same error the frontend is seeing.")

print("=" * 60)
```

**How to run:**
```bash
cd backend
python test_appointments_table.py
```

---

## Frontend Calendar Integration

### Understanding Date Libraries

**date-fns:** A modern JavaScript date library.

**Why not native Date?**
```javascript
// Native JavaScript Date (confusing):
const date = new Date();
date.getMonth();  // Returns 0-11 (January = 0) 😕
date.getDate();   // Day of month
date.getDay();    // Day of week 🤯

// date-fns (intuitive):
import { format, addDays, startOfMonth } from 'date-fns';

format(new Date(), 'MMMM d, yyyy');  // "February 5, 2026"
addDays(new Date(), 7);              // Next week
startOfMonth(new Date());            // First day of month
```

### Step 1: Update API Service

**File:** `frontend/src/services/api.js`

```javascript
const API_BASE_URL = 'http://localhost:8000';

export const api = {
  // Existing functions...
  
  // Verify if flat exists
  verifyFlat: async (flatNumber) => {
    const response = await fetch(`${API_BASE_URL}/flats/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ flat_number: flatNumber })
    });
    if (!response.ok) throw new Error('Failed to verify flat');
    return response.json();
  },
  
  // Fetch appointments with optional filters
  fetchAppointments: async (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    if (filters.flat_number) params.append('flat_number', filters.flat_number);
    
    const response = await fetch(`${API_BASE_URL}/appointments?${params}`);
    if (!response.ok) throw new Error('Failed to fetch appointments');
    return response.json();
  },
  
  // Create new appointment
  createAppointment: async (appointmentData) => {
    const response = await fetch(`${API_BASE_URL}/appointments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(appointmentData)
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create appointment');
    }
    return response.json();
  },
};
```

### Step 2: Enhance CompactCalendar Component

**File:** `frontend/src/components/CompactCalendar.jsx`

```javascript
import { useState, useMemo, useEffect } from 'react';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth, isToday, parseISO, isFuture } from 'date-fns';
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon } from 'lucide-react';
import { cn } from '@/lib';
import { api } from '../services/api';

function CompactCalendar({ complaints, onDateClick }) {
    const [currentDate, setCurrentDate] = useState(new Date());
    const [appointments, setAppointments] = useState([]);
    const [loading, setLoading] = useState(false);

    const monthStart = startOfMonth(currentDate);
    const monthEnd = endOfMonth(currentDate);
    const daysInMonth = eachDayOfInterval({ start: monthStart, end: monthEnd });

    // Fetch appointments when month changes
    useEffect(() => {
        fetchAppointments();
    }, [currentDate]);

    const fetchAppointments = async () => {
        setLoading(true);
        try {
            const data = await api.fetchAppointments({
                start_date: monthStart.toISOString(),
                end_date: monthEnd.toISOString()
            });
            setAppointments(data || []);
        } catch (error) {
            console.error('Failed to fetch appointments:', error);
            setAppointments([]);
        } finally {
            setLoading(false);
        }
    };

    // Merge complaints (by appointment_date) and standalone appointments
    const itemsByDate = useMemo(() => {
        const map = {};
        
        // Add complaints with appointment dates
        complaints.forEach(complaint => {
            const relevantDate = complaint.appointment_date 
                ? parseISO(complaint.appointment_date)
                : parseISO(complaint.created_at);
            const dateKey = format(relevantDate, 'yyyy-MM-dd');
            if (!map[dateKey]) map[dateKey] = [];
            map[dateKey].push({ ...complaint, type: 'complaint' });
        });
        
        // Add standalone appointments
        appointments.forEach(appointment => {
            const appointmentDate = parseISO(appointment.appointment_date);
            const dateKey = format(appointmentDate, 'yyyy-MM-dd');
            if (!map[dateKey]) map[dateKey] = [];
            map[dateKey].push({ ...appointment, type: 'appointment' });
        });
        
        return map;
    }, [complaints, appointments]);

    const previousMonth = () => {
        setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1));
    };

    const nextMonth = () => {
        setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1));
    };

    return (
        <div className="bg-card border border-border rounded-lg p-6 h-full">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <CalendarIcon className="w-5 h-5 text-primary" />
                    <h3 className="text-lg font-semibold text-foreground">
                        {format(currentDate, 'MMMM yyyy')}
                    </h3>
                </div>
                <div className="flex gap-2">
                    <button onClick={previousMonth} className="p-2 rounded-lg hover:bg-secondary transition-colors">
                        <ChevronLeft className="w-4 h-4 text-muted-foreground" />
                    </button>
                    <button onClick={nextMonth} className="p-2 rounded-lg hover:bg-secondary transition-colors">
                        <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    </button>
                </div>
            </div>

            {/* Legend */}
            <div className="flex items-center gap-3 mb-3 text-xs text-muted-foreground">
                <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full bg-primary/20"></div>
                    <span>Scheduled visits</span>
                </div>
            </div>

            {/* Calendar Grid */}
            <div className="grid grid-cols-7 gap-1">
                {/* Weekday headers */}
                {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((day, i) => (
                    <div key={i} className="text-center text-xs font-medium text-muted-foreground py-2">
                        {day}
                    </div>
                ))}

                {/* Calendar days */}
                {daysInMonth.map((day) => {
                    const dateKey = format(day, 'yyyy-MM-dd');
                    const itemsOnDate = itemsByDate[dateKey] || [];
                    const hasItems = itemsOnDate.length > 0;
                    const today = isToday(day);
                    const futureDate = isFuture(day) || isToday(day);

                    return (
                        <button
                            key={dateKey}
                            onClick={() => onDateClick(day, itemsOnDate)}
                            className={cn(
                                "aspect-square p-1 rounded-lg text-sm transition-all duration-200",
                                today && "ring-2 ring-primary ring-offset-2 ring-offset-background",
                                hasItems
                                    ? "bg-primary/10 text-foreground hover:bg-primary hover:text-primary-foreground cursor-pointer font-semibold"
                                    : futureDate 
                                        ? "text-foreground hover:bg-secondary cursor-pointer"
                                        : "text-muted-foreground hover:bg-secondary/50 cursor-pointer",
                                !isSameMonth(day, currentDate) && "opacity-30"
                            )}
                        >
                            <div className="flex flex-col items-center justify-center h-full">
                                <span>{format(day, 'd')}</span>
                                {hasItems && (
                                    <div className="flex items-center gap-0.5 mt-0.5">
                                        <span className="w-1.5 h-1.5 rounded-full bg-primary"></span>
                                        <span className="text-[10px] font-bold text-primary">
                                            {itemsOnDate.length}
                                        </span>
                                    </div>
                                )}
                            </div>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}

export default CompactCalendar;
```

**Key Concepts:**

1. **useEffect for Data Fetching:**
   ```javascript
   useEffect(() => {
       fetchAppointments();
   }, [currentDate]);  // Run when currentDate changes
   ```

2. **useMemo for Performance:**
   ```javascript
   const itemsByDate = useMemo(() => {
       // Expensive computation
       return map;
   }, [complaints, appointments]);  // Only recompute when these change
   ```

3. **Data Merging Strategy:**
   ```javascript
   const map = {};
   
   // Step 1: Add complaints
   complaints.forEach(complaint => {
       const dateKey = format(date, 'yyyy-MM-dd');  // "2026-02-05"
       if (!map[dateKey]) map[dateKey] = [];
       map[dateKey].push({ ...complaint, type: 'complaint' });
   });
   
   // Step 2: Add appointments to same dates
   appointments.forEach(appointment => {
       const dateKey = format(date, 'yyyy-MM-dd');
       if (!map[dateKey]) map[dateKey] = [];
       map[dateKey].push({ ...appointment, type: 'appointment' });
   });
   
   // Result: map['2026-02-05'] = [complaint1, appointment1, complaint2]
   ```

---

## Interactive Appointment Creation

### Step 1: Create DateComplaintsModal with Form

**File:** `frontend/src/components/DateComplaintsModal.jsx`

```javascript
import { useState } from 'react';
import { motion } from 'framer-motion';
import { X, Calendar, Plus, Clock } from 'lucide-react';
import { format, parseISO, isFuture, isToday } from 'date-fns';
import PriorityBadge from './PriorityBadge';
import { cn } from '@/lib';
import { api } from '../services/api';

function DateComplaintsModal({ date, complaints, onClose, onComplaintClick }) {
    const canSchedule = isFuture(date) || isToday(date);
    const [showForm, setShowForm] = useState(false);
    const [formData, setFormData] = useState({
        flat_number: '',
        time: '10:00',
        notes: ''
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [flatError, setFlatError] = useState('');

    // Separate complaints and appointments
    const actualComplaints = complaints.filter(item => item.type === 'complaint');
    const standaloneAppointments = complaints.filter(item => item.type === 'appointment');
    const allItems = [...actualComplaints, ...standaloneAppointments];

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
        if (name === 'flat_number') setFlatError('');
        setError('');
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            // Step 1: Verify flat exists
            const flatCheck = await api.verifyFlat(formData.flat_number);
            if (!flatCheck.exists) {
                setFlatError(`Flat ${formData.flat_number} does not exist`);
                setLoading(false);
                return;
            }

            // Step 2: Combine date and time
            const appointmentDateTime = new Date(date);
            const [hours, minutes] = formData.time.split(':');
            appointmentDateTime.setHours(parseInt(hours), parseInt(minutes), 0);

            // Step 3: Create appointment
            await api.createAppointment({
                flat_number: formData.flat_number,
                appointment_date: appointmentDateTime.toISOString(),
                notes: formData.notes || null,
                status: 'scheduled'
            });

            // Step 4: Reset and close
            setFormData({ flat_number: '', time: '10:00', notes: '' });
            setShowForm(false);
            
            // Step 5: Refresh page to show new appointment
            window.location.reload();
        } catch (err) {
            setError(err.message || 'Failed to create appointment');
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50" onClick={onClose}>
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                onClick={(e) => e.stopPropagation()}
                className="bg-card border border-border rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl"
            >
                {/* Header */}
                <div className="flex items-start justify-between p-6 border-b border-border">
                    <div className="flex items-center gap-3">
                        <Calendar className="w-6 h-6 text-primary" />
                        <div>
                            <h2 className="text-2xl font-bold text-foreground">
                                {format(date, 'MMMM d, yyyy')}
                            </h2>
                            <p className="text-sm text-muted-foreground">
                                {allItems.length} scheduled visit{allItems.length !== 1 ? 's' : ''}
                            </p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 rounded-lg hover:bg-secondary transition-colors">
                        <X className="w-5 h-5 text-muted-foreground" />
                    </button>
                </div>

                {/* Scheduled Visits List */}
                <div className="p-6 space-y-3">
                    {allItems.length === 0 ? (
                        <div className="text-center py-8">
                            <Calendar className="w-12 h-12 text-muted-foreground mx-auto mb-3 opacity-50" />
                            <p className="text-muted-foreground">
                                {canSchedule ? 'No visits scheduled for this date' : 'No visits on this date'}
                            </p>
                        </div>
                    ) : (
                        allItems.map((item, index) => {
                            const isComplaint = item.type === 'complaint';
                            
                            return (
                                <button
                                    key={`${item.type}-${item.id}-${index}`}
                                    onClick={() => {
                                        if (isComplaint) {
                                            onClose();
                                            onComplaintClick(item);
                                        }
                                    }}
                                    className={cn(
                                        "w-full text-left p-4 rounded-lg border border-border bg-secondary",
                                        isComplaint && "hover:border-primary hover:bg-card transition-all duration-200 group cursor-pointer",
                                        !isComplaint && "cursor-default"
                                    )}
                                >
                                    <div className="flex items-start justify-between gap-2 mb-2">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className="text-xs font-medium text-muted-foreground">
                                                    Flat {item.flat_number || 'N/A'}
                                                </span>
                                                {isComplaint && (
                                                    <>
                                                        <span className="text-xs text-muted-foreground">•</span>
                                                        <span className="text-xs font-medium text-primary capitalize">
                                                            {item.category}
                                                        </span>
                                                    </>
                                                )}
                                                {!isComplaint && (
                                                    <>
                                                        <span className="text-xs text-muted-foreground">•</span>
                                                        <span className="text-xs font-medium text-blue-500">
                                                            Appointment
                                                        </span>
                                                    </>
                                                )}
                                            </div>
                                            <h4 className={cn(
                                                "text-sm font-semibold text-foreground",
                                                isComplaint && "group-hover:text-primary transition-colors"
                                            )}>
                                                {isComplaint 
                                                    ? `${item.description?.substring(0, 60)}${item.description?.length > 60 ? '...' : ''}`
                                                    : item.notes || 'Scheduled visit'
                                                }
                                            </h4>
                                        </div>
                                        {isComplaint && <PriorityBadge priority={item.priority} />}
                                    </div>
                                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-2">
                                        <Clock className="w-3.5 h-3.5" />
                                        <span>{format(parseISO(item.appointment_date), 'h:mm a')}</span>
                                    </div>
                                </button>
                            );
                        })
                    )}
                </div>

                {/* Schedule New Appointment Form */}
                {canSchedule && (
                    <div className="p-6 pt-0">
                        {!showForm ? (
                            <button
                                onClick={() => setShowForm(true)}
                                className="w-full p-4 rounded-lg border-2 border-dashed border-border bg-secondary/50 hover:bg-secondary hover:border-primary transition-all group"
                            >
                                <Plus className="w-8 h-8 text-muted-foreground group-hover:text-primary mx-auto mb-2 transition-colors" />
                                <p className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                                    Schedule New Appointment
                                </p>
                                <p className="text-xs text-muted-foreground mt-1">
                                    Click to create a visit for this date
                                </p>
                            </button>
                        ) : (
                            <motion.form
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                onSubmit={handleSubmit}
                                className="bg-secondary/50 rounded-lg border border-border p-4 space-y-4"
                            >
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="text-sm font-semibold text-foreground">New Appointment</h3>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setShowForm(false);
                                            setError('');
                                            setFlatError('');
                                        }}
                                        className="text-xs text-muted-foreground hover:text-foreground"
                                    >
                                        Cancel
                                    </button>
                                </div>

                                {error && (
                                    <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                                        <p className="text-xs text-red-500">{error}</p>
                                    </div>
                                )}

                                <div>
                                    <label className="block text-xs font-medium text-foreground mb-1.5">
                                        Flat Number *
                                    </label>
                                    <input
                                        type="text"
                                        name="flat_number"
                                        value={formData.flat_number}
                                        onChange={handleChange}
                                        placeholder="e.g., 101, A201, B305"
                                        required
                                        className={cn(
                                            "w-full px-3 py-2 rounded-lg border bg-background text-foreground text-sm",
                                            "focus:outline-none focus:ring-2 focus:ring-primary/50",
                                            flatError ? "border-red-500" : "border-border"
                                        )}
                                    />
                                    {flatError && <p className="text-xs text-red-500 mt-1">{flatError}</p>}
                                </div>

                                <div>
                                    <label className="block text-xs font-medium text-foreground mb-1.5">
                                        Time *
                                    </label>
                                    <input
                                        type="time"
                                        name="time"
                                        value={formData.time}
                                        onChange={handleChange}
                                        required
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                                    />
                                </div>

                                <div>
                                    <label className="block text-xs font-medium text-foreground mb-1.5">
                                        Notes (Optional)
                                    </label>
                                    <textarea
                                        name="notes"
                                        value={formData.notes}
                                        onChange={handleChange}
                                        placeholder="Add any notes about this appointment..."
                                        rows="2"
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
                                    />
                                </div>

                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="w-full px-4 py-2.5 rounded-lg bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {loading ? 'Creating...' : 'Create Appointment'}
                                </button>
                            </motion.form>
                        )}
                    </div>
                )}
            </motion.div>
        </div>
    );
}

export default DateComplaintsModal;
```

**Form Handling Patterns:**

1. **Controlled Inputs:**
   ```javascript
   const [formData, setFormData] = useState({ flat_number: '', time: '10:00' });
   
   <input
       value={formData.flat_number}
       onChange={(e) => setFormData({ ...formData, flat_number: e.target.value })}
   />
   ```

2. **Async Submit with Validation:**
   ```javascript
   const handleSubmit = async (e) => {
       e.preventDefault();  // Don't reload page
       
       try {
           // Validate
           const flatCheck = await api.verifyFlat(formData.flat_number);
           if (!flatCheck.exists) {
               setFlatError("Flat doesn't exist");
               return;
           }
           
           // Submit
           await api.createAppointment(data);
           
           // Success
           window.location.reload();
       } catch (err) {
           setError(err.message);
       }
   };
   ```

3 **Combining Date and Time:**
   ```javascript
   // User selects date: Feb 10, 2026
   const date = new Date("2026-02-10");
   
   // User selects time: 14:30
   const time = "14:30";
   const [hours, minutes] = time.split(':');  // ["14", "30"]
   
   // Combine them
   date.setHours(parseInt(hours), parseInt(minutes), 0);
   // Result: 2026-02-10T14:30:00
   
   // Convert to ISO for API
   const isoString = date.toISOString();
   // "2026-02-10T09:00:00.000Z" (in UTC!)
   ```

---

## Debugging DateTime Serialization

### The Problem: 500 Internal Server Error

**What Happened:**
```
User tried to create appointment through frontend form
Frontend showed: "Failed to create appointment"
Backend logs showed: INFO: 127.0.0.1:57797 - "POST /appointments HTTP/1.1" 500 Internal Server Error
```

**Our Debugging Journey:**

#### Step 1: Verify Table Exists

**First thought:** Maybe the `appointments` table doesn't exist in Supabase?

**Test Command:**
```bash
cd backend
python -c "import os; from supabase import create_client; from dotenv import load_dotenv; load_dotenv(); s = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')); r = s.table('appointments').select('*').limit(1).execute(); print(f'Table exists! Count: {len(r.data)}')"
```

**Result:**
```
Table exists! Count: 0
```

**Conclusion:** ✅ Table exists but empty. Problem is elsewhere.

---

#### Step 2: Test Direct Database Insert

**Second thought:** Maybe the database schema has issues? Let's try inserting directly.

**Test Command:**
```bash
python -c "import os; from supabase import create_client; from dotenv import load_dotenv; from datetime import datetime; load_dotenv(); s = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')); data = {'flat_number': '101', 'appointment_date': '2026-02-10T10:00:00', 'status': 'scheduled', 'notes': 'Test'}; r = s.table('appointments').insert(data).execute(); print(f'Success: {r.data}')"
```

**Result:**
```
Success: [{'id': 1, 'complaint_id': None, 'flat_number': '101', 'appointment_date': '2026-02-10T10:00:00', 'status': 'scheduled', 'notes': 'Test', 'created_at': '2026-02-05T10:09:27.973911'}]
```

**Conclusion:** ✅ Database and schema are fine! The problem is in how the API serializes data.

---

#### Step 3: Investigate Pydantic Serialization

**Third thought:** What is `model_dump()` actually returning?

**Test Command:**
```bash
python -c "from app.schemas.appointment import AppointmentCreate; from datetime import datetime; a = AppointmentCreate(flat_number='101', appointment_date=datetime(2026,2,10,10,0), status='scheduled', notes='Test'); print('model_dump:', a.model_dump()); print('status type:', type(a.model_dump()['status']))"
```

**Result:**
```
model_dump: {'flat_number': '101', 'appointment_date': datetime.datetime(2026, 2, 10, 10, 0), 'status': <AppointmentStatus.SCHEDULED: 'scheduled'>, 'notes': 'Test', 'complaint_id': None}
status type: <enum 'AppointmentStatus'>
```

**🚨 FOUND THE PROBLEM!**

**Two issues discovered:**
1. `appointment_date` is a `datetime.datetime` object, not a string!
2. `status` is an `AppointmentStatus` enum object, not a string!

**Why this causes 500 error:**
```python
# What Pydantic sends:
db.table("appointments").insert({
    'appointment_date': datetime.datetime(2026, 2, 10, 10, 0),  # ❌ Object!
    'status': <AppointmentStatus.SCHEDULED: 'scheduled'>        # ❌ Enum!
})

# What Supabase expects (JSON):
db.table("appointments").insert({
    'appointment_date': '2026-02-10T10:00:00',  # ✅ String!
    'status': 'scheduled'                        # ✅ String!
})
```

---

### The Solution: mode='json'

**File:** `backend/app/routes/appointments.py` (excerpt)

```python
@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate,
    db: Client = Depends(get_db)
):
    try:
        # Verify flat exists
        flat_response = db.table("flats").select("id").eq("flat_number", appointment_data.flat_number).execute()
        if not flat_response.data:
            raise HTTPException(404, f"Flat {appointment_data.flat_number} not found")
        
        # ✅ FIX: Use mode='json' to serialize datetime and enum to strings
        insert_data = appointment_data.model_dump(mode='json')
        
        # Now insert_data contains proper JSON strings:
        # {
        #     'flat_number': '101',
        #     'appointment_date': '2026-02-10T10:00:00',  ← String!
        #     'status': 'scheduled',                       ← String!
        #     'notes': 'Test'
        # }
        
        response = db.table("appointments").insert(insert_data).execute()
        
        if response.data:
            return response.data[0]
        else:
            raise HTTPException(500, "Failed to create appointment")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error creating appointment: {str(e)}")
```

---

### Testing the Fix

**Test Command:**
```bash
python -c "from app.schemas.appointment import AppointmentCreate; from datetime import datetime; a = AppointmentCreate(flat_number='101', appointment_date=datetime(2026,2,10,14,30), status='scheduled', notes='Test appointment'); d = a.model_dump(mode='json'); print('Serialized data:', d); print('appointment_date type:', type(d['appointment_date'])); print('status type:', type(d['status']))"
```

**Result:**
```
Serialized data: {'flat_number': '101', 'appointment_date': '2026-02-10T14:30:00', 'status': 'scheduled', 'notes': 'Test appointment', 'complaint_id': None}
appointment_date type: <class 'str'>
status type: <class 'str'>
```

**✅ SUCCESS! Both are now strings!**

---

### Why mode='json' Works

**Pydantic's model_dump() modes:**

```python
# Default mode (mode='python'):
appointment_data.model_dump()
# Returns Python-native types: datetime objects, enums, etc.
# Good for: Python-to-Python communication
# Bad for: JSON APIs, databases

# JSON mode (mode='json'):
appointment_data.model_dump(mode='json')
# Returns JSON-serializable types: strings, ints, etc.
# Good for: APIs, databases, web responses
# Bad for: Nothing! Use this for external systems
```

**Automatic conversions mode='json' does:**
- `datetime.datetime(2026, 2, 10, 10, 0)` → `"2026-02-10T10:00:00"`
- `AppointmentStatus.SCHEDULED` → `"scheduled"`
- `date.today()` → `"2026-02-05"`
- `UUID(...)` → `"550e8400-e29b-41d4-a716-446655440000"`

---

### The Complete Debugging Checklist

When you encounter 500 errors in API endpoints, follow this checklist:

**1. Verify table exists:**
```bash
python -c "from supabase import create_client; import os; from dotenv import load_dotenv; load_dotenv(); s = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')); r = s.table('TABLE_NAME').select('*').limit(1).execute(); print('Table exists!')"
```

**2. Test direct insert with proper types:**
```bash
python -c "from supabase import create_client; import os; from dotenv import load_dotenv; load_dotenv(); s = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')); data = {'field': 'value'}; r = s.table('TABLE_NAME').insert(data).execute(); print(r.data)"
```

**3. Check what Pydantic is returning:**
```bash
python -c "from app.schemas.YOUR_SCHEMA import YourModel; m = YourModel(...); print(m.model_dump()); print({k: type(v) for k, v in m.model_dump().items()})"
```

**4. Test with mode='json':**
```bash
python -c "from app.schemas.YOUR_SCHEMA import YourModel; m = YourModel(...); print(m.model_dump(mode='json')); print({k: type(v) for k, v in m.model_dump(mode='json').items()})"
```

**5. Check backend logs:**
```
Look for the actual error message in uvicorn output
Common patterns:
- "not JSON serializable" → Use mode='json'
- "column does not exist" → Run database migration
- "foreign key constraint" → Referenced record doesn't exist
```

---

### Real-World Debugging Session

**Timeline of our session:**

```
15:38 - User reports: "POST /appointments HTTP/1.1" 500 Internal Server Error
15:39 - Created test_appointments_table.py to check table existence
15:40 - Confirmed table exists (0 rows)
15:41 - Tested direct insert with string values → SUCCESS
15:42 - Realized: API must be sending wrong data types
15:43 - Tested model_dump() output → Found datetime and enum objects
15:44 - Added mode='json' to model_dump() call
15:45 - Backend auto-reloaded
15:46 - User tested: "POST /appointments HTTP/1.1" 201 Created ✅
```

**Total debugging time:** 8 minutes

**Key lesson:** Always check what types you're actually sending to external systems!

---


    appointment_date=datetime(2026, 2, 10, 14, 30),
    status='scheduled',
    notes='Test'
)

# Without mode='json':
print('Default:', a.model_dump())
# appointment_date: datetime.datetime(2026, 2, 10, 14, 30)
# status: <AppointmentStatus.SCHEDULED: 'scheduled'>

# With mode='json':
print('JSON mode:', a.model_dump(mode='json'))
# appointment_date: '2026-02-10T14:30:00'
# status: 'scheduled'
"
```

---

## Merging Multiple Data Sources

### The Challenge

**Calendar must show:**
1. Complaints with `appointment_date` set (manager visit for complaint)
2. Standalone appointments from `appointments` table (general maintenance)

### The Solution: Tagged Objects

**Step 1: Tag Data by Source**

```javascript
// In CompactCalendar.jsx
const itemsByDate = useMemo(() => {
    const map = {};
    
    // Add complaints with 'type' tag
    complaints.forEach(complaint => {
        const date = parseISO(complaint.appointment_date);
        const dateKey = format(date, 'yyyy-MM-dd');
        if (!map[dateKey]) map[dateKey] = [];
        map[dateKey].push({ 
            ...complaint, 
            type: 'complaint'  // ← Tag
        });
    });
    
    // Add appointments with 'type' tag
    appointments.forEach(appointment => {
        const date = parseISO(appointment.appointment_date);
        const dateKey = format(date, 'yyyy-MM-dd');
        if (!map[dateKey]) map[dateKey] = [];
        map[dateKey].push({ 
            ...appointment, 
            type: 'appointment'  // ← Tag
        });
    });
    
    return map;
}, [complaints, appointments]);

// Result example:
// itemsByDate = {
//     '2026-02-10': [
//         { id: 5, description: '...', type: 'complaint' },
//         { id: 2, notes: '...', type: 'appointment' }
//     ]
// }
```

**Step 2: Render Different UI Based on Type**

```javascript
// In DateComplaintsModal.jsx
allItems.map(item => {
    const isComplaint = item.type === 'complaint';
    
    return (
        <button
            className={isComplaint ? "cursor-pointer hover:bg-primary" : "cursor-default"}
            onClick={() => {
                if (isComplaint) {
                    // Open complaint details modal
                    onComplaintClick(item);
                }
                // Appointments are not clickable (no detail view yet)
            }}
        >
            {/* Show category for complaints */}
            {isComplaint && <span>{item.category}</span>}
            
            {/* Show "Appointment" badge for standalone appointments */}
            {!isComplaint && <span className="text-blue-500">Appointment</span>}
            
            {/* Show description for complaints, notes for appointments */}
            <h4>{isComplaint ? item.description : item.notes}</h4>
        </button>
    );
});
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Missing Schema Migration

**Symptom:**
```
Error: Could not find the 'appointment_date' column of 'complaints' in the schema cache
```

**Cause:** Added column to code but not to database.

**Solution:**
```bash
# 1. Open Supabase Dashboard
# 2. Navigate to SQL Editor
# 3. Run migration:

ALTER TABLE complaints 
ADD COLUMN IF NOT EXISTS appointment_date TIMESTAMP WITH TIME ZONE;
```

### Pitfall 2: DateTime Not Serializing

**Symptom:**
```
500 Internal Server Error
"datetime.datetime object is not JSON serializable"
```

**Cause:** Sending Python datetime object to Supabase.

**Solution:**
```python
# ❌ Wrong:
insert_data = appointment_data.model_dump()

# ✅ Correct:
insert_data = appointment_data.model_dump(mode='json')
```

### Pitfall 3: Timezone Confusion

**Problem:**
```
User in India (UTC+5:30) creates appointment at 2:00 PM
Backend stores: 2026-02-10T14:00:00
Calendar shows: 2:00 PM ← Correct!

User in US (UTC-5) views same appointment
Calendar shows: 2:00 PM ← WRONG! Should be different time
```

**Solution:** Always use TIMESTAMP WITH TIME ZONE in database.

```sql
-- ❌ Wrong:
appointment_date TIMESTAMP

-- ✅ Correct:
appointment_date TIMESTAMP WITH TIME ZONE
```

### Pitfall 4: Not Refetching After Create

**Problem:** Appointment created successfully but calendar doesn't update.

**Solution:**
```javascript
// Option 1: Reload page (simple but not elegant)
window.location.reload();

// Option 2: Refetch appointments (better)
await api.createAppointment(data);
await fetchAppointments();  // Refresh calendar data
```

### Pitfall 5: Flat Validation Race Condition

**Problem:**
```javascript
// Wrong: Check flat exists, but don't wait
api.verifyFlat(flatNumber);  // Returns Promise
api.createAppointment({ flat_number: flatNumber, ... });  // Runs immediately!
```

**Solution:**
```javascript
// Correct: Wait for validation
const flatCheck = await api.verifyFlat(flatNumber);
if (!flatCheck.exists) {
    throw new Error("Flat doesn't exist");
}
// Only then create appointment
await api.createAppointment({ ... });
```

---

## Complete Code Examples

### Example 1: Seed Appointments for Testing

**File:** `backend/seed_complaints_with_appointments.py`

```python
"""
Seed script to add test complaints with appointment dates to see on calendar.
Run this to create sample complaints with scheduled visit dates.
"""
import os
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

# Create Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def seed_complaints_with_appointments():
    """Seed complaints table with appointment dates"""
    
    # Create complaints for the next few days
    base_date = datetime.now()
    
    complaints_data = [
        {
            "flat_number": "101",
            "category": "plumbing",
            "priority": "high",
            "description": "Kitchen sink is leaking heavily. Water pooling on floor.",
            "status": "pending",
            "source": "web",
            "appointment_date": (base_date + timedelta(days=1, hours=10)).isoformat()
        },
        {
            "flat_number": "A201",
            "category": "electrical",
            "priority": "high",
            "description": "Main circuit breaker keeps tripping. No power in living room.",
            "status": "pending",
            "source": "voice",
            "appointment_date": (base_date + timedelta(days=1, hours=14)).isoformat()
        },
        {
            "flat_number": "B102",
            "category": "maintenance",
            "priority": "medium",
            "description": "Door lock is jammed, difficult to open from outside.",
            "status": "pending",
            "source": "web",
            "appointment_date": (base_date + timedelta(days=2, hours=9)).isoformat()
        },
        {
            "flat_number": "A102",
            "category": "hvac",
            "priority": "medium",
            "description": "Air conditioning not cooling properly, making strange noises.",
            "status": "in-progress",
            "source": "voice",
            "appointment_date": (base_date + timedelta(days=3, hours=11)).isoformat()
        },
        {
            "flat_number": "C101",
            "category": "plumbing",
            "priority": "low",
            "description": "Bathroom faucet drips occasionally.",
            "status": "pending",
            "source": "web",
            "appointment_date": (base_date + timedelta(days=4, hours=15)).isoformat()
        },
    ]
    
    print(f"Seeding {len(complaints_data)} complaints with appointment dates...")
    
    try:
        # Insert all complaints
        response = supabase.table("complaints").insert(complaints_data).execute()
        print(f"Successfully seeded {len(complaints_data)} complaints!")
        print("\nScheduled visits:")
        for complaint in complaints_data:
            visit_date = datetime.fromisoformat(complaint["appointment_date"])
            print(f"  {visit_date.strftime('%A, %b %d at %I:%M %p')} - Flat {complaint['flat_number']} ({complaint['category']})")
        return response.data
    except Exception as e:
        print(f"Error seeding complaints: {e}")
        return None


if __name__ == "__main__":
    print("=" * 70)
    print("SEEDING COMPLAINTS WITH APPOINTMENT DATES")
    print("=" * 70)
    seed_complaints_with_appointments()
    print("=" * 70)
    print("\nNow check the calendar in the frontend to see the scheduled visits!")
```

**How to run:**
```bash
cd backend
python seed_complaints_with_appointments.py
```

---

## Testing & Verification

### Backend Testing Checklist

**Test 1: Verify Table Exists**
```bash
python -c "
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
s = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

result = s.table('appointments').select('*').limit(1).execute()
print('✅ Appointments table exists!')
print(f'Count: {len(result.data)}')
"
```

**Test 2: Test Direct Insert**
```bash
python -c "
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
s = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

data = {
    'flat_number': '101',
    'appointment_date': '2026-02-10T10:00:00',
    'status': 'scheduled',
    'notes': 'Test'
}

result = s.table('appointments').insert(data).execute()
print('✅ Insert successful!')
print(result.data)
"
```

**Test 3: Test API Endpoint**
```bash
# Test with curl (if available in Git Bash or WSL)
curl -X POST http://localhost:8000/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "flat_number": "101",
    "appointment_date": "2026-02-10T14:30:00",
    "status": "scheduled",
    "notes": "Test appointment"
  }'
```

### Frontend Testing Checklist

**Visual Test 1: Calendar Shows Dots**
1. Run `npm run dev`
2. Check calendar widget on dashboard
3. Verify dates with appointments show blue dots
4. Verify dot count matches number of visits

**Visual Test 2: Date Click Shows Modal**
1. Click date with blue dot
2. Modal should open
3. Should show all visits for that date
4. Each visit should show:
   - Flat number
   - Time
   - Type (Complaint/Appointment)
   - Status badge

**Functional Test 3: Create Appointment**
1. Click future date (no dot)
2. Modal opens
3. Click "Schedule New Appointment"
4. Fill form:
   - Flat: "101"
   - Time: "2:30 PM"
   - Notes: "Check water heater"
5. Click "Create Appointment"
6. Page refreshes
7. Blue dot appears on that date
8. Click date again
9. New appointment visible in list

**Error Test 4: Invalid Flat**
1. Try creating appointment with flat "999"
2. Should show error: "Flat 999 does not exist"
3. Should NOT create appointment
4. Calendar should NOT show dot

---

## Senior Developer Mindset

### Anticipate Edge Cases

**Think ahead:**
```
What if user creates appointment in the past?
→ Disable form for past dates

What if flat is deleted after appointment created?
→ Use ON DELETE SET NULL in foreign key

What if two users create appointments at same time?
→ Database handles concurrency automatically

What if timezone is wrong?
→ Always use TIMESTAMP WITH TIME ZONE
```

### Design for Extensibility

**Current:** Appointments for apartment visits
**Future:** Could extend to:
- Recurring appointments
- Multiple assignees
- Email reminders
- Conflict detection

**How we prepared:**
```sql
-- Status constraint allows adding new states
CHECK (status IN ('scheduled', 'completed', 'cancelled', 'rescheduled'))
-- Easy to add 'recurring', 'pending-approval', etc.

-- Notes field is TEXT (unlimited)
-- Can store JSON: {"recurrence": "weekly", "assignee": "John"}
```

### Write Debuggable Code

**Bad:**
```python
try:
    data = appointment_data.model_dump()
    response = db.table("appointments").insert(data).execute()
    return response.data[0]
except:
    raise HTTPException(500, "Error")
```

**Good:**
```python
try:
    # Step 1: Serialize (can fail)
    insert_data = appointment_data.model_dump(mode='json')
    
    # Step 2: Insert (can fail)
    response = db.table("appointments").insert(insert_data).execute()
    
    # Step 3: Validate response (can fail)
    if not response.data:
        raise HTTPException(500, "No data returned from insert")
    
    return response.data[0]
except HTTPException:
    raise  # Re-raise HTTP exceptions
except Exception as e:
    # Log actual error for debugging
    print(f"Appointment creation failed: {e}")
    raise HTTPException(500, f"Error creating appointment: {str(e)}")
```

### Document Gotchas

```python
# ⚠️ IMPORTANT: Must use mode='json' for Supabase!
# 
# Pydantic's model_dump() returns Python objects:
# - datetime → datetime.datetime object
# - Enum → AppointmentStatus object
#
# Supabase requires JSON strings:
# - datetime → "2026-02-10T14:30:00"
# - Enum → "scheduled"
#
# mode='json' handles this automatically
insert_data = appointment_data.model_dump(mode='json')
```

---

## Critical Bug: Calendar Month-Start Day Alignment

### The Bug

The calendar built in this session has a subtle but visually obvious bug that only manifests when the 1st of the month falls on a non-Sunday.

**Example:** If March 1 is a Saturday, the calendar renders:
```
S  M  T  W  T  F  S
1  2  3  4  5  6  7   ← WRONG: 1 should be in the Saturday column
```

Instead of the correct layout:
```
S  M  T  W  T  F  S
               1  2
3  4  5  6  7  8  9
```

**Root Cause:** The calendar grid maps `daysInMonth` directly without prepending empty placeholder cells for the days in the first row before the 1st of the month.

```jsx
// ❌ ORIGINAL CODE — missing leading empty cells
{daysInMonth.map((day) => (
    <button key={format(day, 'yyyy-MM-dd')}>
        {format(day, 'd')}
    </button>
))}
```

This renders dates 1-28/30/31 in a 7-column grid starting from position 0 (Sunday column). If the month starts on Wednesday, position 0 should be empty — but dates 1, 2, 3 fill positions 0, 1, 2 instead.

### The Fix: Prepend Empty Cells

```jsx
const monthStart = startOfMonth(currentDate);

// How many empty cells to prepend?
// getDay() returns 0=Sunday, 1=Monday, ..., 6=Saturday
// If the 1st falls on Wednesday (3), we need 3 empty cells
const leadingEmptyDays = monthStart.getDay();  // 0-6

return (
    <div className="grid grid-cols-7 gap-px bg-border">
        {/* Empty cells for days before the 1st */}
        {Array.from({ length: leadingEmptyDays }).map((_, i) => (
            <div key={`empty-${i}`} className="bg-background min-h-[90px]" />
        ))}

        {/* Actual date cells */}
        {daysInMonth.map((day) => {
            const dateKey = format(day, 'yyyy-MM-dd');
            return (
                <div key={dateKey} className="bg-background min-h-[90px]">
                    {format(day, 'd')}
                </div>
            );
        })}
    </div>
);
```

**Why `Array.from({ length: n })`?** This creates an array of `n` empty slots in a single expression. `Array.from({ length: 0 })` creates an empty array, so if the month starts on Sunday (getDay() = 0), no empty cells are added. Clean and correct.

**The `gap-px bg-border` grid trick:** Instead of adding a border to each cell (which would double up at shared edges), set `gap-px` on the grid and `bg-border` on the grid itself. Each 1px gap shows the grid's background color as a border line — one pixel, never doubled.

### When to Apply This Fix

This fix is required any time you render a month calendar grid where:
1. Days of the month are the only items in the grid
2. The grid aligns to a 7-column week layout starting with Sunday
3. You're using `eachDayOfInterval({ start: monthStart, end: monthEnd })`

Without this fix, the calendar is aesthetically wrong and unusable for all months except those that happen to start on Sunday.

---

## Congratulations! 🎉

You've built a production-ready appointment scheduling system with:
- ✅ Proper database schema with constraints
- ✅ RESTful API with validation
- ✅ Interactive calendar UI
- ✅ DateTime handling across timezones
- ✅ Multi-source data merging
- ✅ Error handling and debugging

**What you learned:**
1. Database schema design (tables, constraints, foreign keys)
2. API development (Pydantic, FastAPI, Supabase)
3. Frontend state management (useState, useEffect, useMemo)
4. DateTime handling (date-fns, ISO format, timezones)
5. Form validation (async, real-time feedback)
6. Debugging serialization issues
7. Merging data from multiple sources

**Next steps:**
- Add recurring appointments
- Implement email/SMS reminders
- Add conflict detection
- Export to Google Calendar
- Add appointment history

You're now ready to build complex calendar systems in any tech stack! 🚀
