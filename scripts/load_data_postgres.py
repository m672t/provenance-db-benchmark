import psycopg2
import json
import time

print("=" * 60)
print("بارگذاری داده در PostgreSQL")
print("=" * 60)

DATA_FILE = '../data.json'

try:
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="4570176501",
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()
    
    total = 0
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except:
                continue
            
            if 'datum' not in record:
                continue
            
            datum = record['datum']
            if isinstance(datum, dict):
                for key, value in datum.items():
                    if isinstance(value, dict):
                        item = value
                        if 'uuid' in item:
                            cur.execute(
                                "INSERT INTO nodes (uuid, type) VALUES (%s, %s) ON CONFLICT (uuid) DO NOTHING",
                                (item['uuid'], item.get('type', 'Unknown'))
                            )
                        elif 'src' in item and 'dst' in item:
                            cur.execute(
                                "INSERT INTO edges (src, dst, type, ts) VALUES (%s, %s, %s, %s)",
                                (item['src'], item['dst'], item.get('type', 'Unknown'), item.get('ts', 0))
                            )
                        total += 1
            
            if line_num % 10000 == 0:
                conn.commit()
                print(f"   {line_num} خط پردازش شد...")
    
    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ PostgreSQL: {total} آیتم بارگذاری شد")
    
except Exception as e:
    print(f"❌ خطا: {e}")
