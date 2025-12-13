import requests
import json

# Get all authorized users
response = requests.get('http://localhost:5001/api/access-granted-users')

print(f'Status Code: {response.status_code}')
print(f'Response: {response.text}')

# Parse the response
if response.status_code == 200:
    data = response.json()
    if data.get('success'):
        users = data.get('data', [])
        print(f"\nFound {len(users)} authorized users:")
        for user in users:
            print(f"- {user.get('FULL_NAME', '')} ({user.get('EMPLOYEE_ID', '')}) - {user.get('DEPARTMENT', '')}")
    else:
        print("API returned success=False")
else:
    print("Failed to get users")