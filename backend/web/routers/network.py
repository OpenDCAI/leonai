"""Network graph API — returns nodes + edges for the relationship graph."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from backend.web.core.dependencies import get_app, get_current_member_id

router = APIRouter(prefix="/api/network", tags=["network"])


@router.get("/graph")
async def get_graph(
    app: Annotated[Any, Depends(get_app)],
    _member_id: Annotated[str, Depends(get_current_member_id)],
) -> dict:
    member_repo = getattr(app.state, "member_repo", None)
    conv_member_repo = getattr(app.state, "conv_member_repo", None)
    if member_repo is None or conv_member_repo is None:
        raise HTTPException(500, "Repos not initialized")

    members = member_repo.list_all()
    edges_raw = conv_member_repo.list_all_edges()

    # Only include members that appear in at least one edge
    connected_ids = set()
    for src, tgt, _ in edges_raw:
        connected_ids.add(src)
        connected_ids.add(tgt)

    nodes = [
        {"id": m.id, "name": m.name, "type": m.type.value}
        for m in members
        if m.id in connected_ids
    ]
    edges = [
        {"source": src, "target": tgt, "weight": w}
        for src, tgt, w in edges_raw
    ]

    return {"nodes": nodes, "edges": edges}
