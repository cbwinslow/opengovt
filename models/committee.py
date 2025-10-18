"""
Committee data models.

Represents legislative committees and memberships.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Committee:
    """
    Represents a legislative committee or subcommittee.
    """
    id: Optional[int] = None
    source: Optional[str] = None  # 'openstates', 'congress'
    source_id: Optional[str] = None
    
    # Committee identification
    jurisdiction_id: Optional[int] = None
    chamber: Optional[str] = None  # 'house', 'senate', 'joint', 'upper', 'lower'
    name: Optional[str] = None
    
    # Committee hierarchy
    parent_id: Optional[int] = None  # For subcommittees
    is_subcommittee: bool = False
    
    # Committee details
    committee_type: Optional[str] = None  # 'standing', 'select', 'special', 'joint'
    thomas_id: Optional[str] = None  # Federal committee ID
    
    # Metadata
    inserted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Raw data
    extras: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'source': self.source,
            'source_id': self.source_id,
            'jurisdiction_id': self.jurisdiction_id,
            'chamber': self.chamber,
            'name': self.name,
            'parent_id': self.parent_id,
            'is_subcommittee': self.is_subcommittee,
            'committee_type': self.committee_type,
            'thomas_id': self.thomas_id,
            'extras': self.extras,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Committee':
        """Create Committee from dictionary."""
        committee = cls()
        committee.id = data.get('id')
        committee.source = data.get('source')
        committee.source_id = data.get('source_id')
        committee.jurisdiction_id = data.get('jurisdiction_id')
        committee.chamber = data.get('chamber')
        committee.name = data.get('name')
        committee.parent_id = data.get('parent_id')
        committee.is_subcommittee = data.get('is_subcommittee', False)
        committee.committee_type = data.get('committee_type')
        committee.thomas_id = data.get('thomas_id')
        committee.extras = data.get('extras', {})
        
        return committee


@dataclass
class CommitteeMembership:
    """
    Represents a person's membership on a committee.
    """
    id: Optional[int] = None
    committee_id: Optional[int] = None
    person_id: Optional[int] = None
    
    # Role on committee
    role: Optional[str] = None  # 'chair', 'vice_chair', 'ranking_member', 'member'
    
    # Term dates
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Raw data
    extras: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'committee_id': self.committee_id,
            'person_id': self.person_id,
            'role': self.role,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'extras': self.extras,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommitteeMembership':
        """Create CommitteeMembership from dictionary."""
        membership = cls()
        membership.id = data.get('id')
        membership.committee_id = data.get('committee_id')
        membership.person_id = data.get('person_id')
        membership.role = data.get('role')
        
        if data.get('start_date'):
            if isinstance(data['start_date'], str):
                membership.start_date = datetime.fromisoformat(data['start_date'])
            else:
                membership.start_date = data['start_date']
        
        if data.get('end_date'):
            if isinstance(data['end_date'], str):
                membership.end_date = datetime.fromisoformat(data['end_date'])
            else:
                membership.end_date = data['end_date']
        
        membership.extras = data.get('extras', {})
        
        return membership
