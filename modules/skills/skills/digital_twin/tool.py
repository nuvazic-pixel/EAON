from dataclasses import dataclass


@dataclass
class TwinAsset:
    asset_id: str
    asset_type: str
    status: str
    geometry_ref: str | None = None
    parent_id: str | None = None


def create_ftth_asset_schema() -> dict:
    return {
        'asset_id': 'unique string',
        'asset_type': 'nvt | trench | hdd | crossing | house_connection | asphalt_patch',
        'status': 'planned | in_progress | blocked | completed | inspected',
        'geometry': 'Point | LineString | Polygon',
        'address': 'optional string',
        'crew': 'optional string',
        'last_update': 'ISO datetime',
        'risk_level': 'low | medium | high',
        'notes': 'free text',
    }


def suggest_dashboard_cards() -> list[str]:
    return [
        'Blocked segments',
        'Open asphalt reinstatements',
        'Crew progress today',
        'High-risk crossings',
        'Missing documentation photos',
        'Material bottlenecks',
    ]
