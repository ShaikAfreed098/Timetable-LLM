"""
LLM Agent powered by LangChain + OpenAI with tool/function calling.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Generator, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.core.scheduler import generate_timetable, check_conflicts
from app.models.faculty import Faculty
from app.models.subject import Subject
from app.models.room import Room, RoomType
from app.models.batch import Batch
from app.models.timetable import Assignment

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an intelligent college timetable assistant.

College hours: 9:10 AM to 4:00 PM. Each teaching period is 50 minutes.
Morning break: 10:50 AM – 11:00 AM (non-negotiable, not a teaching period).
Lunch break: 12:40 PM – 1:30 PM (non-negotiable, not a teaching period).
Period schedule:
  P1 09:10–10:00 | P2 10:00–10:50 | [Break] |
  P3 11:00–11:50 | P4 11:50–12:40 | [Lunch] |
  P5 13:30–14:20 | P6 14:20–15:10 | P7 15:10–16:00

You have access to tools:
  - add_faculty: add a faculty member
  - add_subject: add a subject
  - add_room: add a room
  - add_batch: add a student batch/section
  - assign_subject: assign a subject to a faculty for a batch
  - generate_timetable: generate a conflict-free timetable
  - check_conflicts: check a timetable for conflicts
  - get_faculty_schedule: retrieve a faculty member's schedule

Always confirm destructive actions with the user before proceeding.
Present timetables as formatted Markdown tables.
If you do not have enough information to call a tool, ask the user for the missing details.

CRITICAL INSTRUCTION: YOU MUST ONLY CALL ONE TOOL PER RESPONSE. NEVER CALL MULTIPLE TOOLS AT THE SAME TIME.
If the user provides a list of multiple items (e.g. 2 instances of Faculty, 2 Subjects, 2 Assignments), you MUST call the tool for the FIRST item only.
Wait for the system to return the result of that tool, and then in your next turn, call the tool for the SECOND item. 
DO NOT OUTPUT MORE THAN ONE TOOL CALL IN A SINGLE TURN, OR THE SYSTEM WILL CRASH.
"""

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "add_faculty",
            "description": "Add a new faculty member to the system.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "department": {"type": "string"},
                    "email": {"type": "string"},
                    "max_periods_per_day": {"type": "integer", "default": 5},
                    "unavailable_slots": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "day": {"type": "string"},
                                "period": {"type": "integer"},
                            },
                        },
                    },
                },
                "required": ["name", "department", "email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_subject",
            "description": "Add a new subject/course.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "code": {"type": "string"},
                    "department": {"type": "string"},
                    "credits": {"type": "integer", "default": 3},
                    "periods_per_week": {"type": "integer", "default": 3},
                    "requires_lab": {"type": "boolean", "default": False},
                },
                "required": ["name", "code", "department"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_room",
            "description": "Add a classroom, lab, or seminar room.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_number": {"type": "string"},
                    "capacity": {"type": "integer", "default": 60},
                    "type": {"type": "string", "enum": ["classroom", "lab", "seminar"]},
                    "floor": {"type": "integer", "default": 1},
                    "building": {"type": "string", "default": "Main"},
                },
                "required": ["room_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_batch",
            "description": "Add a student batch/section.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "department": {"type": "string"},
                    "semester": {"type": "integer"},
                    "student_count": {"type": "integer", "default": 60},
                    "year": {"type": "integer"},
                },
                "required": ["name", "department", "semester", "year"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "assign_subject",
            "description": "Assign a subject to a faculty member for a batch.",
            "parameters": {
                "type": "object",
                "properties": {
                    "faculty_id": {"type": "integer"},
                    "subject_id": {"type": "integer"},
                    "batch_id": {"type": "integer"},
                    "semester": {"type": "integer"},
                },
                "required": ["faculty_id", "subject_id", "batch_id", "semester"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_timetable",
            "description": "Generate a conflict-free timetable for a semester and department.",
            "parameters": {
                "type": "object",
                "properties": {
                    "semester": {"type": "integer"},
                    "department": {"type": "string"},
                },
                "required": ["semester", "department"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_conflicts",
            "description": "Check a timetable for scheduling conflicts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timetable_id": {"type": "string"},
                },
                "required": ["timetable_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_faculty_schedule",
            "description": "Get the weekly schedule for a faculty member.",
            "parameters": {
                "type": "object",
                "properties": {
                    "faculty_id": {"type": "integer"},
                    "timetable_id": {"type": "string"},
                },
                "required": ["faculty_id", "timetable_id"],
            },
        },
    },
]


def _execute_tool(tool_name: str, args: Dict[str, Any], db: Session) -> str:
    """Execute a tool call and return a string result."""
    try:
        if tool_name == "add_faculty":
            from app.models.faculty import Faculty as FacultyModel

            existing = db.query(FacultyModel).filter(FacultyModel.email == args["email"]).first()
            if existing:
                return f"Faculty with email {args['email']} already exists (id={existing.id})."
            f = FacultyModel(
                name=args["name"],
                department=args["department"],
                email=args["email"],
                max_periods_per_day=args.get("max_periods_per_day", 5),
                unavailable_slots=args.get("unavailable_slots", []),
            )
            db.add(f)
            db.commit()
            db.refresh(f)
            return f"Faculty '{f.name}' added successfully with id={f.id}."

        elif tool_name == "add_subject":
            from app.models.subject import Subject as SubjectModel

            existing = db.query(SubjectModel).filter(SubjectModel.code == args["code"]).first()
            if existing:
                return f"Subject with code {args['code']} already exists (id={existing.id})."
            s = SubjectModel(
                name=args["name"],
                code=args["code"],
                department=args["department"],
                credits=args.get("credits", 3),
                periods_per_week=args.get("periods_per_week", 3),
                requires_lab=args.get("requires_lab", False),
            )
            db.add(s)
            db.commit()
            db.refresh(s)
            return f"Subject '{s.name}' (code={s.code}) added with id={s.id}."

        elif tool_name == "add_room":
            from app.models.room import Room as RoomModel

            existing = db.query(RoomModel).filter(RoomModel.room_number == args["room_number"]).first()
            if existing:
                return f"Room {args['room_number']} already exists (id={existing.id})."
            r = RoomModel(
                room_number=args["room_number"],
                capacity=args.get("capacity", 60),
                type=args.get("type", "classroom"),
                floor=args.get("floor", 1),
                building=args.get("building", "Main"),
            )
            db.add(r)
            db.commit()
            db.refresh(r)
            return f"Room '{r.room_number}' added with id={r.id}."

        elif tool_name == "add_batch":
            b = Batch(
                name=args["name"],
                department=args["department"],
                semester=args["semester"],
                student_count=args.get("student_count", 60),
                year=args["year"],
            )
            db.add(b)
            db.commit()
            db.refresh(b)
            return f"Batch '{b.name}' added with id={b.id}."

        elif tool_name == "assign_subject":
            existing = (
                db.query(Assignment)
                .filter(
                    Assignment.faculty_id == args["faculty_id"],
                    Assignment.subject_id == args["subject_id"],
                    Assignment.batch_id == args["batch_id"],
                )
                .first()
            )
            if existing:
                return "Assignment already exists."
            a = Assignment(
                faculty_id=args["faculty_id"],
                subject_id=args["subject_id"],
                batch_id=args["batch_id"],
                semester=args["semester"],
            )
            db.add(a)
            db.commit()
            return "Subject assigned successfully."

        elif tool_name == "generate_timetable":
            result = generate_timetable(db, args["semester"], args["department"])
            if result.get("conflicts"):
                return "Timetable generation failed: " + "; ".join(result["conflicts"])
            return (
                f"Timetable generated successfully. "
                f"Timetable ID: {result['timetable_id']}. "
                f"Generated {result.get('slots_count', '?')} slots for batches {result.get('batch_ids')}."
            )

        elif tool_name == "check_conflicts":
            conflicts = check_conflicts(db, args["timetable_id"])
            if not conflicts:
                return "No conflicts detected. The timetable is conflict-free."
            return "Conflicts found:\n" + "\n".join(f"- {c}" for c in conflicts)

        elif tool_name == "get_faculty_schedule":
            from app.models.timetable import TimetableSlot

            slots = (
                db.query(TimetableSlot)
                .filter(
                    TimetableSlot.timetable_id == args["timetable_id"],
                    TimetableSlot.faculty_id == args["faculty_id"],
                    TimetableSlot.slot_type == "class",
                )
                .order_by(TimetableSlot.day_of_week, TimetableSlot.period_number)
                .all()
            )
            if not slots:
                return "No schedule found for this faculty member in the given timetable."
            lines = ["| Day | Period | Subject | Room |", "|-----|--------|---------|------|"]
            for s in slots:
                subj = db.get(Subject, s.subject_id) if s.subject_id else None
                room = db.get(Room, s.room_id) if s.room_id else None
                lines.append(
                    f"| {s.day_of_week} | P{s.period_number} | "
                    f"{subj.name if subj else '?'} | "
                    f"{room.room_number if room else '?'} |"
                )
            return "\n".join(lines)

        else:
            return f"Unknown tool: {tool_name}"
    except Exception as e:
        logger.exception("Tool execution error")
        return f"Error executing {tool_name}: {str(e)}"


def run_agent(
    messages: List[Dict[str, str]],
    db: Session,
    stream: bool = False,
) -> Generator[str, None, None]:
    """
    Run the LLM agent with tool calling.
    Yields text chunks (for streaming) or a single final response.
    """
    if not settings.OPENAI_API_KEY or not settings.OPENAI_API_KEY.strip():
        yield "⚠️ No OPENAI_API_KEY configured. Please set it in your environment."
        return

    base_url = "https://integrate.api.nvidia.com/v1" if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("nvapi-") else None

    model_name = settings.LLM_MODEL
    if base_url and "nvidia" in base_url and model_name == "gpt-4o":
        model_name = "meta/llama-3.1-70b-instruct"

    llm = ChatOpenAI(
        model=model_name,
        temperature=settings.LLM_TEMPERATURE,
        openai_api_key=settings.OPENAI_API_KEY,
        base_url=base_url,
    )
    # Disable parallel tool calls to support models/endpoints that only allow one tool call at a time
    llm_with_tools = llm.bind_tools(TOOLS_SCHEMA, parallel_tool_calls=False)

    chat_messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "user":
            chat_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            chat_messages.append(AIMessage(content=content))

    # Agentic loop (max 15 tool rounds to allow for sequential bulk additions)
    for _ in range(15):
        response = llm_with_tools.invoke(chat_messages)
        tool_calls = getattr(response, "tool_calls", None) or []

        if not tool_calls:
            # No more tool calls — yield the final text
            yield response.content
            return

        # Execute tool calls and add results to messages
        chat_messages.append(response)
        for tc in tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_result = _execute_tool(tool_name, tool_args, db)
            from langchain_core.messages import ToolMessage
            chat_messages.append(
                ToolMessage(content=tool_result, tool_call_id=tc["id"])
            )

    # Fallback if loop exhausted
    final = llm_with_tools.invoke(chat_messages)
    yield final.content
