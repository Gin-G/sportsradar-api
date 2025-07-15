import json
import os
import requests

API_KEY = os.environ.get("API_KEY")

headers = {
    "accept": "application/json",
    "x-api-key": API_KEY
}

def get_teams():
    url = "https://api.sportradar.com/nfl/official/trial/v7/en/league/teams.json"

    response = requests.get(url, headers=headers)

    return response.json()

def get_roster(team_id):
    url = "https://api.sportradar.com/nfl/official/trial/v7/en/teams/" + team_id + "/full_roster.json"

    response = requests.get(url, headers=headers)

    return response.json()

def get_team_id_by_abbreviation(abbreviation):
    """Look up team ID by abbreviation (alias)"""
    teams_data = get_teams()
    
    for team in teams_data["teams"]:
        if team["alias"].upper() == abbreviation.upper():
            return team["id"]
    
    return None  # Team not found

def get_roster_by_abbreviation(abbreviation):
    """Get roster using team abbreviation"""
    team_id = get_team_id_by_abbreviation(abbreviation)
    
    if team_id:
        return get_roster(team_id)
    else:
        raise ValueError(f"Team with abbreviation '{abbreviation}' not found")

# Example usage:
try:
    # Get roster for San Francisco 49ers using "SF"
    roster = get_roster_by_abbreviation("NE")
    print(json.dumps(roster, indent=2))
except ValueError as e:
    print(f"Error: {e}")

'''
# Or get multiple teams by abbreviation
team_abbreviations = ["SF", "KC", "BUF", "DAL"]

for abbr in team_abbreviations:
    try:
        print(f"Getting roster for {abbr}")
        roster = get_roster_by_abbreviation(abbr)
        print(json.dumps(roster, indent=2))
        print("-" * 50)
    except ValueError as e:
        print(f"Error: {e}")

teams = get_teams()
print(json.dumps(teams, indent=2))

# Loop through each team and get their roster
for team in teams["teams"]:
    team_id = team["id"]
    team_name = team["name"]
    team_market = team["market"]
    
    print(f"Getting roster for {team_market} {team_name} (ID: {team_id})")
    
    try:
        roster = get_roster(team_id)
        print(json.dumps(roster, indent=2))
        print("-" * 50)  # Separator between teams
    except Exception as e:
        print(f"Error getting roster for {team_market} {team_name}: {e}")
'''