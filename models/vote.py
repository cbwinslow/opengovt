"""
Vote data models.

Represents legislative votes and individual vote records.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Vote:
    """
    Represents a legislative vote event (roll call vote).
    
    Unified representation across OpenStates, Congress.gov, GovInfo.gov.
    """
    id: Optional[int] = None
    source: Optional[str] = None  # 'openstates', 'congress', 'govinfo'
    source_id: Optional[str] = None
    
    # Associated entities
    bill_id: Optional[int] = None
    jurisdiction_id: Optional[int] = None
    session_id: Optional[int] = None
    
    # Vote identification
    chamber: Optional[str] = None  # 'house', 'senate', 'upper', 'lower'
    vote_number: Optional[int] = None
    roll_call_number: Optional[int] = None
    
    # Vote details
    vote_date: Optional[datetime] = None
    motion: Optional[str] = None  # Description of what was voted on
    result: Optional[str] = None  # 'passed', 'failed', 'agreed to', 'rejected'
    vote_type: Optional[str] = None  # 'passage', 'procedural', 'amendment', 'veto override'
    
    # Vote counts
    yeas: Optional[int] = None
    nays: Optional[int] = None
    present: Optional[int] = None
    absent: Optional[int] = None
    not_voting: Optional[int] = None
    
    # Passage requirements
    required_for_passage: Optional[str] = None  # 'majority', '2/3', '3/5'
    
    # Metadata
    congress_number: Optional[int] = None  # For federal votes
    session_year: Optional[int] = None
    
    inserted_at: Optional[datetime] = None
    
    # Raw data
    extras: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'source': self.source,
            'source_id': self.source_id,
            'bill_id': self.bill_id,
            'jurisdiction_id': self.jurisdiction_id,
            'session_id': self.session_id,
            'chamber': self.chamber,
            'vote_number': self.vote_number,
            'roll_call_number': self.roll_call_number,
            'vote_date': self.vote_date.isoformat() if self.vote_date else None,
            'motion': self.motion,
            'result': self.result,
            'vote_type': self.vote_type,
            'yeas': self.yeas,
            'nays': self.nays,
            'present': self.present,
            'absent': self.absent,
            'not_voting': self.not_voting,
            'required_for_passage': self.required_for_passage,
            'congress_number': self.congress_number,
            'session_year': self.session_year,
            'extras': self.extras,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Vote':
        """Create Vote from dictionary."""
        vote = cls()
        vote.id = data.get('id')
        vote.source = data.get('source')
        vote.source_id = data.get('source_id')
        vote.bill_id = data.get('bill_id')
        vote.jurisdiction_id = data.get('jurisdiction_id')
        vote.session_id = data.get('session_id')
        vote.chamber = data.get('chamber')
        vote.vote_number = data.get('vote_number')
        vote.roll_call_number = data.get('roll_call_number')
        
        if data.get('vote_date'):
            if isinstance(data['vote_date'], str):
                vote.vote_date = datetime.fromisoformat(data['vote_date'])
            else:
                vote.vote_date = data['vote_date']
        
        vote.motion = data.get('motion')
        vote.result = data.get('result')
        vote.vote_type = data.get('vote_type')
        vote.yeas = data.get('yeas')
        vote.nays = data.get('nays')
        vote.present = data.get('present')
        vote.absent = data.get('absent')
        vote.not_voting = data.get('not_voting')
        vote.required_for_passage = data.get('required_for_passage')
        vote.congress_number = data.get('congress_number')
        vote.session_year = data.get('session_year')
        vote.extras = data.get('extras', {})
        
        return vote


@dataclass
class VoteRecord:
    """
    Represents an individual legislator's vote in a Vote event.
    """
    id: Optional[int] = None
    vote_id: Optional[int] = None
    person_id: Optional[int] = None
    
    # Vote choice
    vote_choice: Optional[str] = None  # 'yes', 'no', 'present', 'absent', 'not_voting'
    
    # Member information (denormalized for convenience)
    member_name: Optional[str] = None
    party: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    
    # Raw data
    extras: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'vote_id': self.vote_id,
            'person_id': self.person_id,
            'vote_choice': self.vote_choice,
            'member_name': self.member_name,
            'party': self.party,
            'state': self.state,
            'district': self.district,
            'extras': self.extras,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VoteRecord':
        """Create VoteRecord from dictionary."""
        record = cls()
        record.id = data.get('id')
        record.vote_id = data.get('vote_id')
        record.person_id = data.get('person_id')
        record.vote_choice = data.get('vote_choice')
        record.member_name = data.get('member_name')
        record.party = data.get('party')
        record.state = data.get('state')
        record.district = data.get('district')
        record.extras = data.get('extras', {})
        
        return record
