"""Small, explicit projections for organizational and personal workspace data."""
from fastapi import HTTPException
from app.models import CollaborationItem, Evidence, Fact, Gate, Notification, Project, Risk, Task, User
from app.services.collaboration import item_access
from app.services.serializers import serialize_task


def personal_summary(db, context):
    task_rows = db.query(Task, Project.name).join(Project, Task.project_id == Project.id).filter(
        Project.tenant_id == context.tenant.id, Task.assignee_id == context.user.id,
    ).order_by(Task.id.desc()).all()
    notices = db.query(Notification).filter(
        Notification.tenant_id == context.tenant.id, Notification.user_id == context.user.id,
    ).order_by(Notification.id.desc()).all()
    task_ids = [task.id for task, _ in task_rows]
    linked = {item.task_id: item for item in db.query(CollaborationItem).filter(
        CollaborationItem.tenant_id == context.tenant.id, CollaborationItem.task_id.in_(task_ids),
    )} if task_ids else {}
    tasks = []
    for task, name in task_rows:
        item = linked.get(task.id)
        if item:
            try:
                item_access(db, context, item.id)
            except HTTPException:
                continue
        record = serialize_task(task, project_name=name, assignee_name=context.user.name)
        if item:
            reviewer = db.get(User, item.owner_id)
            record.update(collaboration_item_id=item.id, reviewer_name=reviewer.name,
                          next_user_name=reviewer.name if task.status == "submitted"
                          else None if task.status in {"accepted", "cancelled", "completed"} else context.user.name)
        tasks.append(record)
    return {
        "user_id": context.user.id,
        "tasks": tasks,
        "notifications": [{"id": n.id, "title": n.title, "content": n.content,
                           "status": n.status} for n in notices],
        "pending_tasks": sum(t["status"] not in ('accepted', 'completed', 'cancelled') for t in tasks),
        "unread_notifications": sum(n.status == 'unread' for n in notices),
    }


def project_reviews(db, tenant_id):
    projects = db.query(Project).filter(Project.tenant_id == tenant_id).order_by(Project.id.desc()).all()
    ids = [p.id for p in projects]
    grouped = {p.id: {"risks": [], "gates": [], "facts": [], "evidence": {"total": 0, "pending": 0}} for p in projects}
    if ids:
        for row in db.query(Risk).filter(Risk.project_id.in_(ids)).all():
            grouped[row.project_id]["risks"].append({"id": row.id, "title": row.title, "level": row.level,
                                                     "status": row.status, "mitigation": row.mitigation})
        for row in db.query(Gate).filter(Gate.project_id.in_(ids)).all():
            grouped[row.project_id]["gates"].append({"id": row.id, "name": row.name, "status": row.status,
                                                     "required_evidence": row.required_evidence, "owner_group": row.owner_group})
        for row in db.query(Fact).filter(Fact.project_id.in_(ids)).all():
            # Titles and provenance only: raw content may contain finance or contacts.
            grouped[row.project_id]["facts"].append({"id": row.id, "title": row.title, "source": row.source, "status": row.status})
        for row in db.query(Evidence).filter(Evidence.project_id.in_(ids)).all():
            counts = grouped[row.project_id]["evidence"]
            counts["total"] += 1
            counts["pending"] += int(row.status != 'verified')
    return [{
        "id": p.id, "name": p.name, "city": p.city, "artist_id": p.artist_id, "artist_name": p.artist_name,
        "venue": p.venue, "venue_id": p.venue_id, "schedule": p.schedule, "status": p.status,
        **grouped[p.id],
    } for p in projects]
