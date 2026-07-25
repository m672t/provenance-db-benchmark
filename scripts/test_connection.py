import psycopg2
from neo4j import GraphDatabase

print("=" * 50)
print("تست اتصال به دیتابیس‌ها")
print("=" * 50)

print("\n🔵 تست PostgreSQL...")
try:
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="4570176501",
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()
    print(f"✅ PostgreSQL متصل شد! نسخه: {version[0][:50]}...")
    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ خطا در PostgreSQL: {e}")

print("\n🟢 تست Neo4j...")
try:
    driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "4570176501")
    )
    with driver.session() as session:
        result = session.run("RETURN 1 AS test")
        for record in result:
            print(f"✅ Neo4j متصل شد! (تست: {record['test']})")
    driver.close()
except Exception as e:
    print(f"❌ خطا در Neo4j: {e}")

print("\n" + "=" * 50)
