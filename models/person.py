"""
Person and Member data models.

Represents legislators, politicians, and their roles across federal and state jurisdictions.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import date, datetime


@dataclass
class Person:
    """
    Represents a person (legislator/politician) with biographical information.
    
    This is the canonical representation that unifies data from multiple sources
    (OpenStates, Congress.gov, GovInfo.gov, theunitedstates.io).
    """
    id: Optional[int] = None
    source: Optional[str] = None  # 'openstates', 'congress', 'govinfo', 'theunitedstates'
    source_id: Optional[str] = None
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    sort_name: Optional[str] = None
    birth_date: Optional[date] = None
    death_date: Optional[date] = None
    
    # Identifiers across systems
    bioguide_id: Optional[str] = None  # Federal bioguide ID
    openstates_id: Optional[str] = None  # OpenStates person ID
    thomas_id: Optional[str] = None  # Legacy THOMAS ID
    govtrack_id: Optional[str] = None  # GovTrack ID
    
    # Additional biographical info
    gender: Optional[str] = None
    image_url: Optional[str] = None
    
    # Contact information
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    
    # Social media
    twitter: Optional[str] = None
    facebook: Optional[str] = None
    youtube: Optional[str] = None
    
    # Metadata
    inserted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Raw data from source
    extras: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'source': self.source,
            'source_id': self.source_id,
            'name': self.name,
            'given_name': self.given_name,
            'family_name': self.family_name,
            'sort_name': self.sort_name,
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'death_date': self.death_date.isoformat() if self.death_date else None,
            'bioguide_id': self.bioguide_id,
            'openstates_id': self.openstates_id,
            'thomas_id': self.thomas_id,
            'govtrack_id': self.govtrack_id,
            'gender': self.gender,
            'image_url': self.image_url,
            'email': self.email,
            'phone': self.phone,
            'website': self.website,
            'twitter': self.twitter,
            'facebook': self.facebook,
            'youtube': self.youtube,
            'extras': self.extras,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Person':
        """Create Person from dictionary."""
        person = cls()
        person.id = data.get('id')
        person.source = data.get('source')
        person.source_id = data.get('source_id')
        person.name = data.get('name')
        person.given_name = data.get('given_name')
        person.family_name = data.get('family_name')
        person.sort_name = data.get('sort_name')
        
        if data.get('birth_date'):
            if isinstance(data['birth_date'], str):
                person.birth_date = date.fromisoformat(data['birth_date'])
            else:
                person.birth_date = data['birth_date']
        
        if data.get('death_date'):
            if isinstance(data['death_date'], str):
                person.death_date = date.fromisoformat(data['death_date'])
            else:
                person.death_date = data['death_date']
        
        person.bioguide_id = data.get('bioguide_id')
        person.openstates_id = data.get('openstates_id')
        person.thomas_id = data.get('thomas_id')
        person.govtrack_id = data.get('govtrack_id')
        person.gender = data.get('gender')
        person.image_url = data.get('image_url')
        person.email = data.get('email')
        person.phone = data.get('phone')
        person.website = data.get('website')
        person.twitter = data.get('twitter')
        person.facebook = data.get('facebook')
        person.youtube = data.get('youtube')
        person.extras = data.get('extras', {})
        
        return person


@dataclass
class Member:
    """
    Represents a person's membership/role in a legislative body.
    
    A person can have multiple memberships (different terms, roles, jurisdictions).
    """
    id: Optional[int] = None
    person_id: Optional[int] = None
    jurisdiction_id: Optional[int] = None
    
    # Role details
    chamber: Optional[str] = None  # 'upper', 'lower', 'house', 'senate', 'assembly'
    role: Optional[str] = None  # 'Senator', 'Representative', 'Assembly Member', etc.
    district: Optional[str] = None  # District number or 'At-Large'
    
    # Party and location
    current_party: Optional[str] = None  # 'Democrat', 'Republican', 'Independent', etc.
    state: Optional[str] = None  # Two-letter state code
    
    # Term dates
    term_start: Optional[datetime] = None
    term_end: Optional[datetime] = None
    
    # Source information
    source: Optional[str] = None
    source_id: Optional[str] = None
    
    # Office information
    office_address: Optional[str] = None
    office_phone: Optional[str] = None
    
    # Leadership roles
    leadership_role: Optional[str] = None  # 'Speaker', 'Majority Leader', etc.
    
    # Committee assignments (list of committee IDs)
    committee_ids: List[int] = field(default_factory=list)
    
    # Metadata
    inserted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Raw data
    extras: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'person_id': self.person_id,
            'jurisdiction_id': self.jurisdiction_id,
            'chamber': self.chamber,
            'role': self.role,
            'district': self.district,
            'current_party': self.current_party,
            'state': self.state,
            'term_start': self.term_start.isoformat() if self.term_start else None,
            'term_end': self.term_end.isoformat() if self.term_end else None,
            'source': self.source,
            'source_id': self.source_id,
            'office_address': self.office_address,
            'office_phone': self.office_phone,
            'leadership_role': self.leadership_role,
            'committee_ids': self.committee_ids,
            'extras': self.extras,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Member':
        """Create Member from dictionary."""
        member = cls()
        member.id = data.get('id')
        member.person_id = data.get('person_id')
        member.jurisdiction_id = data.get('jurisdiction_id')
        member.chamber = data.get('chamber')
        member.role = data.get('role')
        member.district = data.get('district')
        member.current_party = data.get('current_party')
        member.state = data.get('state')
        
        if data.get('term_start'):
            if isinstance(data['term_start'], str):
                member.term_start = datetime.fromisoformat(data['term_start'])
            else:
                member.term_start = data['term_start']
        
        if data.get('term_end'):
            if isinstance(data['term_end'], str):
                member.term_end = datetime.fromisoformat(data['term_end'])
            else:
                member.term_end = data['term_end']
        
        member.source = data.get('source')
        member.source_id = data.get('source_id')
        member.office_address = data.get('office_address')
        member.office_phone = data.get('office_phone')
        member.leadership_role = data.get('leadership_role')
        member.committee_ids = data.get('committee_ids', [])
        member.extras = data.get('extras', {})
        
        return member
