print('Test 3:'); print(list(db.aql.execute("FOR doc IN notes_view SEARCH ANALYZER(doc.title == 'colocations', 'text_en') RETURN doc.title")))
