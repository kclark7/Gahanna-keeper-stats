import requests

# Setup Sleeper league API settings
league_id = "1253713259077324800" #Gahanna Keeper
sleeper_api = 'https://api.sleeper.app/v1/league/'
league = requests.get(sleeper_api + league_id).json()

gahanna_api = sleeper_api + league_id
users = requests.get(gahanna_api + '/users').json()

# Get leaguemates
for user in users:
    user['standings_points'] = 0

rosters = requests.get(gahanna_api + '/rosters').json()
for roster in rosters:
    roster['weekly_points_score'] = 0
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
    for roster in range (12):
        scores[week].append(weekly_points[week][roster][roster+1])
    scores[week].sort()

for week in range (1,15):
    matchups = requests.get(gahanna_api + '/matchups/' + str(week)).json()
    for roster in rosters:
        for match in matchups:
            if roster['roster_id'] == match['roster_id']:
                if(match['points'] > 0):
                    for i in range(0, len(scores[week])):
                        for j in range(i+1, len(scores[week])):
                            if(scores[week][i] == scores[week][j] == match['points']):
                                roster['weekly_points_score'] += 0.5
                    roster['weekly_points_score'] += scores[week].index(match['points']) + 1

for user in users:
    for roster in rosters:
        if roster['owner_id'] == user['user_id']:
            user['standings_points'] += roster['weekly_points_score']

for user in users:
    for roster in rosters:
        if roster['owner_id'] == user['user_id']:
            print(roster['settings']['wins'] * 13)
            print(user['standings_points'])
            user['standings_points'] += roster['settings']['wins'] * 13

standings = {}

for user in users:
    standings[user['display_name']] = user['standings_points']

standings = sorted(standings.items(), key=lambda x: x[1], reverse=True)

print("\nPlayoffs:")
for user in range(12):
    if user == 6:
        print("\nOutside looking in:")
    print(f"{user+1}: {standings[user][0]} - {standings[user][1]} points")