import json
import urllib.request

req = urllib.request.urlopen("http://localhost:8001/runs/eng-51c378fbaa18/events?after=0&limit=200")
data = json.loads(req.read())

print("KEPT PAPERS:")
for e in data['events']:
    if e['type'] == 'screen.kept':
        p = e['payload'].get('paper', {})
        print(f"- [{p.get('id')}] {p.get('citation')}: {p.get('title')} ({p.get('venue')}, {p.get('year')})")

print("\nCLUSTERS:")
for e in data['events']:
    if e['type'] == 'synthesis.cluster':
        c = e['payload'].get('cluster', {})
        print(f"- [{c.get('id')}] {c.get('title')}: {c.get('claim')}")

print("\nGAPS:")
for e in data['events']:
    if e['type'] == 'synthesis.gap':
        g = e['payload'].get('gap', {})
        print(f"- [{g.get('id')}] {g.get('text')} (from: {g.get('from')})")
