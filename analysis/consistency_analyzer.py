"""
Consistency analyzer for voting records and political positions.

Analyzes voting consistency, position changes over time, and alignment
with stated positions for politicians.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class ConsistencyScore:
    """
    Represents consistency analysis results for a politician.
    """
    person_id: int
    analysis_period_start: Optional[datetime] = None
    analysis_period_end: Optional[datetime] = None
    
    # Voting consistency scores
    overall_consistency: Optional[float] = None  # 0 to 1
    party_line_voting: Optional[float] = None  # % votes with party
    issue_consistency: Dict[str, float] = field(default_factory=dict)  # By topic/issue
    
    # Position changes
    position_changes: List[Dict[str, Any]] = field(default_factory=list)
    flip_flops: List[Dict[str, Any]] = field(default_factory=list)
    
    # Cosponsorship analysis
    bipartisan_score: Optional[float] = None  # % bipartisan bill support
    
    # Alignment with stated positions
    campaign_alignment: Optional[float] = None
    
    # Metadata
    analyzed_at: Optional[datetime] = None
    total_votes_analyzed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'person_id': self.person_id,
            'analysis_period_start': self.analysis_period_start.isoformat() if self.analysis_period_start else None,
            'analysis_period_end': self.analysis_period_end.isoformat() if self.analysis_period_end else None,
            'overall_consistency': self.overall_consistency,
            'party_line_voting': self.party_line_voting,
            'issue_consistency': self.issue_consistency,
            'position_changes': self.position_changes,
            'flip_flops': self.flip_flops,
            'bipartisan_score': self.bipartisan_score,
            'campaign_alignment': self.campaign_alignment,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'total_votes_analyzed': self.total_votes_analyzed,
            'metadata': self.metadata,
        }


@dataclass
class VoteRecord:
    """
    Simplified vote record for consistency analysis.
    """
    vote_id: int
    bill_id: int
    person_id: int
    vote_choice: str  # 'yes', 'no', 'present', 'absent'
    vote_date: datetime
    bill_subject: Optional[str] = None
    party_position: Optional[str] = None  # What the party voted
    bill_title: Optional[str] = None


class ConsistencyAnalyzer:
    """
    Analyzer for voting consistency and position tracking.
    """
    
    def __init__(self):
        """Initialize consistency analyzer."""
        pass
    
    def analyze_voting_consistency(
        self,
        person_id: int,
        votes: List[VoteRecord],
        party: str = None,
    ) -> ConsistencyScore:
        """
        Analyze voting consistency for a person.
        
        Args:
            person_id: ID of the person to analyze
            votes: List of vote records
            party: Person's party affiliation
            
        Returns:
            ConsistencyScore object
        """
        if not votes:
            logger.warning(f"No votes provided for person {person_id}")
            return ConsistencyScore(
                person_id=person_id,
                analyzed_at=datetime.utcnow(),
            )
        
        # Sort votes by date
        votes = sorted(votes, key=lambda v: v.vote_date)
        
        # Calculate party line voting
        party_line_votes = 0
        party_votes_total = 0
        
        for vote in votes:
            if vote.party_position:
                party_votes_total += 1
                if vote.vote_choice == vote.party_position:
                    party_line_votes += 1
        
        party_line_voting = party_line_votes / party_votes_total if party_votes_total > 0 else None
        
        # Calculate issue consistency
        issue_consistency = self._calculate_issue_consistency(votes)
        
        # Detect position changes and flip-flops
        position_changes, flip_flops = self._detect_position_changes(votes)
        
        # Calculate overall consistency (based on various factors)
        consistency_factors = []
        if party_line_voting is not None:
            consistency_factors.append(party_line_voting)
        if issue_consistency:
            consistency_factors.extend(issue_consistency.values())
        
        overall_consistency = sum(consistency_factors) / len(consistency_factors) if consistency_factors else None
        
        return ConsistencyScore(
            person_id=person_id,
            analysis_period_start=votes[0].vote_date,
            analysis_period_end=votes[-1].vote_date,
            overall_consistency=overall_consistency,
            party_line_voting=party_line_voting,
            issue_consistency=issue_consistency,
            position_changes=position_changes,
            flip_flops=flip_flops,
            analyzed_at=datetime.utcnow(),
            total_votes_analyzed=len(votes),
            metadata={
                'party_line_votes': party_line_votes,
                'party_votes_total': party_votes_total,
            },
        )
    
    def _calculate_issue_consistency(self, votes: List[VoteRecord]) -> Dict[str, float]:
        """
        Calculate consistency within specific issue areas.
        
        Args:
            votes: List of vote records
            
        Returns:
            Dictionary mapping issue to consistency score
        """
        # Group votes by subject/issue
        issue_votes = {}
        for vote in votes:
            subject = vote.bill_subject or 'unknown'
            if subject not in issue_votes:
                issue_votes[subject] = []
            issue_votes[subject].append(vote)
        
        # Calculate consistency per issue
        issue_consistency = {}
        for issue, issue_vote_list in issue_votes.items():
            if len(issue_vote_list) < 2:
                continue
            
            # Count yes vs no votes
            vote_choices = [v.vote_choice for v in issue_vote_list if v.vote_choice in ['yes', 'no']]
            if not vote_choices:
                continue
            
            # Consistency = proportion of majority position
            counter = Counter(vote_choices)
            majority_count = counter.most_common(1)[0][1]
            consistency = majority_count / len(vote_choices)
            
            issue_consistency[issue] = consistency
        
        return issue_consistency
    
    def _detect_position_changes(
        self,
        votes: List[VoteRecord],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Detect position changes and flip-flops on similar bills.
        
        Args:
            votes: List of vote records
            
        Returns:
            Tuple of (position_changes, flip_flops)
        """
        position_changes = []
        flip_flops = []
        
        # Group votes by bill subject
        subject_votes = {}
        for vote in votes:
            subject = vote.bill_subject or 'unknown'
            if subject not in subject_votes:
                subject_votes[subject] = []
            subject_votes[subject].append(vote)
        
        # Look for changes within each subject
        for subject, subject_vote_list in subject_votes.items():
            if len(subject_vote_list) < 2:
                continue
            
            # Sort by date
            subject_vote_list = sorted(subject_vote_list, key=lambda v: v.vote_date)
            
            # Track vote pattern
            vote_pattern = [v.vote_choice for v in subject_vote_list if v.vote_choice in ['yes', 'no']]
            
            if not vote_pattern:
                continue
            
            # Detect changes
            for i in range(1, len(vote_pattern)):
                if vote_pattern[i] != vote_pattern[i-1]:
                    change = {
                        'subject': subject,
                        'from_position': vote_pattern[i-1],
                        'to_position': vote_pattern[i],
                        'date': subject_vote_list[i].vote_date.isoformat(),
                        'bill_id': subject_vote_list[i].bill_id,
                    }
                    position_changes.append(change)
                    
                    # Check if it's a flip-flop (change back to original position)
                    if i + 1 < len(vote_pattern) and vote_pattern[i+1] == vote_pattern[i-1]:
                        flip_flop = {
                            'subject': subject,
                            'positions': [vote_pattern[i-1], vote_pattern[i], vote_pattern[i+1]],
                            'dates': [
                                subject_vote_list[i-1].vote_date.isoformat(),
                                subject_vote_list[i].vote_date.isoformat(),
                                subject_vote_list[i+1].vote_date.isoformat(),
                            ],
                        }
                        flip_flops.append(flip_flop)
        
        return position_changes, flip_flops
    
    def calculate_bipartisan_score(
        self,
        person_id: int,
        sponsored_bills: List[Dict[str, Any]],
    ) -> float:
        """
        Calculate bipartisan score based on bill sponsorship/cosponsorship.
        
        Args:
            person_id: Person ID
            sponsored_bills: List of bills with cosponsor information
            
        Returns:
            Bipartisan score (0 to 1)
        """
        if not sponsored_bills:
            return 0.0
        
        bipartisan_count = 0
        
        for bill in sponsored_bills:
            # Check if bill has cosponsors from other party
            cosponsors = bill.get('cosponsors', [])
            parties = [c.get('party') for c in cosponsors]
            
            # If there are multiple parties, it's bipartisan
            unique_parties = set(p for p in parties if p)
            if len(unique_parties) > 1:
                bipartisan_count += 1
        
        return bipartisan_count / len(sponsored_bills)
    
    def compare_politicians(
        self,
        person1_id: int,
        person2_id: int,
        votes1: List[VoteRecord],
        votes2: List[VoteRecord],
    ) -> Dict[str, Any]:
        """
        Compare voting patterns between two politicians.
        
        Args:
            person1_id: First person ID
            person2_id: Second person ID
            votes1: Votes for first person
            votes2: Votes for second person
            
        Returns:
            Dictionary with comparison metrics
        """
        # Find common votes (same bill)
        bill_ids_1 = {v.bill_id for v in votes1}
        bill_ids_2 = {v.bill_id for v in votes2}
        common_bills = bill_ids_1 & bill_ids_2
        
        if not common_bills:
            return {
                'agreement_rate': None,
                'common_votes': 0,
                'message': 'No common votes found',
            }
        
        # Build vote lookup
        votes1_map = {v.bill_id: v.vote_choice for v in votes1 if v.bill_id in common_bills}
        votes2_map = {v.bill_id: v.vote_choice for v in votes2 if v.bill_id in common_bills}
        
        # Calculate agreement
        agreements = 0
        total = 0
        
        for bill_id in common_bills:
            choice1 = votes1_map.get(bill_id)
            choice2 = votes2_map.get(bill_id)
            
            if choice1 and choice2 and choice1 in ['yes', 'no'] and choice2 in ['yes', 'no']:
                total += 1
                if choice1 == choice2:
                    agreements += 1
        
        agreement_rate = agreements / total if total > 0 else None
        
        return {
            'person1_id': person1_id,
            'person2_id': person2_id,
            'agreement_rate': agreement_rate,
            'agreements': agreements,
            'disagreements': total - agreements,
            'common_votes': total,
        }


def analyze_voting_consistency(
    person_id: int,
    votes: List[VoteRecord],
    party: str = None,
) -> ConsistencyScore:
    """
    Convenience function for consistency analysis.
    
    Args:
        person_id: Person ID
        votes: List of vote records
        party: Party affiliation
        
    Returns:
        ConsistencyScore object
    """
    analyzer = ConsistencyAnalyzer()
    return analyzer.analyze_voting_consistency(person_id, votes, party)


# Example usage
EXAMPLE_USAGE = """
# Example: Analyzing voting consistency

from analysis.consistency_analyzer import ConsistencyAnalyzer, VoteRecord
from datetime import datetime

# Initialize analyzer
analyzer = ConsistencyAnalyzer()

# Create vote records
votes = [
    VoteRecord(1, 101, 1, 'yes', datetime(2023, 1, 15), 'healthcare', 'yes'),
    VoteRecord(2, 102, 1, 'yes', datetime(2023, 2, 20), 'healthcare', 'yes'),
    VoteRecord(3, 103, 1, 'no', datetime(2023, 3, 10), 'healthcare', 'yes'),
    VoteRecord(4, 104, 1, 'yes', datetime(2023, 4, 5), 'education', 'yes'),
]

# Analyze consistency
score = analyzer.analyze_voting_consistency(person_id=1, votes=votes, party='Democrat')

print(f"Overall consistency: {score.overall_consistency:.2f}")
print(f"Party line voting: {score.party_line_voting:.2%}")
print(f"Issue consistency: {score.issue_consistency}")
print(f"Position changes: {len(score.position_changes)}")
print(f"Flip-flops: {len(score.flip_flops)}")

# Compare two politicians
votes_person2 = [...]  # Another list of votes
comparison = analyzer.compare_politicians(1, 2, votes, votes_person2)
print(f"Agreement rate: {comparison['agreement_rate']:.2%}")
"""
