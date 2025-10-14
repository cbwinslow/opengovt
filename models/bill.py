"""
Bill data models.

Represents legislative bills, their actions, text versions, and sponsorships.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Bill:
    """
    Represents a legislative bill from any jurisdiction (federal or state).
    
    Unified representation across OpenStates, Congress.gov, GovInfo.gov.
    """
    id: Optional[int] = None
    source: Optional[str] = None  # 'openstates', 'congress', 'govinfo'
    source_id: Optional[str] = None
    
    # Jurisdiction and session
    jurisdiction_id: Optional[int] = None
    session_id: Optional[int] = None
    
    # Bill identification
    bill_number: Optional[str] = None  # 'HR1234', 'S456', 'AB789', etc.
    chamber: Optional[str] = None  # 'house', 'senate', 'upper', 'lower', 'assembly'
    
    # Bill content
    title: Optional[str] = None
    summary: Optional[str] = None
    official_title: Optional[str] = None
    short_title: Optional[str] = None
    
    # Status and dates
    status: Optional[str] = None  # 'introduced', 'passed', 'enacted', 'failed', etc.
    introduced_date: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Subject classification
    subjects: List[str] = field(default_factory=list)
    policy_areas: List[str] = field(default_factory=list)
    
    # Related bills
    companion_bill_ids: List[int] = field(default_factory=list)
    
    # Metadata
    congress_number: Optional[int] = None  # For federal bills
    bill_type: Optional[str] = None  # 'hr', 's', 'hjres', 'sjres', etc.
    
    inserted_at: Optional[datetime] = None
    
    # Raw data
    extras: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'source': self.source,
            'source_id': self.source_id,
            'jurisdiction_id': self.jurisdiction_id,
            'session_id': self.session_id,
            'bill_number': self.bill_number,
            'chamber': self.chamber,
            'title': self.title,
            'summary': self.summary,
            'official_title': self.official_title,
            'short_title': self.short_title,
            'status': self.status,
            'introduced_date': self.introduced_date.isoformat() if self.introduced_date else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'subjects': self.subjects,
            'policy_areas': self.policy_areas,
            'companion_bill_ids': self.companion_bill_ids,
            'congress_number': self.congress_number,
            'bill_type': self.bill_type,
            'extras': self.extras,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Bill':
        """Create Bill from dictionary."""
        bill = cls()
        bill.id = data.get('id')
        bill.source = data.get('source')
        bill.source_id = data.get('source_id')
        bill.jurisdiction_id = data.get('jurisdiction_id')
        bill.session_id = data.get('session_id')
        bill.bill_number = data.get('bill_number')
        bill.chamber = data.get('chamber')
        bill.title = data.get('title')
        bill.summary = data.get('summary')
        bill.official_title = data.get('official_title')
        bill.short_title = data.get('short_title')
        bill.status = data.get('status')
        
        if data.get('introduced_date'):
            if isinstance(data['introduced_date'], str):
                bill.introduced_date = datetime.fromisoformat(data['introduced_date'])
            else:
                bill.introduced_date = data['introduced_date']
        
        if data.get('updated_at'):
            if isinstance(data['updated_at'], str):
                bill.updated_at = datetime.fromisoformat(data['updated_at'])
            else:
                bill.updated_at = data['updated_at']
        
        bill.subjects = data.get('subjects', [])
        bill.policy_areas = data.get('policy_areas', [])
        bill.companion_bill_ids = data.get('companion_bill_ids', [])
        bill.congress_number = data.get('congress_number')
        bill.bill_type = data.get('bill_type')
        bill.extras = data.get('extras', {})
        
        return bill


@dataclass
class BillAction:
    """
    Represents an action taken on a bill (committee referral, floor vote, signing, etc.).
    """
    id: Optional[int] = None
    bill_id: Optional[int] = None
    
    action_date: Optional[datetime] = None
    description: Optional[str] = None
    action_type: Optional[str] = None  # 'introduction', 'referral', 'vote', 'signing', etc.
    
    # Action details
    chamber: Optional[str] = None
    committee: Optional[str] = None
    
    # Source data
    source_action_code: Optional[str] = None
    
    # Raw data
    extras: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'bill_id': self.bill_id,
            'action_date': self.action_date.isoformat() if self.action_date else None,
            'description': self.description,
            'action_type': self.action_type,
            'chamber': self.chamber,
            'committee': self.committee,
            'source_action_code': self.source_action_code,
            'extras': self.extras,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BillAction':
        """Create BillAction from dictionary."""
        action = cls()
        action.id = data.get('id')
        action.bill_id = data.get('bill_id')
        
        if data.get('action_date'):
            if isinstance(data['action_date'], str):
                action.action_date = datetime.fromisoformat(data['action_date'])
            else:
                action.action_date = data['action_date']
        
        action.description = data.get('description')
        action.action_type = data.get('action_type')
        action.chamber = data.get('chamber')
        action.committee = data.get('committee')
        action.source_action_code = data.get('source_action_code')
        action.extras = data.get('extras', {})
        
        return action


@dataclass
class BillText:
    """
    Represents a version of bill text (introduced, engrossed, enrolled, etc.).
    """
    id: Optional[int] = None
    bill_id: Optional[int] = None
    
    text_type: Optional[str] = None  # 'Introduced', 'Engrossed', 'Enrolled', 'Reported', etc.
    text_url: Optional[str] = None
    content: Optional[str] = None  # Full text content
    
    # Format information
    format: Optional[str] = None  # 'xml', 'html', 'pdf', 'txt'
    
    # Date information
    version_date: Optional[datetime] = None
    
    # Raw data
    extras: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'bill_id': self.bill_id,
            'text_type': self.text_type,
            'text_url': self.text_url,
            'content': self.content,
            'format': self.format,
            'version_date': self.version_date.isoformat() if self.version_date else None,
            'extras': self.extras,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BillText':
        """Create BillText from dictionary."""
        text = cls()
        text.id = data.get('id')
        text.bill_id = data.get('bill_id')
        text.text_type = data.get('text_type')
        text.text_url = data.get('text_url')
        text.content = data.get('content')
        text.format = data.get('format')
        
        if data.get('version_date'):
            if isinstance(data['version_date'], str):
                text.version_date = datetime.fromisoformat(data['version_date'])
            else:
                text.version_date = data['version_date']
        
        text.extras = data.get('extras', {})
        
        return text


@dataclass
class BillSponsorship:
    """
    Represents a person's sponsorship of a bill (primary sponsor or cosponsor).
    """
    id: Optional[int] = None
    bill_id: Optional[int] = None
    person_id: Optional[int] = None
    
    # Sponsorship details
    name: Optional[str] = None  # Name as listed on bill
    role: Optional[str] = None  # 'primary', 'cosponsor', 'original_cosponsor'
    sponsor_order: Optional[int] = None  # Order in which cosponsor was added
    
    # Dates
    sponsored_date: Optional[datetime] = None
    withdrawn_date: Optional[datetime] = None
    
    # Raw data
    extras: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'bill_id': self.bill_id,
            'person_id': self.person_id,
            'name': self.name,
            'role': self.role,
            'sponsor_order': self.sponsor_order,
            'sponsored_date': self.sponsored_date.isoformat() if self.sponsored_date else None,
            'withdrawn_date': self.withdrawn_date.isoformat() if self.withdrawn_date else None,
            'extras': self.extras,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BillSponsorship':
        """Create BillSponsorship from dictionary."""
        sponsorship = cls()
        sponsorship.id = data.get('id')
        sponsorship.bill_id = data.get('bill_id')
        sponsorship.person_id = data.get('person_id')
        sponsorship.name = data.get('name')
        sponsorship.role = data.get('role')
        sponsorship.sponsor_order = data.get('sponsor_order')
        
        if data.get('sponsored_date'):
            if isinstance(data['sponsored_date'], str):
                sponsorship.sponsored_date = datetime.fromisoformat(data['sponsored_date'])
            else:
                sponsorship.sponsored_date = data['sponsored_date']
        
        if data.get('withdrawn_date'):
            if isinstance(data['withdrawn_date'], str):
                sponsorship.withdrawn_date = datetime.fromisoformat(data['withdrawn_date'])
            else:
                sponsorship.withdrawn_date = data['withdrawn_date']
        
        sponsorship.extras = data.get('extras', {})
        
        return sponsorship
