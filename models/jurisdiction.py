"""
Jurisdiction and Session data models.

Represents legislative jurisdictions (federal, states) and their sessions.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class Jurisdiction:
    """
    Represents a legislative jurisdiction (federal, state, territory).
    """
    id: Optional[int] = None
    name: Optional[str] = None  # 'United States', 'New York', 'California', etc.
    jurisdiction_type: Optional[str] = None  # 'federal', 'state', 'territory'
    
    # Identifiers
    state_code: Optional[str] = None  # Two-letter code: 'US', 'NY', 'CA', etc.
    fips_code: Optional[str] = None  # Federal Information Processing Standard code
    
    # Legislative structure
    legislature_name: Optional[str] = None  # 'Congress', 'Legislature', 'General Assembly'
    upper_chamber_name: Optional[str] = None  # 'Senate'
    lower_chamber_name: Optional[str] = None  # 'House of Representatives', 'Assembly'
    
    # OpenStates specific
    openstates_id: Optional[str] = None
    
    # Metadata
    inserted_at: Optional[datetime] = None
    
    # Raw data
    extras: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'jurisdiction_type': self.jurisdiction_type,
            'state_code': self.state_code,
            'fips_code': self.fips_code,
            'legislature_name': self.legislature_name,
            'upper_chamber_name': self.upper_chamber_name,
            'lower_chamber_name': self.lower_chamber_name,
            'openstates_id': self.openstates_id,
            'extras': self.extras,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Jurisdiction':
        """Create Jurisdiction from dictionary."""
        jurisdiction = cls()
        jurisdiction.id = data.get('id')
        jurisdiction.name = data.get('name')
        jurisdiction.jurisdiction_type = data.get('jurisdiction_type')
        jurisdiction.state_code = data.get('state_code')
        jurisdiction.fips_code = data.get('fips_code')
        jurisdiction.legislature_name = data.get('legislature_name')
        jurisdiction.upper_chamber_name = data.get('upper_chamber_name')
        jurisdiction.lower_chamber_name = data.get('lower_chamber_name')
        jurisdiction.openstates_id = data.get('openstates_id')
        jurisdiction.extras = data.get('extras', {})
        
        return jurisdiction


@dataclass
class Session:
    """
    Represents a legislative session within a jurisdiction.
    """
    id: Optional[int] = None
    jurisdiction_id: Optional[int] = None
    
    # Session identification
    identifier: Optional[str] = None  # '2023-2024', '118th', '2023 Regular'
    name: Optional[str] = None  # Human-readable name
    
    # Session type
    session_type: Optional[str] = None  # 'regular', 'special', 'extraordinary'
    
    # Dates
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Congress specific
    congress_number: Optional[int] = None  # For federal sessions
    
    # Metadata
    inserted_at: Optional[datetime] = None
    
    # Raw data
    extras: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'jurisdiction_id': self.jurisdiction_id,
            'identifier': self.identifier,
            'name': self.name,
            'session_type': self.session_type,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'congress_number': self.congress_number,
            'extras': self.extras,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Create Session from dictionary."""
        session = cls()
        session.id = data.get('id')
        session.jurisdiction_id = data.get('jurisdiction_id')
        session.identifier = data.get('identifier')
        session.name = data.get('name')
        session.session_type = data.get('session_type')
        
        if data.get('start_date'):
            if isinstance(data['start_date'], str):
                session.start_date = datetime.fromisoformat(data['start_date'])
            else:
                session.start_date = data['start_date']
        
        if data.get('end_date'):
            if isinstance(data['end_date'], str):
                session.end_date = datetime.fromisoformat(data['end_date'])
            else:
                session.end_date = data['end_date']
        
        session.congress_number = data.get('congress_number')
        session.extras = data.get('extras', {})
        
        return session
