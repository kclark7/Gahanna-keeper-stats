import requests
from functions import *

# Setup Sleeper league API settings
league_id = "1385461620423012352" #Gahanna Keeper
sleeper_api = 'https://api.sleeper.app/v1/league/'
league = requests.get(sleeper_api + league_id).json()

gahanna_api = sleeper_api + league_id
users = requests.get(gahanna_api + '/users').json()
rosters = requests.get(gahanna_api + '/rosters').json()

for roster in rosters:
    roster['weekly_points_score'] = 0
    roster['previous_weekly_points_score'] = 0
weekly_points = {}

for week in range(1,15):
    weekly_points[week] = []
    matchups = requests.get(gahanna_api + '/matchups/' + str(week)).json()
    for match in matchups:
        weekly_points[week].append({match['roster_id'] : match['points']})

scores = {
    1:[],
    2:[],
    3:[],
    4:[],
    5:[],
    6:[],
    7:[],
    8:[],
    9:[],
    10:[],
    11:[],
    12:[],
    13:[],
    14:[]
    }

for week in weekly_points:
    scores[week] = []
    for roster in range(12):
        scores[week].append(weekly_points[week][roster][roster+1])
    scores[week].sort()

# Sleeper returns 0 points for weeks that have not been played yet. The most
# recent completed scoring week is therefore the last week containing points.
completed_weeks = [
    week for week in range(1, 15)
    if any(score > 0 for score in scores[week])
]
current_week = max(completed_weeks) if completed_weeks else 0
previous_week = max(current_week - 1, 0)

for week in range(1, current_week + 1):
    matchups = requests.get(gahanna_api + '/matchups/' + str(week)).json()
    for roster in rosters:
        for match in matchups:
            if roster['roster_id'] == match['roster_id']:
                if match['points'] > 0:
                    weekly_score = 0
                    for i in range(0, len(scores[week])):
                        for j in range(i+1, len(scores[week])):
                            if scores[week][i] == scores[week][j] == match['points']:
                                weekly_score += 0.5
                    weekly_score += scores[week].index(match['points']) + 1
                    roster['weekly_points_score'] += weekly_score
                    if week <= previous_week:
                        roster['previous_weekly_points_score'] += weekly_score

# Current Sleeper wins include the most recently completed week. Reconstruct
# the previous week's win total by checking matchup results through previous_week.
current_wins = {roster['roster_id']: roster['settings']['wins'] for roster in rosters}
previous_wins = {roster['roster_id']: 0 for roster in rosters}

for week in range(1, previous_week + 1):
    matchups = requests.get(gahanna_api + '/matchups/' + str(week)).json()
    matchup_groups = {}
    for match in matchups:
        matchup_groups.setdefault(match['matchup_id'], []).append(match)
    for matchup in matchup_groups.values():
        if len(matchup) == 2 and matchup[0]['points'] != matchup[1]['points']:
            winner = max(matchup, key=lambda x: x['points'])
            previous_wins[winner['roster_id']] += 1

standings = {}
previous_standings = {}

for user in users:
    for roster in rosters:
        if roster['owner_id'] == user['user_id']:
            standings[user['display_name']] = (
                roster['weekly_points_score'] + current_wins[roster['roster_id']] * 13
            )
            previous_standings[user['display_name']] = (
                roster['previous_weekly_points_score'] + previous_wins[roster['roster_id']] * 13
            )

standings = sorted(standings.items(), key=lambda x: x[1], reverse=True)
previous_standings = sorted(previous_standings.items(), key=lambda x: x[1], reverse=True)

current_rankings = {
    display_name: rank
    for rank, (display_name, _) in enumerate(standings, start=1)
}

previous_rankings = {
    display_name: rank
    for rank, (display_name, _) in enumerate(previous_standings, start=1)
}

previous_points = dict(previous_standings)

# Build historical rankings from the same Sleeper matchup data so we can detect
# teams that have moved in the same direction for three consecutive updates.
def standings_through_week(end_week):
    weekly_scores = {roster['roster_id']: 0 for roster in rosters}
    wins = {roster['roster_id']: 0 for roster in rosters}

    for week in range(1, end_week + 1):
        matchups = requests.get(gahanna_api + '/matchups/' + str(week)).json()
        week_scores = sorted(match['points'] for match in matchups)

        for match in matchups:
            if match['points'] > 0:
                weekly_score = week_scores.index(match['points']) + 1
                duplicate_count = week_scores.count(match['points'])
                if duplicate_count > 1:
                    weekly_score += 0.5 * (duplicate_count - 1)
                weekly_scores[match['roster_id']] += weekly_score

        matchup_groups = {}
        for match in matchups:
            matchup_groups.setdefault(match['matchup_id'], []).append(match)
        for matchup in matchup_groups.values():
            if len(matchup) == 2 and matchup[0]['points'] != matchup[1]['points']:
                winner = max(matchup, key=lambda x: x['points'])
                wins[winner['roster_id']] += 1

    week_standings = {}
    for user in users:
        for roster in rosters:
            if roster['owner_id'] == user['user_id']:
                week_standings[user['display_name']] = (
                    weekly_scores[roster['roster_id']] + wins[roster['roster_id']] * 13
                )

    sorted_week_standings = sorted(
        week_standings.items(), key=lambda x: x[1], reverse=True
    )
    return {
        display_name: rank
        for rank, (display_name, _) in enumerate(sorted_week_standings, start=1)
    }


ranking_history = {}
if current_week >= 4:
    for week in range(current_week - 3, current_week + 1):
        ranking_history[week] = standings_through_week(week)


def streak_emoji(display_name):
    if current_week < 3:
        return ""

    # A team holding 1st or 12th for the latest three weekly standings also
    # counts as a hot/cold streak even though it cannot keep moving further.
    last_three_ranks = [
        standings_through_week(week)[display_name]
        for week in range(current_week - 2, current_week + 1)
    ]
    if last_three_ranks == [1, 1, 1]:
        return " 🔥"
    if last_three_ranks == [12, 12, 12]:
        return " 🥶"

    if current_week < 4:
        return ""

    ranks = [
        ranking_history[week][display_name]
        for week in range(current_week - 3, current_week + 1)
    ]

    # Lower rank numbers mean the team moved up the standings.
    if ranks[0] > ranks[1] > ranks[2] > ranks[3]:
        return " 🔥"
    if ranks[0] < ranks[1] < ranks[2] < ranks[3]:
        return " 🥶"
    return ""


def ranking_movement(display_name):
    previous_rank = previous_rankings.get(display_name)
    current_rank = current_rankings[display_name]

    if previous_rank is None or previous_rank == current_rank:
        return ""

    places_moved = abs(previous_rank - current_rank)
    if current_rank < previous_rank:
        return f" (\033[92m↑ {places_moved}\033[0m)"
    return f" (\033[91m↓ {places_moved}\033[0m)"


def email_ranking_movement(display_name):
    previous_rank = previous_rankings.get(display_name)
    current_rank = current_rankings[display_name]

    if previous_rank is None:
        return '<span style="color:#6b7280;font-size:12px;">NEW</span>'
    if previous_rank == current_rank:
        return '<span style="color:#6b7280;">—</span>'

    places_moved = abs(previous_rank - current_rank)
    if current_rank < previous_rank:
        return f'<span style="color:#15803d;font-weight:700;">↑ {places_moved}</span>'
    return f'<span style="color:#b91c1c;font-weight:700;">↓ {places_moved}</span>'

email_body = f"""
<html>
<body style="margin:0;padding:24px;background-color:#f3f4f6;font-family:Arial,Helvetica,sans-serif;color:#111827;">
  <div style="max-width:680px;margin:0 auto;background-color:#ffffff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">
    <div style="padding:14px 18px 10px 18px;">
      <h2 style="margin:0;font-size:21px;">Week {current_week} Standings</h2>
    </div>
    <table role="presentation" style="width:100%;border-collapse:collapse;font-size:14px;">
      <thead>
        <tr style="background-color:#f9fafb;border-top:1px solid #e5e7eb;border-bottom:1px solid #e5e7eb;">
          <th style="padding:7px 12px;text-align:center;color:#6b7280;width:48px;">Rank</th>
          <th style="padding:7px 12px;text-align:left;color:#6b7280;">Team</th>
          <th style="padding:7px 10px;text-align:center;color:#6b7280;width:60px;">Move</th>
          <th style="padding:7px 12px;text-align:right;color:#6b7280;width:125px;white-space:nowrap;">Points</th>
        </tr>
      </thead>
      <tbody>
"""

for user in range(12):
    rank = user + 1
    display_name = standings[user][0]
    points = standings[user][1]
    points_gained = points - previous_points.get(display_name, points)
    points_movement = (
        f'<span style="color:#15803d;font-weight:700;margin-left:4px;">(+{points_gained:g})</span>'
        if points_gained > 0 else ""
    )
    movement = email_ranking_movement(display_name)
    streak = streak_emoji(display_name)

    # Label the top-six playoff section and the cutoff immediately above 7th place.
    if rank == 1:
        email_body += """
        <tr>
          <td colspan="4" style="border-top:3px solid #374151;padding:4px 12px 2px 12px;color:#15803d;font-size:11px;font-weight:700;letter-spacing:0.3px;">
            PLAYOFF POSITION
          </td>
        </tr>
"""
    elif rank == 7:
        email_body += """
        <tr>
          <td colspan="4" style="border-top:3px solid #374151;padding:4px 12px 2px 12px;color:#b91c1c;font-size:11px;font-weight:700;letter-spacing:0.3px;">
            OUTSIDE LOOKING IN
          </td>
        </tr>
"""

    bye_label = ""
    if rank <= 2:
        bye_label = '<span style="display:inline-block;margin-left:8px;padding:2px 6px;border-radius:4px;background-color:#eef2ff;color:#4338ca;font-size:10px;font-weight:700;letter-spacing:0.3px;vertical-align:1px;">BYE</span>'

    email_body += f"""
        <tr style="border-bottom:1px solid #e5e7eb;">
          <td style="padding:8px 12px;text-align:center;font-weight:700;">{rank}</td>
          <td style="padding:8px 12px;font-weight:600;">{display_name}{streak}{bye_label}</td>
          <td style="padding:8px 10px;text-align:center;">{movement}</td>
          <td style="padding:8px 12px;text-align:right;white-space:nowrap;">{points:g} {points_movement}</td>
        </tr>
"""

email_body += """
      </tbody>
    </table>
    <div style="padding:8px 18px 10px 18px;color:#6b7280;font-size:12px;">
      <span style="color:#15803d;font-weight:700;">↑</span> moved up &nbsp;&nbsp;
      <span style="color:#b91c1c;font-weight:700;">↓</span> moved down
    </div>
  </div>
</body>
</html>
"""

# Send HTML standings email.
send_email("Weekly Standings Update", email_body, html=True)