import json
import os
import requests
from typing import Dict, List, Optional, Tuple

API_KEY = os.environ.get("API_KEY")

HEADERS = {
    "accept": "application/json",
    "x-api-key": API_KEY
}

def get_teams():
    url = "https://api.sportradar.com/nfl/official/trial/v7/en/league/teams.json"

    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def get_roster(team_id):
    url = "https://api.sportradar.com/nfl/official/trial/v7/en/teams/" + team_id + "/full_roster.json"

    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
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

def get_full_schedule(year=2025):
    year = str(year)
    url = f"https://api.sportradar.com/nfl/official/trial/v7/en/games/{year}/REG/schedule.json"

    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def get_weekly_schedule(week=1, year=2025):
    week, year = str(week), str(year)
    url = f"https://api.sportradar.com/nfl/official/trial/v7/en/games/{year}/REG/{week}/schedule.json"

    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def get_teams_playing_this_week(week=1, year=2025):
    """Get all teams playing in a specific week with their opponents"""
    schedule = get_weekly_schedule(week, year)
    
    # The games are nested under a 'week' object in the API response
    week_data = schedule.get("week", {})
    games = week_data.get("games", [])
    
    teams_playing = {
        "week": week,
        "year": year,
        "total_teams": 0,
        "total_games": len(games),
        "teams": []
    }
    
    for game in games:
        home_team = game.get("home")
        away_team = game.get("away")
        
        # Add home team with away opponent
        teams_playing["teams"].append({
            "team_id": home_team.get("id"),
            "team_name": home_team.get("name"),
            "team_alias": home_team.get("alias"),
            "opponent_id": away_team.get("id"),
            "opponent_name": away_team.get("name"),
            "opponent_alias": away_team.get("alias"),
            "home_away": "home",
            "game_id": game.get("id"),
            "scheduled": game.get("scheduled")
        })
        
        # Add away team with home opponent
        teams_playing["teams"].append({
            "team_id": away_team.get("id"),
            "team_name": away_team.get("name"),
            "team_alias": away_team.get("alias"),
            "opponent_id": home_team.get("id"),
            "opponent_name": home_team.get("name"),
            "opponent_alias": home_team.get("alias"),
            "home_away": "away",
            "game_id": game.get("id"),
            "scheduled": game.get("scheduled")
        })
    
    teams_playing["total_teams"] = len(teams_playing["teams"])
    return teams_playing

def get_players_by_position(roster_data, position):
    """Extract players of a specific position from roster data"""
    players = []
    
    for player in roster_data.get("players", []):
        if player.get("position") == position:
            players.append({
                "id": player.get("id"),
                "name": player.get("name"),
                "position": player.get("position"),
                "jersey": player.get("jersey"),
                "height": player.get("height"),
                "weight": player.get("weight"),
                "birth_date": player.get("birth_date"),
                "experience": player.get("experience"),
                "college": player.get("college")
            })
    
    return players

def get_fantasy_player_pool(week=1, year=2025, positions=None):
    """
    Get all players by position for teams playing in a specific week
    
    Args:
        week: NFL week number
        year: NFL season year
        positions: List of positions to include (default: QB, RB, WR, TE)
    
    Returns:
        Dictionary with positions as keys and lists of players as values
    """
    if positions is None:
        positions = ["QB", "RB", "WR", "TE"]
    
    teams_data = get_teams_playing_this_week(week, year)
    player_pool = {pos: [] for pos in positions}
    
    # Process each team playing this week
    for team_info in teams_data["teams"]:
        try:
            roster_data = get_roster(team_info["team_id"])
            
            # Get players for each requested position
            for position in positions:
                players = get_players_by_position(roster_data, position)
                
                # Add team and opponent info to each player
                for player in players:
                    player.update({
                        "team_id": team_info["team_id"],
                        "team_name": team_info["team_name"],
                        "team_alias": team_info["team_alias"],
                        "opponent_id": team_info["opponent_id"],
                        "opponent_name": team_info["opponent_name"],
                        "opponent_alias": team_info["opponent_alias"],
                        "home_away": team_info["home_away"],
                        "game_id": team_info["game_id"],
                        "scheduled": team_info["scheduled"]
                    })
                    
                    player_pool[position].append(player)
                    
        except Exception as e:
            print(f"Error processing team {team_info['team_name']}: {e}")
            continue
    
    return player_pool

schedule = get_fantasy_player_pool()
print(json.dumps(schedule, indent=2))

'''
# Example usage:
try:
    # Get roster for San Francisco 49ers using "SF"
    roster = get_roster_by_abbreviation("NE")
    print(json.dumps(roster, indent=2))
except ValueError as e:
    print(f"Error: {e}")

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