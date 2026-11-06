import math


def project_input_snapshot(project):
    return {
        "name": project.name,
        "type": project.type,
        "artist_id": project.artist_id,
        "artist_name": project.artist_name,
        "city": project.city,
        "venue_id": project.venue_id,
        "venue": project.venue,
        "source_project_id": project.source_project_id,
        "schedule": project.schedule,
        "expected_attendance": project.expected_attendance,
        "avg_ticket_price": project.avg_ticket_price,
        "artist_fee": project.artist_fee,
        "venue_cost": project.venue_cost,
        "marketing_cost": project.marketing_cost,
        "production_cost": project.production_cost,
        "available_funds": project.available_funds,
        "venue_capacity": project.venue_capacity,
        "ticket_tiers": project.ticket_tiers or [],
        "conservative_occupancy_rate": project.conservative_occupancy_rate,
        "neutral_occupancy_rate": project.neutral_occupancy_rate,
        "optimistic_occupancy_rate": project.optimistic_occupancy_rate,
    }


def calculate_finance_result(payload):
    attendance = payload.expected_attendance
    ticket_price = payload.avg_ticket_price
    costs = [
        payload.artist_fee,
        payload.venue_cost,
        payload.marketing_cost,
        payload.production_cost,
    ]
    missing = []
    if attendance is None:
        missing.append('expected_attendance')
    if ticket_price is None:
        missing.append('avg_ticket_price')
    for key, value in [
        ('artist_fee', payload.artist_fee),
        ('venue_cost', payload.venue_cost),
        ('marketing_cost', payload.marketing_cost),
        ('production_cost', payload.production_cost),
    ]:
        if value is None:
            missing.append(key)

    if missing:
        return {
            "formula_version": "finance-v1",
            "status": "pending_input",
            "missing_fields": missing,
            "scenarios": {},
            "breakeven_attendance": None,
            "total_cost": None,
        }

    total_cost = sum(costs)
    scenarios = {}
    for key, factor in [('conservative', 0.8), ('neutral', 1), ('optimistic', 1.2)]:
        scenario_attendance = round(attendance * factor)
        revenue = scenario_attendance * ticket_price
        scenarios[key] = {
            "attendance": scenario_attendance,
            "revenue": revenue,
            "cost": total_cost,
            "profit": revenue - total_cost,
        }

    return {
        "formula_version": "finance-v1",
        "status": "calculated",
        "missing_fields": [],
        "scenarios": scenarios,
        "breakeven_attendance": math.ceil(total_cost / ticket_price) if ticket_price else None,
        "total_cost": total_cost,
    }


def calculate_breakeven_result(project, payload):
    ticket_price = payload.avg_ticket_price or project.avg_ticket_price
    cost_values = {
        "artist_fee": payload.artist_fee if payload.artist_fee is not None else project.artist_fee,
        "venue_cost": payload.venue_cost if payload.venue_cost is not None else project.venue_cost,
        "marketing_cost": payload.marketing_cost if payload.marketing_cost is not None else project.marketing_cost,
        "production_cost": payload.production_cost if payload.production_cost is not None else project.production_cost,
    }
    missing = [key for key, value in cost_values.items() if value is None]
    if ticket_price is None:
        missing.append("avg_ticket_price")
    if missing:
        return {
            "formula_version": "breakeven-v1",
            "status": "pending_input",
            "missing_fields": missing,
            "total_cost": None,
            "avg_ticket_price": ticket_price,
            "breakeven_attendance": None,
            "target_profit_attendance": None,
        }
    total_cost = sum(cost_values.values())
    target_profit = payload.target_profit or 0
    return {
        "formula_version": "breakeven-v1",
        "status": "calculated",
        "missing_fields": [],
        "total_cost": total_cost,
        "avg_ticket_price": ticket_price,
        "breakeven_attendance": math.ceil(total_cost / ticket_price) if ticket_price else None,
        "target_profit_attendance": math.ceil((total_cost + target_profit) / ticket_price) if ticket_price else None,
    }


def calculate_show_result(project, payload):
    field_values = {
        "venue_capacity": payload.venue_capacity if payload.venue_capacity is not None else project.venue_capacity,
        "expected_attendance": payload.expected_attendance if payload.expected_attendance is not None else project.expected_attendance,
        "avg_ticket_price": payload.avg_ticket_price if payload.avg_ticket_price is not None else project.avg_ticket_price,
        "artist_fee": payload.artist_fee if payload.artist_fee is not None else project.artist_fee,
        "venue_cost": payload.venue_cost if payload.venue_cost is not None else project.venue_cost,
        "marketing_cost": payload.marketing_cost if payload.marketing_cost is not None else project.marketing_cost,
        "production_cost": payload.production_cost if payload.production_cost is not None else project.production_cost,
        "security_cost": payload.security_cost,
        "travel_cost": payload.travel_cost,
        "accommodation_cost": payload.accommodation_cost,
        "insurance_cost": payload.insurance_cost,
        "approval_cost": payload.approval_cost,
        "contingency_cost": payload.contingency_cost,
    }
    required_fields = [
        "venue_capacity",
        "expected_attendance",
        "avg_ticket_price",
        "artist_fee",
        "venue_cost",
        "marketing_cost",
        "production_cost",
        "security_cost",
        "travel_cost",
        "accommodation_cost",
        "insurance_cost",
        "approval_cost",
        "contingency_cost",
    ]
    missing = [field for field in required_fields if field_values.get(field) is None]
    if missing:
        return {
            "formula_version": "show-calculation-v1",
            "status": "pending_input",
            "missing_fields": missing,
            "total_cost": None,
            "non_ticket_income": None,
            "net_ticket_revenue": None,
            "total_revenue": None,
            "net_profit": None,
            "profit_margin": None,
            "breakeven_attendance": None,
            "breakeven_occupancy_rate": None,
            "funding_gap": None,
            "recommended_min_ticket_price": None,
            "recommended_target_ticket_price": None,
            "scenarios": {},
        }

    total_cost = sum(field_values[field] for field in [
        "artist_fee",
        "venue_cost",
        "marketing_cost",
        "production_cost",
        "security_cost",
        "travel_cost",
        "accommodation_cost",
        "insurance_cost",
        "approval_cost",
        "contingency_cost",
    ])
    fee_rate = (payload.tax_fee_rate or 0) + (payload.ticketing_fee_rate or 0)
    net_rate = max(1 - fee_rate, 0)
    non_ticket_income = (payload.sponsorship_income or 0) + (payload.merchandise_income or 0)
    attendance = field_values["expected_attendance"]
    ticket_price = field_values["avg_ticket_price"]
    venue_capacity = field_values["venue_capacity"]
    net_ticket_revenue = round(attendance * ticket_price * net_rate)
    total_revenue = net_ticket_revenue + non_ticket_income
    net_profit = total_revenue - total_cost
    breakeven_attendance = math.ceil((total_cost - non_ticket_income) / (ticket_price * net_rate)) if ticket_price and net_rate else None
    target_profit = payload.target_profit or 0
    recommended_min_ticket_price = math.ceil((total_cost - non_ticket_income) / (attendance * net_rate)) if attendance and net_rate else None
    recommended_target_ticket_price = math.ceil((total_cost + target_profit - non_ticket_income) / (attendance * net_rate)) if attendance and net_rate else None

    scenarios = {}
    for key, rate in [
        ("conservative", payload.conservative_occupancy_rate or 60),
        ("neutral", payload.neutral_occupancy_rate or 80),
        ("optimistic", payload.optimistic_occupancy_rate or 95),
    ]:
        scenario_attendance = round(venue_capacity * rate / 100)
        scenario_net_ticket_revenue = round(scenario_attendance * ticket_price * net_rate)
        scenario_total_revenue = scenario_net_ticket_revenue + non_ticket_income
        scenarios[key] = {
            "occupancy_rate": rate,
            "attendance": scenario_attendance,
            "net_ticket_revenue": scenario_net_ticket_revenue,
            "total_revenue": scenario_total_revenue,
            "cost": total_cost,
            "profit": scenario_total_revenue - total_cost,
        }

    return {
        "formula_version": "show-calculation-v1",
        "status": "calculated",
        "missing_fields": [],
        "total_cost": total_cost,
        "non_ticket_income": non_ticket_income,
        "net_ticket_revenue": net_ticket_revenue,
        "total_revenue": total_revenue,
        "net_profit": net_profit,
        "profit_margin": round(net_profit / total_revenue, 4) if total_revenue else None,
        "breakeven_attendance": breakeven_attendance,
        "breakeven_occupancy_rate": round(breakeven_attendance / venue_capacity, 4) if breakeven_attendance and venue_capacity else None,
        "funding_gap": max(total_cost - (project.available_funds or 0), 0),
        "recommended_min_ticket_price": recommended_min_ticket_price,
        "recommended_target_ticket_price": recommended_target_ticket_price,
        "scenarios": scenarios,
    }
