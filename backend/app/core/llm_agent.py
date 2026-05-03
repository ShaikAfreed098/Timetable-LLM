"""
LLM Agent powered by LangChain + OpenAI with tool/function calling.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Generator, List

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.core.scheduler import generate_timetable, check_conflicts
from app.models.subject import Subject
from app.models.room import Room
from app.models.batch import Batch
from app.models.timetable import Assignment

logger = logging.getLogger(__name__)

def get_system_prompt(config: dict) -> str:
    days_str = ", ".join(config["days"])
    periods_str = ", ".join(str(p) for p in config["periods"])
    period_times = config.get("period_times") or {}
    times_block = ""
    if period_times:
        lines = [f"  P{k}: {v}" for k, v in sorted(period_times.items(), key=lambda kv: int(kv[0]))]
        times_block = "\nPeriod times:\n" + "\n".join(lines)
    return f"""You are an intelligent timetable assistant for an educational institution.

The institution operates on the following days: {days_str}.
They have {len(config["periods"])} periods per day: {periods_str}.{times_block}

Available tools:
  - add_faculty, add_subject, add_room, add_batch
  - assign_subject
  - generate_timetable, check_conflicts, get_faculty_schedule

Guidelines:
- Confirm destructive actions before proceeding.
- Present timetables as formatted Markdown tables.
- If you lack information to call a tool, ask the user for the missing details.
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


def _execute_tool(tool_name: str, args: Dict[str, Any], db: Session, institution_id: int) -> str:
    """Execute a tool call and return a string result."""
    try:
        if tool_name == "add_faculty":
            from app.models.faculty import Faculty as FacultyModel

            existing = db.query(FacultyModel).filter(FacultyModel.email == args["email"], FacultyModel.institution_id == institution_id).first()
            if existing:
                return f"Faculty with email {args['email']} already exists (id={existing.id})."
            f = FacultyModel(
                institution_id=institution_id,
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

            existing = db.query(SubjectModel).filter(SubjectModel.code == args["code"], SubjectModel.institution_id == institution_id).first()
            if existing:
                return f"Subject with code {args['code']} already exists (id={existing.id})."
            s = SubjectModel(
                institution_id=institution_id,
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

            existing = db.query(RoomModel).filter(RoomModel.room_number == args["room_number"], RoomModel.institution_id == institution_id).first()
            if existing:
                return f"Room {args['room_number']} already exists (id={existing.id})."
            r = RoomModel(
                institution_id=institution_id,
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
                institution_id=institution_id,
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
                    Assignment.institution_id == institution_id,
                )
                .first()
            )
            if existing:
                return "Assignment already exists."
            a = Assignment(
                institution_id=institution_id,
                faculty_id=args["faculty_id"],
                subject_id=args["subject_id"],
                batch_id=args["batch_id"],
                semester=args["semester"],
            )
            db.add(a)
            db.commit()
            return "Subject assigned successfully."

        elif tool_name == "generate_timetable":
            result = generate_timetable(db, args["semester"], args["department"], institution_id)
            if result.get("conflicts"):
                return "Timetable generation failed: " + "; ".join(result["conflicts"])
            return (
                f"Timetable generated successfully. "
                f"Timetable ID: {result['timetable_id']}. "
                f"Generated {result.get('slots_count', '?')} slots for batches {result.get('batch_ids')}."
            )

        elif tool_name == "check_conflicts":
            conflicts = check_conflicts(db, args["timetable_id"], institution_id)
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
                    TimetableSlot.institution_id == institution_id,
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
    institution_id: int,
) -> Generator[str, None, None]:
    """
    Run the LLM agent with tool calling.
    Yields text chunks (for streaming) or a single final response.
    """
    api_key = settings.resolved_llm_api_key()
    if not api_key or not api_key.strip():
        yield "LLM is not configured. Set LLM_API_KEY in the server environment."
        return

    base_url = settings.resolved_llm_base_url()
    model_name = settings.LLM_MODEL
    if settings.LLM_PROVIDER == "nvidia" and model_name == "gpt-4o":
        model_name = "meta/llama-3.1-70b-instruct"

    llm = ChatOpenAI(
        model=model_name,
        temperature=settings.LLM_TEMPERATURE,
        openai_api_key=api_key,
        base_url=base_url,
    )
    llm_with_tools = llm.bind_tools(TOOLS_SCHEMA)

    from app.core.scheduler import get_institution_config
    config = get_institution_config(db, institution_id)
    dynamic_prompt = get_system_prompt(config)

    chat_messages = [SystemMessage(content=dynamic_prompt)]
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
            tool_result = _execute_tool(tool_name, tool_args, db, institution_id)
            from langchain_core.messages import ToolMessage
            chat_messages.append(
                ToolMessage(content=tool_result, tool_call_id=tc["id"])
            )

    # Fallback if loop exhausted
    final = llm_with_tools.invoke(chat_messages)
    yield final.content
