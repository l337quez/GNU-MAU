print('Test 7:'); print(list(db.aql.execute("FOR doc IN notes_view SEARCH ANALYZER(doc.title IN TOKENS('colocations', 'text_en'), 'text_en') RETURN doc.title")))
