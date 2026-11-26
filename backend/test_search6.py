print('Test 6:'); print(list(db.aql.execute("FOR doc IN notes_view RETURN doc.title")))
