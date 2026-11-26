from arango import ArangoClient
client = ArangoClient(hosts='http://arangodb:8529')
db = client.db('gnu_mau_knowledge', username='root', password='gnumau_secret')
print(list(db.aql.execute('FOR doc IN Notes RETURN doc.title')))
