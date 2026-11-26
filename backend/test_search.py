from arango import ArangoClient
client = ArangoClient(hosts='http://arangodb:8529')
db = client.db('gnu_mau_knowledge', username='root', password='gnumau_secret')

# Let's test the search
aql = """
FOR doc IN notes_view
    SEARCH doc.project_id == '6a2cc1816a1b95b9c92ddbd3' AND (
        ANALYZER(TOKENS('colocations', 'text_en') ANY IN doc.title, 'text_en') OR
        ANALYZER(TOKENS('colocations', 'text_en') ANY IN doc.content, 'text_en') OR
        ANALYZER(LIKE(doc.title, CONCAT('%', 'colocations', '%')), 'text_en') OR
        ANALYZER(LIKE(doc.content, CONCAT('%', 'colocations', '%')), 'text_en')
    )
    RETURN doc.title
"""
try:
    print("Search Results:")
    print(list(db.aql.execute(aql)))
except Exception as e:
    print("Error:", e)

# Let's test basic tokens
aql2 = """
FOR doc IN notes_view
    SEARCH doc.project_id == '6a2cc1816a1b95b9c92ddbd3' AND
    ANALYZER(doc.title IN TOKENS('colocations', 'text_en'), 'text_en')
    RETURN doc.title
"""
try:
    print("Basic Search Results:")
    print(list(db.aql.execute(aql2)))
except Exception as e:
    print("Error 2:", e)

# Let's just list all titles to see if it exists
print("All titles:")
print(list(db.aql.execute("FOR doc IN Notes RETURN doc.title")))
