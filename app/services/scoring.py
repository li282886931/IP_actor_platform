"""Pure, deterministic normalization with full denominators and visible missing inputs."""


def score_model(metrics, criteria, maximum):
    total_weight = sum(c["weight"] for c in criteria)
    rows, missing = [], []
    for criterion in criteria:
        raw = metrics.get(criterion["metric"])
        points = None
        if raw is None:
            missing.append(criterion["metric"])
        else:
            normalized = min(1., max(0., (float(raw) - criterion["floor"]) /
                                     (criterion["ceiling"] - criterion["floor"])))
            if criterion["method"] == "linear_low":
                normalized = 1 - normalized
            points = normalized * criterion["max_score"]
        contribution = points / criterion["max_score"] * criterion["weight"] / total_weight * maximum if points is not None else None
        rows.append({**criterion, "raw_value": raw, "score": points, "contribution": contribution,
                     "formula": f"{'1−' if criterion['method'] == 'linear_low' else ''}clamp((值−{criterion['floor']})/({criterion['ceiling']}−{criterion['floor']}),0,1)×{criterion['max_score']}"})
    return dict(status="pending_configuration" if not criteria else "pending_input" if missing else "calculated",
                value=round(sum(r["contribution"] for r in rows), 2) if criteria and not missing else None,
                max=maximum, dimensions=rows, missing=missing)
