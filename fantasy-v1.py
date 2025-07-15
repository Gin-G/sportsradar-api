import json
import os
import requests
import time
from typing import Dict, List, Optional, Tuple

API_KEY = os.environ.get("API_KEY")

HEADERS = {
    "accept": "application/json",
    "x-api-key": API_KEY
}

# Rate limiting configuration
REQUEST_DELAY = 1.0  # Seconds between requests
MAX_RETRIES = 3
RETRY_DELAY = 5.0  # Seconds to wait on 429 error

def make_request_with_retry(url: str, max_retries: int = MAX_RETRIES) -> requests.Response:
    """Make HTTP request with retry logic for rate limiting"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=HEADERS)
            
            if response.status_code == 429:
                print(f"Rate limit hit. Waiting {RETRY_DELAY} seconds before retry {attempt + 1}/{max_retries}")
                time.sleep(RETRY_DELAY)
                continue
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise e
            print(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(RETRY_DELAY)
    
    raise Exception("Max retries exceeded")

def get_teams():
    url = "https://api.sportradar.com/nfl/official/trial/v7/en/league/teams.json"
    
    response = make_request_with_retry(url)
    time.sleep(REQUEST_DELAY)  # Rate limiting
    return response.json()

def get_roster(team_id):
    url = "https://api.sportradar.com/nfl/official/trial/v7/en/teams/" + team_id + "/full_roster.json"
    
    response = make_request_with_retry(url)
    time.sleep(REQUEST_DELAY)  # Rate limiting
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

    response = make_request_with_retry(url)
    time.sleep(REQUEST_DELAY)  # Rate limiting
    return response.json()

def get_weekly_schedule(week=1, year=2025):
    week, year = str(week), str(year)
    url = f"https://api.sportradar.com/nfl/official/trial/v7/en/games/{year}/REG/{week}/schedule.json"

    response = make_request_with_retry(url)
    time.sleep(REQUEST_DELAY)  # Rate limiting
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
    
    # Use a set to avoid duplicate team entries
    unique_teams = set()
    
    for game in games:
        home_team = game.get("home")
        away_team = game.get("away")
        
        # Add home team with away opponent
        home_team_id = home_team.get("id")
        if home_team_id not in unique_teams:
            teams_playing["teams"].append({
                "team_id": home_team_id,
                "team_name": home_team.get("name"),
                "team_alias": home_team.get("alias"),
                "opponent_id": away_team.get("id"),
                "opponent_name": away_team.get("name"),
                "opponent_alias": away_team.get("alias"),
                "home_away": "home",
                "game_id": game.get("id"),
                "scheduled": game.get("scheduled")
            })
            unique_teams.add(home_team_id)
        
        # Add away team with home opponent
        away_team_id = away_team.get("id")
        if away_team_id not in unique_teams:
            teams_playing["teams"].append({
                "team_id": away_team_id,
                "team_name": away_team.get("name"),
                "team_alias": away_team.get("alias"),
                "opponent_id": home_team.get("id"),
                "opponent_name": home_team.get("name"),
                "opponent_alias": home_team.get("alias"),
                "home_away": "away",
                "game_id": game.get("id"),
                "scheduled": game.get("scheduled")
            })
            unique_teams.add(away_team_id)
    
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
    
    print(f"Getting teams playing in week {week}, {year}...")
    teams_data = get_teams_playing_this_week(week, year)
    player_pool = {pos: [] for pos in positions}
    
    print(f"Found {len(teams_data['teams'])} teams playing this week")
    print(f"This will require {len(teams_data['teams'])} roster API calls...")
    
    # Process each team playing this week
    for i, team_info in enumerate(teams_data["teams"], 1):
        print(f"Processing team {i}/{len(teams_data['teams'])}: {team_info['team_name']} ({team_info['team_alias']})")
        
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
    
    # Print summary
    print("\nPlayer pool summary:")
    for position, players in player_pool.items():
        print(f"{position}: {len(players)} players")
    
    return player_pool

def save_player_pool_to_file(player_pool: Dict, week: int = 1, year: int = 2025, filename: str = None):
    """Save player pool data to JSON file"""
    if filename is None:
        filename = f"fantasy_player_pool_week_{week}_{year}.json"
    
    with open(filename, 'w') as f:
        json.dump(player_pool, f, indent=2)
    print(f"Player pool saved to {filename}")

def load_player_pool_from_file(filename: str = None, week: int = 1, year: int = 2025) -> Dict:
    """Load player pool data from JSON file"""
    if filename is None:
        filename = f"fantasy_player_pool_week_{week}_{year}.json"
    
    try:
        with open(filename, 'r') as f:
            player_pool = json.load(f)
        print(f"Player pool loaded from {filename}")
        return player_pool
    except FileNotFoundError:
        print(f"File {filename} not found")
        return {}
    except json.JSONDecodeError:
        print(f"Error reading JSON from {filename}")
        return {}

def get_players_by_position_filter(player_pool: Dict, positions: List[str]) -> List[Dict]:
    """
    Filter players by specific positions from loaded player pool
    
    Args:
        player_pool: Dictionary with position keys and player lists
        positions: List of positions to include (e.g., ['QB'], ['WR'], ['RB', 'WR', 'TE'])
    
    Returns:
        List of all players matching the specified positions
    """
    filtered_players = []
    
    for position in positions:
        if position in player_pool:
            filtered_players.extend(player_pool[position])
    
    return filtered_players

def get_qbs(week: int = 1, year: int = 2025) -> List[Dict]:
    """Get all quarterbacks from QB file"""
    filename = f"qb_players_week_{week}_{year}.json"
    try:
        with open(filename, 'r') as f:
            qbs = json.load(f)
        print(f"Found {len(qbs)} quarterbacks")
        return qbs
    except FileNotFoundError:
        print(f"File {filename} not found")
        return []

def get_rbs(week: int = 1, year: int = 2025) -> List[Dict]:
    """Get all running backs from RB file"""
    filename = f"rb_players_week_{week}_{year}.json"
    try:
        with open(filename, 'r') as f:
            rbs = json.load(f)
        print(f"Found {len(rbs)} running backs")
        return rbs
    except FileNotFoundError:
        print(f"File {filename} not found")
        return []

def get_wrs(week: int = 1, year: int = 2025) -> List[Dict]:
    """Get all wide receivers from WR file"""
    filename = f"wr_players_week_{week}_{year}.json"
    try:
        with open(filename, 'r') as f:
            wrs = json.load(f)
        print(f"Found {len(wrs)} wide receivers")
        return wrs
    except FileNotFoundError:
        print(f"File {filename} not found")
        return []

def get_tes(week: int = 1, year: int = 2025) -> List[Dict]:
    """Get all tight ends from TE file"""
    filename = f"te_players_week_{week}_{year}.json"
    try:
        with open(filename, 'r') as f:
            tes = json.load(f)
        print(f"Found {len(tes)} tight ends")
        return tes
    except FileNotFoundError:
        print(f"File {filename} not found")
        return []

def save_position_files(player_pool: Dict, week: int = 1, year: int = 2025):
    """Save separate JSON files for each position"""
    positions = {
        'QB': get_players_by_position_filter(player_pool, ['QB']),
        'RB': get_players_by_position_filter(player_pool, ['RB']),
        'WR': get_players_by_position_filter(player_pool, ['WR']),
        'TE': get_players_by_position_filter(player_pool, ['TE'])
    }
    
    for position, players in positions.items():
        filename = f"{position.lower()}_players_week_{week}_{year}.json"
        with open(filename, 'w') as f:
            json.dump(players, f, indent=2)
        print(f"{position}: {len(players)} players saved to {filename}")

def get_flex_eligible(week: int = 1, year: int = 2025) -> List[Dict]:
    """Get all FLEX-eligible players by loading RB, WR, and TE files"""
    flex_players = []
    
    for position in ['rb', 'wr', 'te']:
        filename = f"{position}_players_week_{week}_{year}.json"
        try:
            with open(filename, 'r') as f:
                players = json.load(f)
                flex_players.extend(players)
        except FileNotFoundError:
            print(f"Warning: {filename} not found")
        except json.JSONDecodeError:
            print(f"Error reading {filename}")
    
    print(f"Found {len(flex_players)} FLEX-eligible players")
    return flex_players

def print_player_summary(players: List[Dict], position_name: str = "Players"):
    """Print a summary of players with key info"""
    print(f"\n{position_name} Summary ({len(players)} players):")
    print("-" * 60)
    
    for player in players[:10]:  # Show first 10 players
        print(f"{player['name']} ({player['team_alias']}) vs {player['opponent_alias']} - {player['home_away'].upper()}")
    
    if len(players) > 10:
        print(f"... and {len(players) - 10} more players")
    
    # Team distribution
    teams = {}
    for player in players:
        team = player['team_alias']
        teams[team] = teams.get(team, 0) + 1
    
    print(f"\nTeam distribution:")
    for team, count in sorted(teams.items()):
        print(f"  {team}: {count} players")

# Example usage with error handling
if __name__ == "__main__":
    try:
        print("Starting player pool collection...")
        schedule = get_fantasy_player_pool(week=1, year=2025)
        
        # Save main file and individual position files
        save_player_pool_to_file(schedule, week=1, year=2025)
        save_position_files(schedule, week=1, year=2025)
        
        # Print just the summary
        print("\nFinal summary:")
        for position, players in schedule.items():
            print(f"{position}: {len(players)} players")
        
        # Example of using the separate files
        print("\n" + "="*60)
        print("POSITION FILE EXAMPLES:")
        print("="*60)
        
        # Load from individual files
        qbs = get_qbs(week=1, year=2025)
        rbs = get_rbs(week=1, year=2025)
        flex_players = get_flex_eligible(week=1, year=2025)
        
        print_player_summary(qbs, "Quarterbacks")
        print_player_summary(flex_players, "FLEX Players")
            
    except Exception as e:
        print(f"Error: {e}")
        print("Check your API_KEY environment variable and network connection")