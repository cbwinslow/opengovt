# API Endpoints Reference

This document provides information about the various government data APIs that this project integrates with.

## Table of Contents
- [Congress.gov API](#congressgov-api)
- [GovInfo.gov API](#govinfoagov-api)
- [OpenStates API](#openstates-api)
- [ProPublica Congress API](#propublica-congress-api)
- [GovTrack API](#govtrack-api)
- [Using the APIs](#using-the-apis)

---

## Congress.gov API

**Base URL**: `https://api.congress.gov/v3/`

**Authentication**: API key required (free registration at https://api.congress.gov/sign-up/)

**Rate Limits**: 5,000 requests per hour

### Key Endpoints

#### 1. Bills

```
GET /bill
GET /bill/{congress}
GET /bill/{congress}/{billType}
GET /bill/{congress}/{billType}/{billNumber}
GET /bill/{congress}/{billType}/{billNumber}/actions
GET /bill/{congress}/{billType}/{billNumber}/amendments
GET /bill/{congress}/{billType}/{billNumber}/cosponsors
GET /bill/{congress}/{billType}/{billNumber}/text
GET /bill/{congress}/{billType}/{billNumber}/summaries
```

**Example Request**:
```bash
curl -X GET "https://api.congress.gov/v3/bill/118/hr/1234?api_key=YOUR_API_KEY"
```

**Example Response**:
```json
{
  "bill": {
    "congress": 118,
    "type": "HR",
    "number": "1234",
    "title": "To provide...",
    "introducedDate": "2023-01-15",
    "updateDate": "2023-03-20",
    "sponsors": [
      {
        "bioguideId": "S000148",
        "fullName": "Sen. Schumer, Charles E.",
        "firstName": "Charles",
        "lastName": "Schumer",
        "party": "D",
        "state": "NY"
      }
    ]
  }
}
```

#### 2. Members

```
GET /member
GET /member/{bioguideId}
GET /member/{bioguideId}/sponsored-legislation
GET /member/{bioguideId}/cosponsored-legislation
```

**Example**:
```bash
curl "https://api.congress.gov/v3/member/S000148?api_key=YOUR_API_KEY"
```

#### 3. Amendments

```
GET /amendment
GET /amendment/{congress}/{amendmentType}
GET /amendment/{congress}/{amendmentType}/{amendmentNumber}
```

#### 4. Committees

```
GET /committee
GET /committee/{chamber}
GET /committee/{chamber}/{committeeCode}
GET /committee/{chamber}/{committeeCode}/reports
```

#### 5. Congressional Record

```
GET /congressional-record
GET /congressional-record/{volumeNumber}
GET /congressional-record/{volumeNumber}/{issueNumber}
```

### Python Usage Example

```python
import requests

API_KEY = "your_api_key_here"
BASE_URL = "https://api.congress.gov/v3"

def get_bill(congress, bill_type, bill_number):
    """Fetch bill details from Congress.gov API."""
    url = f"{BASE_URL}/bill/{congress}/{bill_type}/{bill_number}"
    params = {"api_key": API_KEY, "format": "json"}
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

# Example: Get HR 1234 from 118th Congress
bill = get_bill(118, "hr", 1234)
print(f"Title: {bill['bill']['title']}")
print(f"Sponsor: {bill['bill']['sponsors'][0]['fullName']}")
```

---

## GovInfo.gov API

**Base URL**: `https://api.govinfo.gov/`

**Authentication**: API key required (get at https://api.govinfo.gov/signup/)

**Bulk Data**: `https://www.govinfo.gov/bulkdata/`

### Key Endpoints

#### 1. Collections

```
GET /collections
GET /collections/{collectionCode}
GET /collections/{collectionCode}/{publishDate}
```

**Collections Available**:
- `BILLS`: Bill texts
- `BILLSTATUS`: Bill status and metadata
- `CREC`: Congressional Record
- `PLAW`: Public Laws
- `STATUTE`: Statutes at Large

**Example**:
```bash
curl "https://api.govinfo.gov/collections/BILLS/2023-01-15?api_key=YOUR_API_KEY"
```

#### 2. Packages

```
GET /packages/{packageId}
GET /packages/{packageId}/summary
GET /packages/{packageId}/granules
```

**Example**:
```bash
curl "https://api.govinfo.gov/packages/BILLS-118hr1234ih?api_key=YOUR_API_KEY"
```

### Bulk Data Access

**Direct Downloads** (no API key required):
```
https://www.govinfo.gov/bulkdata/BILLS/{congress}/{chamber}/BILLS-{congress}{chamber}.zip
https://www.govinfo.gov/bulkdata/BILLSTATUS/{congress}/hr/BILLSTATUS-{congress}hr.xml
```

**Example Python**:
```python
import requests

def download_bulk_data(congress, chamber):
    """Download bulk bill data from GovInfo."""
    url = f"https://www.govinfo.gov/bulkdata/BILLS/{congress}/{chamber}/BILLS-{congress}{chamber}.zip"
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(f"bills_{congress}_{chamber}.zip", "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

# Download House bills from 118th Congress
download_bulk_data(118, "hr")
```

---

## OpenStates API

**Base URL**: `https://v3.openstates.org/`

**GraphQL Endpoint**: `https://v3.openstates.org/graphql`

**Authentication**: API key required (get at https://openstates.org/accounts/profile/)

**Rate Limits**: Varies by plan (free tier: 1000 requests/day)

### GraphQL Queries

#### 1. Search Bills

```graphql
query {
  bills(
    jurisdiction: "New York"
    session: "2023"
    searchQuery: "healthcare"
    first: 10
  ) {
    edges {
      node {
        id
        identifier
        title
        classification
        subject
        createdAt
        updatedAt
      }
    }
  }
}
```

#### 2. Get Legislator

```graphql
query {
  person(id: "ocd-person/12345") {
    id
    name
    givenName
    familyName
    currentRole {
      title
      district
      chamber
      party
      division {
        name
      }
    }
  }
}
```

#### 3. Get Votes

```graphql
query {
  bill(id: "ocd-bill/12345") {
    votes {
      edges {
        node {
          id
          motion
          result
          date
          counts {
            option
            value
          }
        }
      }
    }
  }
}
```

### Python Usage with GraphQL

```python
import requests

API_KEY = "your_api_key"
GRAPHQL_URL = "https://v3.openstates.org/graphql"

def query_openstates(query, variables=None):
    """Execute GraphQL query against OpenStates API."""
    headers = {
        "X-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    response = requests.post(GRAPHQL_URL, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()

# Example: Search for bills
query = """
query SearchBills($jurisdiction: String!, $searchQuery: String!) {
  bills(jurisdiction: $jurisdiction, searchQuery: $searchQuery, first: 10) {
    edges {
      node {
        identifier
        title
      }
    }
  }
}
"""

result = query_openstates(query, {
    "jurisdiction": "New York",
    "searchQuery": "healthcare"
})

for bill in result["data"]["bills"]["edges"]:
    print(f"{bill['node']['identifier']}: {bill['node']['title']}")
```

### Bulk Data Downloads

**Available at**: https://openstates.org/downloads/

**Format**: State-by-state JSON files

```bash
# Download New York data
curl -O "https://data.openstates.org/ny/2023.json"

# Or use the Plural mirror
curl -O "https://open.pluralpolicy.com/data/openstates-ny.zip"
```

---

## ProPublica Congress API

**Base URL**: `https://api.propublica.org/congress/v1/`

**Authentication**: API key in header `X-API-Key`

**Get API key**: https://www.propublica.org/datastore/api/propublica-congress-api

**Rate Limits**: 5,000 requests per day

### Key Endpoints

#### 1. Members

```
GET /{congress}/{chamber}/members.json
GET /members/{member-id}.json
GET /members/{member-id}/votes.json
GET /members/{member-id}/bills/{type}.json
```

**Example**:
```bash
curl "https://api.propublica.org/congress/v1/118/senate/members.json" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### 2. Votes

```
GET /{congress}/{chamber}/sessions/{session-number}/votes/{roll-call-number}.json
GET /{congress}/{chamber}/votes/recent.json
```

#### 3. Bills

```
GET /{congress}/bills/{type}.json
GET /{congress}/bills/{bill-id}.json
```

### Python Example

```python
import requests

API_KEY = "your_api_key"
BASE_URL = "https://api.propublica.org/congress/v1"

def get_recent_votes(congress, chamber):
    """Get recent votes from ProPublica API."""
    url = f"{BASE_URL}/{congress}/{chamber}/votes/recent.json"
    headers = {"X-API-Key": API_KEY}
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# Get recent Senate votes
votes = get_recent_votes(118, "senate")
for vote in votes["results"]["votes"]:
    print(f"{vote['date']}: {vote['question']}")
```

---

## GovTrack API

**Base URL**: `https://www.govtrack.us/api/v2/`

**Authentication**: None required

**Rate Limits**: Reasonable use (consider caching)

### Key Endpoints

#### 1. Bills

```
GET /bill
GET /bill/{id}
```

**Example**:
```bash
curl "https://www.govtrack.us/api/v2/bill?congress=118&bill_type=h_res&number=1234"
```

#### 2. Votes

```
GET /vote
GET /vote/{id}
GET /vote_voter
```

#### 3. Roles (Legislators)

```
GET /role
GET /role/{id}
GET /person
GET /person/{id}
```

### Python Example

```python
import requests

BASE_URL = "https://www.govtrack.us/api/v2"

def search_bills(congress, keywords):
    """Search bills on GovTrack."""
    url = f"{BASE_URL}/bill"
    params = {
        "congress": congress,
        "q": keywords,
        "limit": 20
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

# Search for healthcare bills
bills = search_bills(118, "healthcare")
for bill in bills["objects"]:
    print(f"{bill['display_number']}: {bill['title']}")
```

---

## Using the APIs

### Best Practices

1. **Cache Responses**: Store API responses to minimize requests
2. **Respect Rate Limits**: Implement backoff and retry logic
3. **Use Bulk Data When Possible**: Download bulk datasets for large-scale analysis
4. **Handle Errors Gracefully**: Check for rate limits and API errors
5. **Version Your Data**: Track when data was last updated

### Example: Unified API Client

```python
import requests
import time
from functools import wraps

def rate_limit(max_per_second=1):
    """Decorator to rate limit API calls."""
    min_interval = 1.0 / max_per_second
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            wait_time = min_interval - elapsed
            if wait_time > 0:
                time.sleep(wait_time)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator

class GovernmentDataAPI:
    """Unified client for government data APIs."""
    
    def __init__(self, congress_api_key=None, openstates_api_key=None, propublica_api_key=None):
        self.congress_api_key = congress_api_key
        self.openstates_api_key = openstates_api_key
        self.propublica_api_key = propublica_api_key
    
    @rate_limit(max_per_second=1)
    def get_congress_bill(self, congress, bill_type, bill_number):
        """Fetch bill from Congress.gov API."""
        url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type}/{bill_number}"
        params = {"api_key": self.congress_api_key, "format": "json"}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    @rate_limit(max_per_second=1)
    def query_openstates(self, query, variables=None):
        """Query OpenStates GraphQL API."""
        url = "https://v3.openstates.org/graphql"
        headers = {
            "X-API-KEY": self.openstates_api_key,
            "Content-Type": "application/json"
        }
        
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    
    @rate_limit(max_per_second=0.1)  # ProPublica is stricter
    def get_propublica_votes(self, congress, chamber):
        """Get recent votes from ProPublica."""
        url = f"https://api.propublica.org/congress/v1/{congress}/{chamber}/votes/recent.json"
        headers = {"X-API-Key": self.propublica_api_key}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

# Usage
api = GovernmentDataAPI(
    congress_api_key="your_key",
    openstates_api_key="your_key",
    propublica_api_key="your_key"
)

# Fetch data from multiple sources
federal_bill = api.get_congress_bill(118, "hr", 1234)
state_bills = api.query_openstates("query { ... }")
recent_votes = api.get_propublica_votes(118, "senate")
```

### Error Handling

```python
import requests
from requests.exceptions import HTTPError, Timeout, RequestException

def safe_api_call(func, *args, max_retries=3, **kwargs):
    """Safely call API with retries."""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except HTTPError as e:
            if e.response.status_code == 429:  # Rate limit
                wait_time = int(e.response.headers.get('Retry-After', 60))
                print(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            elif e.response.status_code in [500, 502, 503, 504]:  # Server errors
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Server error. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise
        except (Timeout, RequestException) as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Request failed. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise
    
    raise Exception(f"Failed after {max_retries} attempts")
```

---

*Last Updated: 2025-10-14*
*Part of the OpenDiscourse.net project*
